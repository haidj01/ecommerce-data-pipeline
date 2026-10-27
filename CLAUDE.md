# E-commerce Data Pipeline (Portfolio Project)

A simulated end-to-end data pipeline for a general e-commerce domain on an **AWS + Databricks** hybrid platform.
Goals: demonstrate real-time streaming and batch processing, and practice for the **Databricks Data Engineer Professional** exam.

See `HANDOFF.md` for decision history, changes made so far, open decisions, and next steps.

## Architecture

```
[AWS]
Order/inventory producers (ECS or local) ──► Kafka (MSK)
Kafka (MSK) ──► MSK Connect (S3 Sink, Avro) ──► S3 / UC External Volume ──┐
     └────────► Spark Structured Streaming (EMR) ──► OpenSearch           │
MWAA DAG (Faker) ──► CSV / JSONL files ─────────► S3 / UC External Volume ┤
MWAA ──► starts + health-checks the EMR streaming job                     │
                                                                           ▼
[Databricks]          Auto Loader ──► Bronze ──► Silver ──► Gold ──► AI/BI Dashboard
                      (Lakeflow Jobs with file-arrival triggers, governed by Unity Catalog)
```

### Platform responsibilities
| Platform | Responsibility |
|---|---|
| AWS | Event ingestion (MSK), raw file landing (S3), real-time metrics (EMR → OpenSearch), AWS-side orchestration (MWAA) |
| Databricks | Bronze / Silver / Gold (Delta), orchestration, governance, analytics dashboard |

## Tech Stack

| Layer | Tool |
|---|---|
| Data generators | Python, Faker, confluent-kafka |
| Messaging | Kafka — Amazon MSK |
| Schema registry | AWS Glue Schema Registry (Avro) |
| Kafka → S3 | MSK Connect — S3 Sink Connector (Avro output) |
| Raw landing | Amazon S3, exposed as Unity Catalog External Volume |
| Real-time processing | Spark Structured Streaming on EMR |
| Real-time dashboard | OpenSearch + OpenSearch Dashboards |
| Ingestion to Bronze | Databricks Auto Loader |
| Lakehouse | Delta Lake on Databricks (Bronze / Silver / Gold) |
| Catalog & governance | Unity Catalog |
| Orchestration (AWS) | Amazon MWAA, smallest environment — batch file generation, EMR streaming start + health check |
| Orchestration (Databricks) | Lakeflow Jobs (file-arrival trigger on the landing volume) |
| Analytics dashboard | Databricks AI/BI Dashboard (SQL Warehouse) |
| Customer registry | PostgreSQL (local Docker for dev, RDS db.t3.micro for AWS demo) — source of truth for batch updates |

## Entities & Ingestion

Source of truth for fields, types and rules: `schemas/*.json` and `docs/data_formats/`. Do not duplicate them here.

| Entity | Ingestion | Format | Generator | Volume |
|---|---|---|---|---|
| `product_catalog` | Daily batch file | CSV | MWAA DAG using `tools/generate_sample_catalog.py` | 10K/day |
| `customer` | **Hybrid:** Kafka stream (registration) + Daily batch file (updates) | Avro (stream), JSON Lines (batch) | New Python producer (registration), MWAA DAG using `tools/generate_sample_customer.py` (updates) | Stream: ~10K/day, Batch: variable |
| `order` | Kafka stream | Avro | New Python producer | 1M/day |
| `inventory` | Kafka stream | Avro | Driven by order events + restocks | 100K/day |
| `shipping` | Kafka stream (Phase 2) | Avro | Driven by orders reaching `shipped` | ~1M/day |

### Kafka topics
| Topic | Key | Event types |
|---|---|---|
| `customer-events` | `customer_id` | customer_registered |
| `orders` | `order_id` | order_created, order_status_changed |
| `inventory-events` | `product_id` + `warehouse_id` | reserved, released, restocked |
| `shipments` (Phase 2) | `order_id` | shipment_created, status_updated |

Every event carries an envelope: `event_id`, `event_type`, `event_timestamp`, `source_system`, `idempotency_key`.
MSK Connect and the EMR streaming job consume the same topics with **separate consumer groups**.

### Generation order
Master files (product_catalog, customer) are generated first; stream producers pick IDs from them so foreign keys stay valid.

