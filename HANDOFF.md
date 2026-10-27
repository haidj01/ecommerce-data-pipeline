# Session Handoff — E-commerce Data Pipeline

Context summary for continuing this project in a new Claude Code session.
**Read `CLAUDE.md` first** (current architecture and rules). This file records *why* decisions were made, what changed, and what is next.

Last updated: 2026-10-19

---

## 1. About the owner & working style

- DJ (Dongjin Kim) — data engineer, 10+ years (Spark, Kafka, Airflow, AWS, Delta Lake, OpenSearch); last role in e-commerce (Chewy).
- Passed Databricks DE Associate; this project doubles as **DE Professional exam practice**.
- Preferences: concise answers; **Korean for conversation, English for code/docs**; move fast from concept to tangible output.
- Final deliverable: a **public GitHub portfolio repo**.

## 2. Project goal

A simulated e-commerce data pipeline showing **both real-time streaming and batch processing** on an **AWS + Databricks** hybrid platform, scoped to one domain (orders) so it can actually be finished.

## 3. Decision log (chronological, with rationale)

| # | Decision | Rationale |
|---|---|---|
| 1 | General e-commerce domain (no Chewy-specific entities like pets/Autoship) | Keep scope clean |
| 2 | Real-time + batch on the same order data | Show both skills without widening scope |
| 3 | Delta Lake on S3, medallion (Bronze/Silver/Gold) | Storage/compute separation, industry standard |
| 4 | Real-time metrics go straight from streaming to OpenSearch, not through Gold | Going through batch layers adds latency |
| 5 | Streaming also lands raw events in the lake | Replayable source of truth for batch |
| 6 | Reuse existing repo specs (`schemas/`, `docs/data_formats/`) instead of re-designing | They were richer than the new draft (event envelope, DQ rules, per-warehouse inventory) |
| 7 | `order_items` stays nested in events; exploded in Silver with PK (`order_id`, `line_item_id`) | `line_item_id` is only unique within an order |
| 8 | Inventory derived fields removed from source schema → computed in Gold | `demand_forecast_30d/90d`, `days_of_supply`, `stockout_risk_score` are not source data |
| 9 | `actual_delivery_date` removed from `order`; lives only in `shipping` | Avoid duplicated delivery state |
| 10 | Ingestion: catalog = daily CSV, customer = daily **JSONL**, order/inventory = Kafka stream, shipping = stream (**Phase 2, proposed**) | Master data is batch, events are streams; customer has nested fields so JSON not CSV |
| 11 | **Platform split:** AWS = ingestion + real-time; Databricks = Bronze/Silver/Gold | Puts DE Pro topics (Auto Loader, UC, Volumes, Lakeflow) on Databricks |
| 12 | Kafka → **MSK Connect S3 Sink (Avro)** → S3 / UC External Volume → **Auto Loader** → Bronze | No custom code for landing; Auto Loader practice |
| 13 | Schema registry: AWS Glue Schema Registry (Avro) | Needed for Avro on MSK |
| 14 | Kafka → EMR Structured Streaming → OpenSearch (real-time dashboard only, no lake write) | Separate consumer group from MSK Connect |
| 15 | **Glue Data Catalog dropped → Unity Catalog** | Databricks owns the lakehouse |
| 16 | Dashboards: OpenSearch (real-time) + **Databricks AI/BI** (Gold analytics); no Gold → OpenSearch push | Avoid cross-platform write-back |
| 17 | Databricks orchestration: **Lakeflow Jobs** with **file-arrival trigger** on the landing volume | MWAA and Databricks stay decoupled; volume is the only hand-off |
| 18 | **MWAA (smallest)**: generate catalog/customer files with Faker → S3; start + health-check EMR streaming job | ≤10K rows/day is fine on workers; Airflow is DJ's strength |
| 19 | Order/inventory producers run **outside** MWAA (ECS or local) | Long-running, ~1M events/day |
| 20 | **Cost plan:** develop locally (Docker Airflow + Kafka; Airflow → AWS via `aws_default` + AWS profile); AWS demo **max 1 day**, collect evidence, **tear down everything** | MWAA/MSK/EMR/OpenSearch bill while idle |
| 21 | IaC required (tool TBD, likely Terraform) | One-command provision/teardown for the 1-day demo |
| 22 | **Customer hybrid ingestion:** registration via Kafka (`customer_registered`), updates via daily batch JSONL. Bronze: separate tables (`customer_stream`, `customer_batch`). Silver: UNION + dedup by `customer_id` | Demonstrates CDC pattern, late-arriving dimension handling, and multi-source merge in Silver |
| 23 | **Customer registry DB (PostgreSQL):** single `customer_registry` table; registration producer writes to both Kafka + DB; batch update DAG reads/updates DB (10% random daily), generates JSONL. No history table. Dev: local Docker; AWS: RDS db.t3.micro | DB serves as source of truth for batch updates, ensures data consistency; update fields: address, contact, preferences |

## 4. Changes already made to the repo

