# Data Format Specifications: Streaming vs Batch

## Overview
This document defines how data should be formatted for different ingestion methods (streaming vs batch) and different file formats (CSV, JSON, Parquet, Kafka messages).

## Ingestion Patterns

### Real-Time Streaming
- **Use Cases**: Orders, Inventory updates, Shipping events
- **Volume**: 1M+ events per day
- **Latency Requirement**: < 5 seconds from event to ingestion
- **Technologies**: Kafka, Kinesis, API webhooks
- **Format**: JSON (primary), Kafka messages

### Daily Batch
- **Use Cases**: Product catalog, Customer master data, Historical data loads
- **Volume**: 10K-100K records per batch
- **Latency Requirement**: Daily (overnight processing)
- **Technologies**: S3, file uploads, database exports
- **Format**: CSV, Parquet, JSON

## Format Specifications by Type

### 1. JSON Format (Streaming & Batch)

#### General Structure
```json
{
  "event_type": "order_created",
  "event_timestamp": "2024-03-20T14:22:15Z",
  "event_id": "evt_1234567890",
  "source_system": "ecommerce_api",
  "data": {
    // Entity-specific data here
  }
}
```

#### Streaming JSON (Kafka/Kinesis)
**Characteristics:**
- One event per message
- Includes event metadata
- Event timestamp for ordering
- Idempotency key for deduplication

**Order Example:**
```json
{
  "event_type": "order_created",
  "event_timestamp": "2024-03-20T10:15:30Z",
  "event_id": "evt_ord_1001234",
  "source_system": "checkout_service",
  "idempotency_key": "ord_1001234_20240320101530",
  "data": {
    "order_id": "ORD-2024-1001234",
    "customer_id": "CUST-1001234",
    "order_date": "2024-03-20T10:15:30Z",
    "order_status": "pending",
    "payment_status": "authorized",
    "order_channel": "web",
    "order_items": [
      {
        "line_item_id": "LINE-001",
        "product_id": "PROD-12345",
        "product_name": "Men's Cotton T-Shirt - Blue",
        "quantity": 2,
        "unit_price": 29.99,
        "discount_amount": 5.00,
        "line_total": 54.98
      }
    ],
    "subtotal": 139.97,
    "discount_total": 5.00,
    "tax_total": 10.80,
    "shipping_cost": 8.99,
    "total_amount": 154.76,
    "currency": "USD"
  }
}
```

**Inventory Update Example (Streaming):**
```json
{
  "event_type": "inventory_updated",
  "event_timestamp": "2024-03-20T14:22:15Z",
  "event_id": "evt_inv_5678",
  "source_system": "warehouse_management",
  "idempotency_key": "inv_prod12345_wh01_20240320142215",
  "data": {
    "inventory_id": "INV-20240320-001234",
    "product_id": "PROD-12345",
    "warehouse_id": "WH-NYC-01",
    "quantity_on_hand": 150,
    "quantity_reserved": 25,
    "quantity_available": 125,
    "event_type": "stock_update",
    "change_reason": "order_fulfillment"
  }
}
```

#### Batch JSON (File-based)
**Characteristics:**
- Array of records
- No event envelope
- Newline-delimited JSON (NDJSON) for large files

**NDJSON Format (Recommended for Large Batches):**
```json
{"customer_id": "CUST-1001234", "email": "john.doe@example.com", "first_name": "John", "last_name": "Doe", "account_status": "active", "registration_date": "2023-01-10T12:00:00Z", "created_at": "2023-01-10T12:00:00Z", "updated_at": "2024-03-20T14:22:15Z", "event_timestamp": "2024-03-20T14:22:15Z"}
{"customer_id": "CUST-1001235", "email": "jane.smith@example.com", "first_name": "Jane", "last_name": "Smith", "account_status": "active", "registration_date": "2023-02-15T10:30:00Z", "created_at": "2023-02-15T10:30:00Z", "updated_at": "2024-03-20T14:22:15Z", "event_timestamp": "2024-03-20T14:22:15Z"}
```