### Where generators run
- **Batch generators (catalog, customer updates):** run inside MWAA workers (≤10K rows/day, lightweight). Faker → CSV / JSONL → upload to S3 landing path. Add `faker` to MWAA `requirements.txt`.
- **Stream producers (customer registration, order, inventory):** long-running — run outside MWAA (ECS task or local), never on Airflow workers.

### Customer hybrid flow details

**Customer Registry DB (PostgreSQL)**
- Single table: `customer_registry` with all customer fields + `last_updated_at`, `created_at`
- Dev: local PostgreSQL (Docker), connection: `postgres_default`
- AWS demo: RDS PostgreSQL db.t3.micro, same connection name
- No separate history table; updates overwrite in place

**Registration (real-time stream)**
1. Customer registration producer (Python, confluent-kafka, Avro)
   - Generate new customer with Faker
   - Publish to Kafka topic `customer-events` (event: `customer_registered`)
   - **Save to `customer_registry` DB** (source of truth for batch updates)
   - MSK Connect → S3 `stream/customer_events/*.avro` → `bronze.customer_stream`

**Update (daily batch)**
1. MWAA DAG: `customer_batch_update` (runs daily on MWAA worker)
   - SELECT 10% of customers randomly from `customer_registry`
   - Generate updates with Faker: address (address_line1, city, state, postal_code), contact (email, phone_number), preferences (marketing_opt_in, loyalty_tier)
   - UPDATE `customer_registry` (preserve changes for consistency)
   - Write JSONL file with updates
   - Upload to S3 `batch/customer/dt=YYYY-MM-DD/*.jsonl` → `bronze.customer_batch`

## Data Flows

1. **Real-time path (AWS):** EMR Structured Streaming reads `orders` → computes orders per minute and revenue → writes to OpenSearch. It does not write to the lake.
2. **Stream landing (AWS):** MSK Connect writes Avro files to the External Volume. Bronze latency depends on the connector flush/rotate interval.
3. **Batch landing (AWS):** a daily MWAA DAG generates catalog (CSV) and customer update (JSONL) files with Faker and uploads them to the External Volume path.
4. **Customer hybrid (AWS → Databricks):** new customer registrations flow via Kafka → MSK Connect → `bronze.customer_stream`; profile updates flow via daily batch → `bronze.customer_batch`. Silver merges both via UNION.
5. **Streaming job control (AWS):** an MWAA DAG starts the EMR streaming job once; a health-check DAG polls its state every few minutes and restarts + alerts on failure.
6. **Lakehouse (Databricks):** file-arrival trigger → Auto Loader → Bronze (raw, append-only) → Silver (validated, deduplicated, conformed) → Gold (marts). Orchestrated by Lakeflow Jobs.
7. MWAA and Lakeflow Jobs are decoupled: the landing volume is the only hand-off point; MWAA never calls Databricks directly.

## Landing Layout (S3 / External Volume)

```
/Volumes/<catalog>/landing/raw/
  stream/customer_events/     # Avro from MSK Connect (customer_registered)
  stream/orders/              # Avro from MSK Connect
  stream/inventory_events/
  batch/product_catalog/dt=YYYY-MM-DD/*.csv
  batch/customer/dt=YYYY-MM-DD/*.jsonl  # customer updates
```

Unity Catalog schemas: `bronze`, `silver`, `gold`.

## Layer Design Rules

- **Bronze:** store events as received; `order_items` stays nested. Add ingestion metadata (`_ingested_at`, `_source_file`).
  - **Customer hybrid:** maintain separate tables `bronze.customer_stream` (from Kafka, registration events) and `bronze.customer_batch` (from daily JSONL, updates). Both are append-only.
- **Silver:**
  - **Customer merge:** UNION `bronze.customer_stream` and `bronze.customer_batch` → deduplicate by `customer_id` (keep latest by `event_timestamp` or `_ingested_at`) → `silver.customer`.
  - Explode `order.order_items` into `silver.order_items`, carrying `order_id`, `order_date`, `event_timestamp` from the header. PK = (`order_id`, `line_item_id`).
  - Deduplicate on `event_id` / `idempotency_key`; use `event_timestamp` for watermarking.
  - Apply rules from `docs/data_formats/data_quality_rules.md`.
  - Mask PII (e.g. `payment_methods`, `date_of_birth`).
- **Gold:** derived metrics are computed here, never in source feeds — `demand_forecast_30d/90d`, `days_of_supply`, `stockout_risk_score`.
- Actual delivery date lives only in `shipping` (removed from `order`).

