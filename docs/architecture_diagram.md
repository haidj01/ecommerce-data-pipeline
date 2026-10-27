# E-commerce Data Pipeline Architecture

## Converting to PDF

This document contains a Mermaid diagram that can be converted to PDF using several methods:

### Option 1: Using mermaid-cli (Recommended)

```bash
# Install mermaid-cli globally
npm install -g @mermaid-js/mermaid-cli

# Convert to PDF
mmdc -i docs/architecture_diagram.md -o docs/architecture_diagram.pdf

# Or convert to PNG
mmdc -i docs/architecture_diagram.md -o docs/architecture_diagram.png -w 2400
```

### Option 2: Using VS Code

1. Install "Markdown Preview Mermaid Support" extension
2. Open this file in VS Code
3. Use Preview mode (Cmd+Shift+V or Ctrl+Shift+V)
4. Right-click on the preview → "Print" → "Save as PDF"

### Option 3: Using Online Tools

1. Copy the Mermaid code block (lines starting with ` ```mermaid `)
2. Visit https://mermaid.live or https://kroki.io
3. Paste the code and export as PDF/PNG/SVG

### Option 4: Using GitHub

1. Push this file to GitHub
2. View the file on GitHub (renders Mermaid automatically)
3. Use browser "Print to PDF" on the rendered page

## Architecture Diagram

```mermaid
flowchart TB
    %% Styling
    classDef awsService fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#232F3E
    classDef databricksService fill:#FF3621,stroke:#000,stroke-width:2px,color:#fff
    classDef dataStore fill:#3B48CC,stroke:#000,stroke-width:2px,color:#fff
    classDef producer fill:#00C853,stroke:#000,stroke-width:2px,color:#fff

    %% AWS Platform
    subgraph AWS["☁️ AWS Platform"]
        direction TB

        %% Data Generation
        subgraph Generation["Data Generation"]
            PROD[Stream Producers<br/>Order/Customer/Inventory]:::producer
            MWAA_BATCH[MWAA<br/>Batch File Generators]:::awsService
            POSTGRES[(PostgreSQL<br/>Customer Registry)]:::dataStore
        end

        %% Kafka Streaming
        MSK[Amazon MSK<br/>Kafka Topics]:::awsService
        GLUE[Glue Schema Registry<br/>Avro]:::awsService

        %% Real-time Processing
        subgraph Realtime["Real-time Processing"]
            EMR[EMR<br/>Spark Structured Streaming]:::awsService
            OPENSEARCH[OpenSearch<br/>Real-time Dashboard]:::awsService
            MWAA_HEALTH[MWAA<br/>EMR Health Check]:::awsService
        end

        %% Stream Landing
        MSK_CONNECT[MSK Connect<br/>S3 Sink Connector]:::awsService

        %% Storage
        S3[S3 / Unity Catalog<br/>External Volume<br/>Landing Zone]:::dataStore
    end

    %% Databricks Platform
    subgraph DATABRICKS["⚡ Databricks Platform"]
        direction TB

        %% Auto Loader
        AUTOLOADER[Auto Loader<br/>File-arrival Trigger]:::databricksService

        %% Lakehouse
        subgraph Lakehouse["🏛️ Lakehouse - Delta Lake"]
            BRONZE[(Bronze<br/>Raw, Append-only)]:::dataStore
            SILVER[(Silver<br/>Validated, Deduplicated<br/>Customer UNION + Dedup)]:::dataStore
            GOLD[(Gold<br/>Business Metrics)]:::dataStore
        end

        %% Governance & Orchestration
        UC[Unity Catalog<br/>Governance]:::databricksService
        LAKEFLOW[Lakeflow Jobs<br/>Orchestration]:::databricksService
        DASHBOARD[AI/BI Dashboard<br/>SQL Warehouse]:::databricksService
    end

    %% Data Flow Connections

    %% Stream path: Producers -> Kafka
    PROD -->|Avro events<br/>customer-events<br/>orders<br/>inventory-events| MSK
    MSK -.->|schema validation| GLUE

    %% Customer hybrid: Registration -> Kafka + DB
    PROD -->|customer_registered| POSTGRES
    POSTGRES -->|batch updates<br/>10% daily| MWAA_BATCH

    %% MSK -> MSK Connect -> S3 (Landing)
    MSK -->|consumer group 1<br/>Avro files| MSK_CONNECT
    MSK_CONNECT -->|stream/customer_events/*.avro<br/>stream/orders/*.avro<br/>stream/inventory_events/*.avro| S3

    %% MSK -> EMR -> OpenSearch (Real-time metrics)
    MSK -->|consumer group 2<br/>orders topic| EMR
    EMR -->|orders/min<br/>revenue trend| OPENSEARCH

    %% Batch path: MWAA -> S3
    MWAA_BATCH -->|batch/product_catalog/*.csv<br/>batch/customer/*.jsonl| S3

    %% MWAA health check
    MWAA_HEALTH -.->|start/monitor/restart| EMR

    %% Databricks ingestion: S3 -> Bronze -> Silver -> Gold
    S3 -->|file arrival trigger| AUTOLOADER
    AUTOLOADER --> BRONZE
    BRONZE --> SILVER
    SILVER --> GOLD
    GOLD --> DASHBOARD

    %% Governance
    UC -.->|data lineage<br/>access control| BRONZE
    UC -.->|data lineage<br/>access control| SILVER
    UC -.->|data lineage<br/>access control| GOLD

    %% Orchestration
    LAKEFLOW -.->|orchestrate| AUTOLOADER

    %% Notes
    NOTE1["`**Customer Hybrid Flow:**
    - Registration: Kafka stream → bronze.customer_stream
    - Updates: Daily batch → bronze.customer_batch
    - Silver: UNION + dedup by customer_id`"]
    NOTE2["`**Platform Responsibilities:**
    - AWS: Ingestion, Real-time metrics
    - Databricks: Lakehouse, Governance, Analytics`"]

    style NOTE1 fill:#FFF9C4,stroke:#F57F17,stroke-width:2px
    style NOTE2 fill:#E1F5FE,stroke:#01579B,stroke-width:2px
```

## Key Components

### AWS Platform

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Stream Producers** | Generate order, customer, inventory events | Python, confluent-kafka, Faker |
| **Amazon MSK** | Message broker for real-time events | Kafka (3 topics: customer-events, orders, inventory-events) |
| **Glue Schema Registry** | Schema validation for Avro messages | AWS Glue |
| **MSK Connect** | Land Avro events to S3 | S3 Sink Connector |
| **EMR Streaming Job** | Real-time metrics computation | Spark Structured Streaming |
| **OpenSearch** | Real-time dashboard (orders/min, revenue) | OpenSearch + Dashboards |
| **MWAA** | Batch file generation + EMR health check | Apache Airflow |
| **PostgreSQL** | Customer registry (source of truth) | RDS (AWS) / Docker (local) |
| **S3 / UC External Volume** | Landing zone for all data | S3, exposed as Unity Catalog volume |

### Databricks Platform

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Auto Loader** | Incremental file ingestion | Databricks Auto Loader |
| **Bronze Layer** | Raw data, append-only | Delta Lake |
| **Silver Layer** | Validated, deduplicated, conformed | Delta Lake + DQ rules |
| **Gold Layer** | Business metrics and aggregations | Delta Lake |
| **Unity Catalog** | Data governance, lineage, access control | Unity Catalog |
| **Lakeflow Jobs** | Orchestration with file-arrival triggers | Databricks Workflows |
| **AI/BI Dashboard** | Analytics dashboard | Databricks SQL Warehouse |

## Data Flows

### 1. Real-time Stream Path (AWS Only)
```
Producers → MSK → EMR Streaming → OpenSearch Dashboard
```
- **Purpose:** Real-time metrics (orders/min, revenue)
- **Latency:** Seconds
- **Does NOT write to lakehouse**

### 2. Stream Landing Path (AWS → Databricks)
```
Producers → MSK → MSK Connect → S3 (Avro) → Auto Loader → Bronze
```
- **Purpose:** Replay-able source of truth
- **Format:** Avro files
- **Topics:** customer-events, orders, inventory-events

### 3. Batch Landing Path (AWS → Databricks)
```
MWAA (Faker) → S3 (CSV/JSONL) → Auto Loader → Bronze
```
- **Purpose:** Master data (catalog, customer updates)
- **Format:** CSV (catalog), JSONL (customer)
- **Frequency:** Daily

### 4. Customer Hybrid Flow (AWS → Databricks)
```
Registration: Producer → Kafka → MSK Connect → bronze.customer_stream
Updates: PostgreSQL → MWAA → S3 → bronze.customer_batch
Silver: UNION(customer_stream, customer_batch) → dedup by customer_id
```

### 5. Lakehouse Transformation (Databricks)
```
Bronze (raw) → Silver (validated, deduplicated) → Gold (metrics) → Dashboard
```
- **Bronze:** Append-only, raw events
- **Silver:** DQ validation, deduplication, PII masking, customer UNION
- **Gold:** Derived metrics (demand forecast, stockout risk)

## Topics and Events

| Kafka Topic | Key | Event Types | Volume |
|-------------|-----|-------------|--------|
| `customer-events` | customer_id | customer_registered | ~10K/day |
| `orders` | order_id | order_created, order_status_changed | 1M/day |
| `inventory-events` | product_id + warehouse_id | reserved, released, restocked | 100K/day |

## Landing Layout

```
/Volumes/<catalog>/landing/raw/
  stream/
    customer_events/      # Avro from MSK Connect
    orders/               # Avro from MSK Connect
    inventory_events/     # Avro from MSK Connect
  batch/
    product_catalog/dt=YYYY-MM-DD/*.csv
    customer/dt=YYYY-MM-DD/*.jsonl
```

## Dashboards

| Dashboard | Platform | Source | Metrics |
|-----------|----------|--------|---------|
| **Real-time** | OpenSearch | EMR streaming job | Orders per minute, revenue trend |
| **Analytics** | Databricks AI/BI | Gold tables | Daily sales, product ranking, customer segments, stockout risk |

## Cost Optimization Strategy

**Development Phase:**
- Local Docker: Airflow, Kafka, PostgreSQL
- Minimal AWS usage (S3 only, access via `aws_default` connection)

**Demo Phase (1 day max):**
- Provision: MWAA (smallest), MSK, MSK Connect, EMR, OpenSearch, RDS (db.t3.micro)
- Run full pipeline end-to-end
- Collect evidence (screenshots, logs, metrics)
- **Teardown everything** after demo

**Infrastructure as Code:**
- Terraform for one-command provision/teardown
- No hardcoded credentials or account IDs