**Standard JSON Array (For Smaller Batches):**
```json
[
  {
    "customer_id": "CUST-1001234",
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "account_status": "active",
    "created_at": "2023-01-10T12:00:00Z"
  }
]
```

### 2. CSV Format (Batch Only)

#### General Requirements
- UTF-8 encoding
- Header row required
- Comma delimiter (`,`)
- Quoted fields for strings containing commas, quotes, or newlines
- ISO 8601 format for timestamps (YYYY-MM-DDTHH:MM:SSZ)
- Empty string for NULL values in optional fields

#### Nested Fields Handling
**Option 1: JSON encoding within CSV**
```csv
order_id,customer_id,order_items,total_amount
"ORD-2024-1001234","CUST-1001234","[{""line_item_id"":""LINE-001"",""product_id"":""PROD-12345"",""quantity"":2}]",154.76
```

**Option 2: Flattened structure (Recommended for simple cases)**
```csv
order_id,customer_id,line_item_id,product_id,quantity,unit_price
ORD-2024-1001234,CUST-1001234,LINE-001,PROD-12345,2,29.99
ORD-2024-1001234,CUST-1001234,LINE-002,PROD-67890,1,79.99
```

#### Example: Product Catalog CSV
```csv
product_id,product_name,category_level_1,category_level_2,category_level_3,brand,price,currency,lifecycle_status,is_active,created_at,updated_at,event_timestamp
PROD-12345,"Men's Cotton T-Shirt - Blue",Apparel,Men's Clothing,T-Shirts & Tanks,Nike,29.99,USD,active,true,2024-01-15T10:30:00Z,2024-03-20T14:22:15Z,2024-03-20T14:22:15Z
PROD-67890,"Women's Jeans - Black",Apparel,Women's Clothing,Jeans,Levi's,79.99,USD,active,true,2024-02-01T09:00:00Z,2024-03-20T14:22:15Z,2024-03-20T14:22:15Z
```

#### Example: Customer CSV
```csv
customer_id,email,phone,first_name,last_name,account_status,customer_segment,registration_date,created_at,updated_at,event_timestamp
CUST-1001234,john.doe@example.com,+1-555-123-4567,John,Doe,active,premium,2023-01-10T12:00:00Z,2023-01-10T12:00:00Z,2024-03-20T14:22:15Z,2024-03-20T14:22:15Z
CUST-1001235,jane.smith@example.com,+1-555-987-6543,Jane,Smith,active,regular,2023-02-15T10:30:00Z,2023-02-15T10:30:00Z,2024-03-20T14:22:15Z,2024-03-20T14:22:15Z
```

### 3. Parquet Format (Batch Only)

#### Characteristics
- Columnar storage format
- Highly compressed
- Efficient for analytical queries
- Native support for nested structures
- Schema enforced

#### Schema Definition
Parquet schemas automatically enforce data types defined in JSON schemas.

#### Nested Structure Support
Parquet natively supports nested arrays and structs:

```
message Order {
  required binary order_id (UTF8);
  required binary customer_id (UTF8);
  required int64 order_date (TIMESTAMP(MILLIS,true));
  required binary order_status (UTF8);

  repeated group order_items {
    required binary line_item_id (UTF8);
    required binary product_id (UTF8);
    required int32 quantity;
    required double unit_price;
    required double line_total;
  }

  required double subtotal;
  required double total_amount;
}
```

#### Advantages for Batch Processing
- 5-10x compression vs CSV
- Fast columnar scanning
- Predicate pushdown
- Native AWS Athena/Glue support

### 4. Kafka Message Format

#### Message Structure
```json
{
  "key": "PROD-12345",
  "value": {
    "event_type": "inventory_updated",
    "event_timestamp": "2024-03-20T14:22:15Z",
    "data": {
      // Entity data
    }
  },
  "headers": {
    "source": "warehouse_management",
    "correlation_id": "corr_123456",
    "event_version": "1.0"
  },
  "partition": 0,
  "offset": 1234567,
  "timestamp": 1710941535000
}
```

