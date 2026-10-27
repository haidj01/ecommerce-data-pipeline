# Data Quality Validation Rules

## Overview
This document consolidates all data quality rules for the e-commerce data pipeline to ensure data integrity, consistency, and reliability.

## Cross-Entity Referential Integrity

### Customer Uniqueness (Critical)
- **customer_id** must be globally unique across all customer records
- **email** must be unique across all customer records
- No duplicate customer_id or email combinations allowed
- Customer identity resolution strategy:
  - Primary: customer_id (exact match)
  - Secondary: email (for identity resolution)
  - Deduplication logic must run before data ingestion

### Product-Order Relationships
- All **product_id** references in orders must exist in product catalog
- All **product_id** references in inventory must exist in product catalog
- Orphaned product references are not allowed

### Order-Shipment Relationships
- All **order_id** references in shipments must exist in orders
- Shipment quantities cannot exceed order quantities
- Multiple shipments per order allowed (partial fulfillment)

### Customer-Order Relationships
- All **customer_id** references in orders must exist in customers
- All **customer_id** references in shipments must exist in customers

## Entity-Specific Validation Rules

### Product Catalog

#### Lifecycle Management
```
Valid transitions:
  pre_launch → active
  active → discontinued
  discontinued → end_of_life
  end_of_life → archived

Invalid transitions (must reject):
  archived → active
  end_of_life → active (without going through proper process)
```

#### Category Hierarchy
- **category_level_1** is required
- **category_level_2** is required
- **category_level_3** is optional (deepest level)
- Category hierarchy must be consistent
- Valid category_level_1 values: ["Apparel", "Electronics", "Home & Garden", "Sports & Outdoors", "Beauty & Health", "Books & Media"]

#### Pricing Rules
- **price** must be >= 0
- **cost** must be >= 0 (if provided)
- **price** should be >= **cost** (warn if violated, log for review)
- **currency** must be valid ISO 4217 code

#### Status Consistency
- If **lifecycle_status** in ["discontinued", "end_of_life", "archived"], then **is_active** must be false
- If **lifecycle_status** = "active", then **is_active** should be true

### Customer

#### Unique Identification
- **customer_id** must match pattern: `^CUST-[0-9]+$`
- **email** must be valid email format
- **email** must be unique (no duplicates)

#### Age Validation
- **date_of_birth** must be at least 13 years ago (COPPA compliance)
- **date_of_birth** must not be in the future

#### Status Transitions
```
Valid account_status transitions:
  (new) → active
  active → inactive
  active → suspended
  inactive → active
  suspended → active
  active/inactive/suspended → closed

Invalid transitions:
  closed → any other status (accounts cannot be reopened)
```

#### Financial Consistency
- **customer_lifetime_value** should equal sum of all completed order totals
- Recalculated periodically from order history

### Inventory

#### Quantity Consistency
```
Required equation:
  quantity_available = quantity_on_hand - quantity_reserved

Validation:
  quantity_on_hand >= quantity_reserved (always)
  quantity_on_hand >= 0
  quantity_reserved >= 0
  quantity_available >= 0
  quantity_in_transit >= 0
  quantity_damaged >= 0
```

#### Inventory Value
```
Required equation:
  inventory_value = quantity_on_hand × unit_cost

Validation:
  inventory_value >= 0
  Recalculate on every inventory update
```

#### Status Derivation
```
Automated status calculation:
  - quantity_available = 0 → inventory_status = "out_of_stock"
  - quantity_available <= reorder_point → inventory_status = "low_stock"
  - quantity_available > reorder_point → inventory_status = "in_stock"
  - lifecycle_status = "discontinued" → inventory_status = "discontinued"
```

#### Demand/Supply Tracking
- Derived metrics (**demand_forecast_30d/90d**, **days_of_supply**, **stockout_risk_score**) are not in the source feed; they are computed in the Gold layer
- Real-time inventory accuracy must be within 1% tolerance
- Physical inventory counts should reconcile monthly

### Order

#### Financial Consistency
```
Required equations:
  subtotal = Σ(line_item.line_total)
  total_amount = subtotal - discount_total + tax_total + shipping_cost

Line item validation:
  line_total = (quantity × unit_price) - discount_amount
```

#### Order Status Flow
```
Valid status transitions:
  pending → confirmed → processing → shipped → delivered

Cancellation allowed at:
  - pending
  - confirmed
  - processing (before shipment)

Refund allowed at:
  - delivered
```

#### Payment-Order Consistency
- **payment_status** must be "paid" or "authorized" before **order_status** can be "processing"
- **order_status** = "delivered" requires **payment_status** = "paid"

#### Temporal Validation
- **order_date** <= current_timestamp
- **estimated_delivery_date** >= **order_date** (if present)
- Actual delivery date is tracked only in Shipping (see Shipping temporal validation)

#### Line Item Validation
- Each line item **quantity** must be > 0
- All **product_id** in order_items must exist in product catalog
- Line item **unit_price** should match product catalog price (warn if different)

### Shipping

#### Shipment Tracking
- **tracking_number** must be unique per carrier
- **shipment_id** must be globally unique

#### Status Flow
```
Valid status transitions:
  pending → picked → packed → labeled → shipped → in_transit → out_for_delivery → delivered

Failure branches:
  any_status → failed_delivery → (retry or returned)
  any_status → cancelled
```

#### Temporal Validation
- **shipped_date** <= **estimated_delivery_date** (if both present)
- **actual_delivery_date** >= **shipped_date** (if both present)
- If **actual_delivery_date** is set, **shipment_status** must be "delivered"

#### Package Consistency
- **package_count** must equal length of **package_details** array (if present)
- Sum of shipment item quantities must not exceed order quantities

#### International Shipments
- If **destination_address.country** ≠ **origin_address.country**, then **is_international** = true
- If **is_international** = true, **customs_declaration** is required

#### Tracking Events
- **tracking_events** array must be in chronological order
- Last tracking event status should align with **shipment_status**

## Data Quality Metrics

### Real-Time Monitoring
- Uniqueness violations: 0% tolerance
- Referential integrity violations: 0% tolerance
- Required field completeness: 100% for required fields
- Format validation pass rate: > 99.9%

### Batch Validation
- Cross-entity reconciliation: daily
- Calculated field verification: daily
- Historical consistency checks: weekly

## Validation Implementation

### Pre-Ingestion Checks
1. Schema validation (field types, required fields)
2. Format validation (regex patterns, date formats)
3. Range validation (min/max values)
4. Referential integrity checks

### Post-Ingestion Checks
1. Uniqueness constraints
2. Calculated field verification
3. Cross-entity relationship validation
4. Business rule validation

### Error Handling
- **Critical errors** (uniqueness, referential integrity): Reject record
- **Warnings** (price < cost): Accept with flag for review
- **Info** (missing optional fields): Accept and log

## Data Quality Reports

### Daily Reports
- Records processed
- Validation failures by type
- Referential integrity violations
- Data completeness metrics

### Weekly Reports
- Trend analysis of data quality metrics
- Top sources of data quality issues
- Recommendations for data source improvements
