# E-Commerce AWS Data Pipeline - Input Data Format Specifications

## Overview
This repository contains comprehensive input data format specifications for an e-commerce AWS data pipeline handling product catalog, inventory, customers, orders, and shipping data.

## Business Context

### Data Sources
- **Product Catalog**: Product information, categorization, pricing, lifecycle management
- **Inventory**: Stock levels, warehouse locations, demand/supply tracking
- **Customers**: Customer profiles, addresses, preferences, purchase history
- **Orders**: Order transactions, line items, payments, fulfillment
- **Shipping**: Shipment tracking, carrier information, delivery status

### Data Volumes
- **Orders**: 1M records per day
- **Inventory Updates**: 100K records per day
- **Product Catalog**: 10K records per day
- **Customers**: 10K records per day
- **Shipping**: ~1M records per day (correlated with orders)

### Ingestion Methods
1. **Real-time Streaming**: Orders, Inventory, Shipping (via Kafka/Kinesis)
2. **Daily Batch**: Product Catalog, Customer master data (via S3/files)

### Stakeholders
- Product Managers
- Catalog Managers
- Warehouse Operations
- Business Analytics teams

## Repository Structure

```
aws_data_pipeline/
├── schemas/                          # JSON schema definitions
│   ├── product_catalog_schema.json
│   ├── customer_schema.json
│   ├── inventory_schema.json
│   ├── order_schema.json
│   ├── shipping_schema.json
│   └── samples/                      # Sample data files
│       ├── product_catalog_sample.csv
│       ├── order_sample_streaming.json
│       └── inventory_sample_streaming.json
├── docs/
│   └── data_formats/
│       ├── data_quality_rules.md     # Data quality validation rules
│       └── format_specifications.md  # Format specs (CSV, JSON, Parquet, Kafka)
├── main.py
└── README.md
```

## Schema Documentation

### 1. Product Catalog (`schemas/product_catalog_schema.json`)

**Purpose**: Product master data with categorization, pricing, and lifecycle management

**Key Features**:
- Unique product identification
- 3-level category hierarchy
- Product lifecycle tracking (pre_launch → active → discontinued → archived)
- Price and cost tracking
- Multi-attribute support

**Critical Fields**:
- `product_id` (PK)
- `category_level_1`, `category_level_2`, `category_level_3`
- `lifecycle_status` (with valid state transitions)
- `is_active` (must align with lifecycle_status)

**Data Quality Rules**:
- Clear product lifecycle with valid state transitions
- Precise product categorization hierarchy
- Price >= Cost validation

### 2. Customer (`schemas/customer_schema.json`)

**Purpose**: Customer master data with unique identification strategy

**Key Features**:
- **Unique customer identification** (primary requirement)
- Dual identifier strategy: customer_id + email
- Address management (billing + multiple shipping)
- Customer segmentation and lifetime value
- Marketing consent tracking

**Critical Fields**:
- `customer_id` (PK, globally unique)
- `email` (unique, secondary identifier)
- `account_status` (with valid transitions)

**Data Quality Rules**:
- Absolute uniqueness on customer_id and email
- Age validation (minimum 13 years)
- Customer lifetime value reconciliation

### 3. Inventory (`schemas/inventory_schema.json`)

**Purpose**: Real-time inventory tracking with demand/supply management

**Key Features**:
- Quantity tracking (on_hand, reserved, available, in_transit, damaged)
- **Supply pipeline** tracking
- Reorder point management
- Demand forecast & stockout risk computed in the Gold layer (not in source feed)

**Critical Fields**:
- `inventory_id` (PK)
- `product_id` (FK)
- `warehouse_id`
- `quantity_on_hand`, `quantity_reserved`, `quantity_available`
- `supply_on_order`

**Data Quality Rules**:
- `quantity_available = quantity_on_hand - quantity_reserved` (enforced)
- Inventory accuracy within 1% tolerance
- Monthly physical count reconciliation

### 4. Order (`schemas/order_schema.json`)

**Purpose**: Order transaction tracking from placement to delivery

**Key Features**:
- Order header with line items (nested structure)
- Payment and order status tracking
- Multi-channel support
- Financial calculations (subtotal, discounts, tax, shipping)
- Fraud detection scoring

**Critical Fields**:
- `order_id` (PK, globally unique)
- `customer_id` (FK)
- `order_items` (array of line items)
- `order_status`, `payment_status`
- `total_amount`

**Data Quality Rules**:
- `total_amount = subtotal - discount_total + tax_total + shipping_cost`
- Valid order status flow: pending → confirmed → processing → shipped → delivered
- Payment must be authorized/paid before processing

### 5. Shipping (`schemas/shipping_schema.json`)

**Purpose**: Shipment and delivery tracking

**Key Features**:
- Carrier and tracking integration
- Multi-package shipment support
- Real-time tracking events
- Delivery status updates
- International shipment handling

**Critical Fields**:
- `shipment_id` (PK)
- `order_id` (FK)
- `tracking_number` (unique per carrier)
- `shipment_status`
- `tracking_events` (array of status updates)

**Data Quality Rules**:
- Valid shipment status flow
- Tracking events in chronological order
- Customs declaration required for international shipments

## Data Quality Rules

Comprehensive data quality validation rules are documented in `docs/data_formats/data_quality_rules.md`.

### Key Validation Categories

1. **Referential Integrity** (0% tolerance)
   - All foreign keys must exist in referenced tables
   - No orphaned records allowed

2. **Unique Identification** (0% tolerance)
   - customer_id: globally unique
   - email: unique across customers
   - order_id: globally unique
   - tracking_number: unique per carrier