- **Schemas → v1.1**
  - `schemas/order_schema.json`: removed `actual_delivery_date` (+2 DQ rules); added `silver_transformation` block (explode rule, composite PK).
  - `schemas/inventory_schema.json`: removed 4 derived fields (29 → 25 fields); added `demand_supply_tracking.gold_layer_metrics`.
  - Note: these JSON files were re-serialized (blank lines between sections were lost; content unchanged otherwise).
- Samples updated accordingly: `schemas/samples/inventory_sample_streaming.json`, `inventory_generated_*.csv`, `order_sample_streaming.json`.
- `tools/generate_sample_inventory.py`: derived fields removed from output (compiles; **not run** — `faker` was not installed in the test shell).
- Docs synced: `docs/data_formats/data_quality_rules.md`, `entity_relationships.md`, `README.md` (only the affected lines).
- **`CLAUDE.md` created** (architecture, ingestion table, topics, layer rules, dashboards, execution plan, roadmap, open decisions).
- **`CLAUDE.md` updated** for customer hybrid ingestion: added `customer-events` Kafka topic, updated Entities & Ingestion table, Data Flows, Landing Layout, and Layer Design Rules (Bronze split + Silver merge).
- **`CLAUDE.md` updated** for customer registry DB: added PostgreSQL to Tech Stack, detailed customer hybrid flow (registration producer → Kafka + DB, batch update DAG → DB select/update → JSONL), updated Repository Structure (`db/` folder), Roadmap, and Execution Plan (local PostgreSQL + RDS).
- **Git:** `git init -b main` + `.gitignore`. **No commits yet**; git user identity not configured in that shell.

## 5. Current repo state

```
CLAUDE.md, HANDOFF.md, README.md, .gitignore
schemas/            5 entity schemas (customer, product_catalog, inventory, order, shipping) + samples/ + ERD PDF
docs/data_formats/  format specs, DQ rules, additional business rules, ERD
docs/summary_note.txt  original requirement notes
tools/              Faker generators: catalog, customer, inventory; schema diagram
.claude/agents/     aws-data-engineer, aws-platform-architect, data-feed-engineer, business-analyst-stakeholder
```

No pipeline code exists yet (no producers, streaming job, DAGs, Databricks code, or IaC).

## 6. Known gaps / inconsistencies

- **`README.md` is outdated**: it is the original spec README (mentions Kinesis option, `main.py`, every entity as both batch and streaming). Needs a rewrite for the portfolio audience matching `CLAUDE.md`.
- Schemas still list **both** `daily_batch` and `real_time_streaming` in `frequency` / `supported_formats` — align with the ingestion table (decision #10, #22, #23).
- **PostgreSQL schema not created yet**: need `db/schema.sql` with `customer_registry` table DDL.
- **Customer generators don't exist yet**: need registration producer (Kafka + DB) and batch update DAG (DB → JSONL).
- `tools/generate_sample_customer.py` outputs CSV — will be replaced by the batch update DAG above.
- `inventory_turnover_rate` and `inventory_value` are also derived values — decide whether to move them to Gold.
- The old folder `/Users/dkim/WorkSpace/aws_data_pipeline` now contains only `.idea/`; this repo is the active one.

## 7. Open decisions

1. Late-arriving dimensions — **partially addressed** by customer hybrid (registrations arrive in real-time via stream). Product catalog is still batch-only; decide handling for orders referencing products not yet in the daily batch.
2. `inventory_turnover_rate` / `inventory_value` → Gold?
3. Silver/Gold style: Lakeflow Declarative Pipelines (DLT) vs notebooks + jobs.
4. IaC tool (Terraform likely).
5. Confirm shipping as Phase 2.

## 8. Next steps (suggested order)

1. First commit (set git identity), optionally create the GitHub remote.
2. **PostgreSQL schema**: `db/schema.sql` with `customer_registry` table DDL.
3. Align schema `frequency` / `supported_formats` with the ingestion table.
4. **Customer registration producer** (Python, confluent-kafka, Avro): Faker → Kafka `customer-events` + PostgreSQL `customer_registry`.
5. **Customer batch update DAG** (MWAA): SELECT 10% from `customer_registry` → Faker updates (address, contact, preferences) → UPDATE DB → write JSONL → S3 `batch/customer/`.
6. Local Airflow (Docker) + local PostgreSQL (Docker) setup: connections `aws_default` and `postgres_default`.
7. MWAA DAG: daily catalog generation → S3 landing path.
8. Order producer (Python, confluent-kafka, Avro) against local Kafka.
9. Inventory event producer driven by order events.
10. Databricks: Auto Loader → Bronze (`customer_stream`, `customer_batch`, others); Silver (`customer` UNION + dedup, others) + Gold + Lakeflow Job with file-arrival trigger.
11. EMR streaming job → OpenSearch + MWAA start/health-check DAGs.
12. IaC (Terraform), 1-day AWS demo (provision MWAA, MSK, RDS, EMR, OpenSearch, Databricks), evidence in `docs/demo/`, teardown, publish.
13. Rewrite `README.md` for the portfolio.