#### Partitioning Strategy

**Orders Topic:**
- **Key**: `customer_id`
- **Partitions**: 50 (for 1M/day = ~20K per partition)
- **Retention**: 7 days

**Inventory Topic:**
- **Key**: `product_id`
- **Partitions**: 20 (for 100K/day = ~5K per partition)
- **Retention**: 3 days

**Shipping Topic:**
- **Key**: `order_id`
- **Partitions**: 50
- **Retention**: 30 days (for tracking history)

#### Message Ordering
- Events with same key go to same partition (ordering guaranteed)
- event_timestamp used for event ordering in processing

## File Naming Conventions

### Batch Files

#### Product Catalog
```
product_catalog_YYYYMMDD_HHMMSS.{csv|json|parquet}
Example: product_catalog_20240320_083000.parquet
```

#### Customer
```
customer_YYYYMMDD_HHMMSS.{csv|json|parquet}
Example: customer_20240320_083000.csv
```

#### Inventory
```
inventory_YYYYMMDD_HHMMSS.{csv|json|parquet}
Example: inventory_20240320_083000.parquet
```

#### Orders (Batch)
```
orders_YYYYMMDD_HHMMSS.{csv|json|parquet}
Example: orders_20240320_083000.parquet
```

### S3 Bucket Structure
```
s3://data-pipeline-raw/
  ├── product_catalog/
  │   ├── year=2024/
  │   │   ├── month=03/
  │   │   │   ├── day=20/
  │   │   │   │   └── product_catalog_20240320_083000.parquet
  ├── customer/
  │   ├── year=2024/
  │   │   ├── month=03/
  │   │   │   ├── day=20/
  │   │   │   │   └── customer_20240320_083000.parquet
  ├── inventory/
  ├── orders/
  └── shipping/
```

## Compression

### Streaming (Kafka)
- **Compression**: Snappy or LZ4
- **Reason**: Low CPU overhead, good compression ratio

### Batch Files

#### CSV
- **Compression**: GZIP (.csv.gz)
- **Ratio**: 5-10x

#### JSON
- **Compression**: GZIP (.json.gz) or Snappy
- **Ratio**: 8-12x

#### Parquet
- **Compression**: Snappy (default) or GZIP
- **Ratio**: Built-in columnar compression (10-50x vs CSV)

## Data Delivery Guarantees

### Streaming (Kafka)
- **At-least-once delivery**: Use idempotency_key for deduplication
- **Exactly-once semantics**: Enable Kafka transactions (advanced)

### Batch
- **File atomicity**: Complete file upload before processing
- **Checksum validation**: MD5/SHA256 for file integrity

## Sample Data Files

Sample files are provided in:
```
/schemas/samples/
  ├── product_catalog_sample.csv
  ├── product_catalog_sample.json
  ├── customer_sample.csv
  ├── customer_sample.json
  ├── inventory_sample.csv
  ├── order_sample.json
  └── shipping_sample.json
```

## Migration Path

### Phase 1: Batch Only
- CSV/Parquet files uploaded to S3 daily
- Simple to implement
- Good for initial setup

### Phase 2: Hybrid
- Critical entities (orders, inventory) stream via Kafka
- Master data (catalog, customers) remain batch
- Best of both worlds

### Phase 3: Full Streaming
- All entities stream in real-time
- Batch loads only for historical data
- Maximum freshness

## Format Selection Guide

| Entity | Volume | Latency Requirement | Recommended Primary | Recommended Secondary |
|--------|--------|---------------------|---------------------|----------------------|
| Product Catalog | 10K/day | Daily | Parquet (batch) | JSON (streaming for updates) |
| Customer | 10K/day | Daily | Parquet (batch) | JSON (streaming for new signups) |
| Inventory | 100K/day | < 1 min | Kafka JSON | Parquet (daily snapshot) |
| Orders | 1M/day | < 5 sec | Kafka JSON | Parquet (daily archive) |
| Shipping | 1M/day | < 30 sec | Kafka JSON | Parquet (daily archive) |