3. **Calculated Field Validation**
   - Inventory: quantity_available = quantity_on_hand - quantity_reserved
   - Orders: total_amount = subtotal - discount + tax + shipping
   - Line items: line_total = quantity × unit_price - discount

4. **Status Transition Validation**
   - Product lifecycle: pre_launch → active → discontinued → archived
   - Order status: pending → confirmed → processing → shipped → delivered
   - Shipment status: pending → shipped → in_transit → delivered

5. **Temporal Validation**
   - order_date <= current_timestamp
   - estimated_delivery_date >= order_date
   - actual_delivery_date >= shipped_date

## Format Specifications

Detailed format specifications for CSV, JSON, Parquet, and Kafka are in `docs/data_formats/format_specifications.md`.

### Supported Formats

| Format | Use Case | Compression | Best For |
|--------|----------|-------------|----------|
| **JSON** | Streaming (Kafka/Kinesis) | Snappy/GZIP | Real-time events, nested data |
| **CSV** | Batch (daily files) | GZIP | Simple tabular data, legacy systems |
| **Parquet** | Batch (analytics) | Snappy | Large datasets, analytical queries |
| **Kafka** | Real-time streaming | Snappy/LZ4 | High-throughput event streams |

### Format Selection Guide

| Entity | Primary Format | Secondary Format | Reason |
|--------|---------------|------------------|---------|
| Product Catalog | Parquet (batch) | JSON (streaming) | Daily updates, analytical queries |
| Customer | Parquet (batch) | JSON (streaming) | Master data, periodic updates |
| Inventory | Kafka JSON | Parquet (snapshot) | Real-time updates critical |
| Orders | Kafka JSON | Parquet (archive) | Real-time processing required |
| Shipping | Kafka JSON | Parquet (archive) | Real-time tracking updates |

### Streaming Format (Kafka/JSON)

**Structure**:
```json
{
  "event_type": "order_created",
  "event_timestamp": "2024-03-20T10:15:30Z",
  "event_id": "evt_ord_1001234",
  "source_system": "checkout_service",
  "idempotency_key": "ord_1001234_20240320101530",
  "data": {
    // Entity-specific data
  }
}
```

**Key Features**:
- Event envelope with metadata
- Idempotency key for deduplication
- Event timestamp for ordering
- Source system tracking

### Batch Format (CSV/Parquet)

**CSV Requirements**:
- UTF-8 encoding
- Header row required
- ISO 8601 timestamps
- Quoted strings for special characters

**Parquet Advantages**:
- Columnar storage (5-10x compression)
- Native nested structure support
- Efficient for analytics
- Schema enforcement

## File Naming Conventions

### Batch Files
```
{entity}_YYYYMMDD_HHMMSS.{csv|json|parquet}

Examples:
- product_catalog_20240320_083000.parquet
- customer_20240320_083000.csv
- inventory_20240320_083000.parquet
```

### S3 Bucket Structure
```
s3://data-pipeline-raw/
  ├── product_catalog/year=2024/month=03/day=20/
  ├── customer/year=2024/month=03/day=20/
  ├── inventory/year=2024/month=03/day=20/
  ├── orders/year=2024/month=03/day=20/
  └── shipping/year=2024/month=03/day=20/
```

## Kafka Topic Configuration

### Topics

| Topic | Key | Partitions | Retention | Volume |
|-------|-----|------------|-----------|--------|
| `orders` | customer_id | 50 | 7 days | 1M/day |
| `inventory` | product_id | 20 | 3 days | 100K/day |
| `shipping` | order_id | 50 | 30 days | 1M/day |

### Message Ordering
- Events with same key → same partition (ordering guaranteed)
- `event_timestamp` used for event-time processing

## Sample Data

Sample data files are provided in `schemas/samples/`:

- `product_catalog_sample.csv` - 5 sample products in CSV format
- `order_sample_streaming.json` - Sample order in streaming JSON format
- `inventory_sample_streaming.json` - Sample inventory update event

## Implementation Phases

### Phase 1: Batch Processing (Weeks 1-4)
- CSV/Parquet files uploaded to S3 daily
- Product catalog and customer master data
- Daily batch processing with AWS Glue

### Phase 2: Hybrid Streaming (Weeks 5-8)
- Add Kafka streaming for orders and inventory
- Master data remains batch
- Real-time dashboards for critical metrics

### Phase 3: Full Streaming (Weeks 9-12)
- All entities streaming
- Batch only for historical loads
- Real-time analytics and alerting

## Next Steps

1. **Review and Approve Schemas**
   - Business stakeholders validate field definitions
   - Confirm data quality rules
   - Sign off on format specifications

2. **Set Up Data Sources**
   - Configure source systems to export in agreed formats
   - Set up Kafka topics for streaming entities
   - Create S3 buckets for batch files

3. **Implement Data Pipeline**
   - Build ingestion layer (AWS Glue, Lambda, Kinesis)
   - Implement data quality validation
   - Set up monitoring and alerting

4. **Testing**
   - Unit tests for data validation rules
   - Integration tests with sample data
   - Performance tests at expected volumes

## Questions or Clarifications?

If you have questions about:
- Specific field definitions → See individual schema files in `schemas/`
- Data quality rules → See `docs/data_formats/data_quality_rules.md`
- Format specifications → See `docs/data_formats/format_specifications.md`
- Business requirements → Contact Product Manager or Catalog Manager

## Version History

- **v1.0** (2024-03-20): Initial schema definitions for all entities