## Dashboards

| Dashboard | Tool | Source | Metrics |
|---|---|---|---|
| Real-time | OpenSearch Dashboards | EMR streaming job | Orders per minute, revenue trend |
| Analytics | Databricks AI/BI | Gold tables | Daily sales, product ranking, customer segments, stockout risk |

## Repository Structure

```
schemas/              # Entity schemas (JSON) + samples/
docs/data_formats/    # Format specs, data quality rules, ERD
tools/                # Sample data generators (Faker)
.claude/agents/       # Sub-agents: aws-data-engineer, aws-platform-architect, data-feed-engineer, business-analyst-stakeholder
# To add:
db/                   # PostgreSQL schema (customer_registry table DDL)
producers/            # Kafka producers (customer registration, orders, inventory) — run on ECS / local
airflow/dags/         # MWAA DAGs: batch file generation (catalog, customer updates), EMR streaming start + health check
streaming/            # EMR Structured Streaming job → OpenSearch
databricks/           # Bronze / Silver / Gold notebooks or pipelines, job definitions
infra/                # AWS + Databricks infrastructure (Terraform)
```

## Roadmap

- [x] Entity schemas v1.1 (derived fields removed, order_items silver rule)
- [x] Customer hybrid ingestion design (stream + batch)
- [ ] PostgreSQL schema: `customer_registry` table DDL
- [ ] Align `frequency` / `supported_formats` in schemas with the ingestion table above
- [ ] Customer registration producer (Kafka, Avro, DB insert)
- [ ] Customer batch update generator (MWAA DAG, DB select/update → JSONL)
- [ ] MWAA DAG: daily catalog generation → S3 landing
- [ ] MWAA DAGs: EMR streaming start + health check
- [ ] Order producer (Kafka, Avro, Glue Schema Registry)
- [ ] Inventory event producer
- [ ] MSK Connect S3 Sink → External Volume
- [ ] Auto Loader → Bronze (customer_stream, customer_batch, others)
- [ ] Silver / Gold transformations + Lakeflow Job (customer UNION + dedup)
- [ ] EMR streaming job → OpenSearch dashboard
- [ ] Databricks AI/BI dashboard
- [ ] IaC: one-command provision / teardown (Terraform)
- [ ] 1-day AWS demo + evidence collection → `docs/demo/`
- [ ] Teardown + publish to GitHub
- [ ] Phase 2: shipping

## Open Decisions

- Late-arriving dimensions (order arrives before its customer/product in the daily batch)
- Whether `inventory_turnover_rate` and `inventory_value` move to Gold
- Silver/Gold implementation style: Lakeflow Declarative Pipelines (DLT) vs notebooks + jobs
- IaC tool (e.g. Terraform) — required by the 1-day demo + full teardown plan

## Execution Plan & Cost

1. **Develop locally:** local Airflow (Docker) + local Kafka + local PostgreSQL; Airflow reaches AWS via the `aws_default` connection (AWS profile). No MWAA/RDS during development.
2. **Demo on AWS — max 1 day:** provision everything (MWAA, MSK, RDS, EMR, OpenSearch, Databricks), run the full pipeline end-to-end, collect evidence.
3. **Tear down everything** after the demo (MWAA, MSK, MSK Connect, EMR, OpenSearch, RDS, Databricks compute; empty/delete S3 buckets).
4. **Final deliverable:** this GitHub repository (code, IaC, docs, evidence).

Implications:
- Infrastructure must be reproducible with one command up / one command down (Terraform).
- DAG and job code must be environment-agnostic: connections `aws_default` and `postgres_default`, settings in Airflow Variables / config, no hard-coded bucket names, IDs, or DB credentials.
- Never commit credentials, account IDs, or generated data files.

### Evidence to collect during the demo (`docs/demo/`)
- Architecture diagram and the exact config used
- Screenshots: OpenSearch real-time dashboard, Databricks AI/BI dashboard, Airflow DAG runs, Lakeflow Job runs, Unity Catalog lineage
- Record counts per layer (landing → bronze → silver → gold) and data-quality check results
- Streaming metrics: throughput and end-to-end latency
- Short logs of the EMR streaming job and health-check restarts
- AWS / Databricks cost for the demo day

## Conventions

- Python (PySpark for Spark jobs)
- Code, comments and docs in English
- Keep scope tight: finish one entity end-to-end (order) before expanding
