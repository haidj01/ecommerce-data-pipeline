# Entity Relationships and Data Flow

## Entity Relationship Diagram (ERD)

```
┌─────────────────┐
│  PRODUCT        │
│  CATALOG        │
│                 │
│ • product_id PK │◄──────────┐
│ • product_name  │            │
│ • categories    │            │
│ • price         │            │
│ • lifecycle     │            │
└─────────────────┘            │
        ▲                      │
        │                      │
        │                      │
        │                      │
┌───────┴────────┐      ┌─────┴────────────┐
│  INVENTORY     │      │  ORDER           │
│                │      │  LINE ITEMS      │
│ • inventory_id │      │                  │
│ • product_id FK│      │ • line_item_id   │
│ • warehouse_id │      │ • product_id FK  │
│ • qty_on_hand  │      │ • quantity       │
│ • qty_reserved │      │ • unit_price     │
│ • demand_fcst  │      └──────────────────┘
│ • supply_order │               │
└────────────────┘               │
                                 │
                                 │
┌─────────────────┐      ┌──────▼───────────┐
│  CUSTOMER       │      │  ORDER           │
│                 │      │  (HEADER)        │
│ • customer_id PK│◄─────┤                  │
│ • email (UQ)    │      │ • order_id PK    │
│ • name          │      │ • customer_id FK │
│ • addresses     │      │ • order_status   │
│ • account_status│      │ • payment_status │
└─────────────────┘      │ • total_amount   │
                         └──────┬───────────┘
                                │
                                │
                                │
                         ┌──────▼───────────┐
                         │  SHIPPING        │
                         │                  │
                         │ • shipment_id PK │
                         │ • order_id FK    │
                         │ • customer_id FK │
                         │ • tracking_num   │
                         │ • carrier        │
                         │ • ship_status    │
                         │ • tracking_events│
                         └──────────────────┘
```

## Relationship Details

### 1. Customer → Order (1:N)
- **Type**: One-to-Many
- **Foreign Key**: order.customer_id → customer.customer_id
- **Cardinality**: One customer can have many orders
- **Referential Integrity**: customer_id must exist in customer table

### 2. Order → Order Line Items (1:N)
- **Type**: One-to-Many (nested)
- **Structure**: Array within order record
- **Cardinality**: One order contains 1 to N line items
- **Integrity**: All line items part of parent order

### 3. Product → Order Line Items (1:N)
- **Type**: One-to-Many
- **Foreign Key**: order_items[].product_id → product_catalog.product_id
- **Cardinality**: One product can be in many order line items
- **Referential Integrity**: product_id must exist in product catalog

### 4. Product → Inventory (1:N)
- **Type**: One-to-Many
- **Foreign Key**: inventory.product_id → product_catalog.product_id
- **Cardinality**: One product can have inventory at multiple warehouses
- **Referential Integrity**: product_id must exist in product catalog

### 5. Order → Shipping (1:N)
- **Type**: One-to-Many
- **Foreign Keys**:
  - shipping.order_id → order.order_id
  - shipping.customer_id → customer.customer_id
- **Cardinality**: One order can have multiple shipments (partial fulfillment)
- **Referential Integrity**: Both order_id and customer_id must exist

## Data Flow Patterns

### Order Creation Flow

```
1. Customer Places Order
   ↓
2. Order Event (Kafka)
   {
     event_type: "order_created",
     data: {
       order_id: "ORD-xxx",
       customer_id: "CUST-xxx",
       order_items: [...]
     }
   }
   ↓
3. Inventory Reservation
   {
     event_type: "inventory_reserved",
     data: {
       product_id: "PROD-xxx",
       quantity_reserved: +2
     }
   }
   ↓
4. Payment Processing
   {
     event_type: "payment_authorized",
     order_id: "ORD-xxx"
   }
   ↓
5. Order Confirmation
   {
     event_type: "order_confirmed",
     order_status: "confirmed"
   }
```

### Fulfillment Flow

```
1. Order Processing Starts
   order_status: "confirmed" → "processing"
   ↓
2. Inventory Allocation
   - Pick items from warehouse
   - Update inventory:
     quantity_on_hand: -2
     quantity_reserved: -2
   ↓
3. Shipment Creation
   {
     event_type: "shipment_created",
     shipment_id: "SHIP-xxx",
     order_id: "ORD-xxx",
     tracking_number: "1Z999..."
   }
   ↓
4. Order Status Update
   order_status: "processing" → "shipped"
   ↓
5. Shipping Tracking Updates
   tracking_events: [
     {status: "picked_up", ...},
     {status: "in_transit", ...},
     {status: "delivered", ...}
   ]
   ↓
6. Delivery Confirmation
   order_status: "shipped" → "delivered"
   shipment_status: "in_transit" → "delivered"
```

### Inventory Update Flow

```
1. Reorder Point Triggered
   quantity_available <= reorder_point
   ↓
2. Purchase Order Created
   supply_on_order: +200
   ↓
3. Shipment Received
   {
     event_type: "shipment_received",
     quantity: 200
   }
   ↓
4. Inventory Restocked
   quantity_on_hand: +200
   quantity_in_transit: -200 (if tracked)
   supply_on_order: -200
   inventory_status: "low_stock" → "in_stock"
```

## Key Metrics by Entity

### Product Catalog Metrics
- Active products count
- Products by category
- Price distribution
- Lifecycle status distribution

### Customer Metrics
- Total customers
- Active vs inactive
- Customer segment distribution
- Average customer lifetime value
- Churn rate

### Inventory Metrics
- Total inventory value
- Stockout risk products (high risk score)
- Low stock products (qty <= reorder_point)
- Inventory turnover rate
- Days of supply by product
- Demand vs supply gap

### Order Metrics
- Orders per day
- Average order value
- Order status distribution
- Payment success rate
- Orders by channel
- Cancellation rate

### Shipping Metrics
- On-time delivery rate
- Average delivery time
- Shipments by carrier
- Failed delivery rate
- Tracking accuracy

## Aggregation Patterns

### Customer 360 View
```sql
Combine:
- customer (profile)
- orders (transaction history)
- shipping (delivery history)
- inventory (product availability for wishlist)

Result: Complete customer view with purchase patterns
```

### Product Performance
```sql
Combine:
- product_catalog (product info)
- order_line_items (sales data)
- inventory (stock levels)

Result: Product sales, turnover, stock health
```

### Fulfillment Efficiency
```sql
Combine:
- orders (order placement)
- inventory (picking efficiency)
- shipping (delivery performance)

Result: Order-to-delivery time, fulfillment accuracy
```

## Data Consistency Rules

### Cross-Entity Validation

1. **Order Placement**
   - Customer must exist (customer_id validation)
   - All products must exist (product_id validation)
   - Inventory must be available (quantity check)

2. **Inventory Reservation**
   - quantity_reserved increases match order quantities
   - quantity_available remains >= 0
   - Product must be active

3. **Shipment Creation**
   - Order must exist and be in valid status
   - Customer must exist
   - Shipment items must match order items

### State Consistency

1. **Order + Inventory**
   ```
   When order confirmed:
     → inventory.quantity_reserved += order.quantity

   When order shipped:
     → inventory.quantity_on_hand -= order.quantity
     → inventory.quantity_reserved -= order.quantity

   When order cancelled:
     → inventory.quantity_reserved -= order.quantity
   ```

2. **Order + Shipping**
   ```
   When shipment delivered:
     → order.order_status = "delivered"
     (delivery date lives only in shipment.actual_delivery_date; join on order_id)
   ```

3. **Customer + Orders**
   ```
   When order completed:
     → customer.customer_lifetime_value += order.total_amount
     → customer.total_orders += 1
     → customer.last_order_date = order.order_date
   ```

## Event Sequencing

### Guaranteed Ordering
- Events with same key (customer_id, order_id, product_id) processed in order
- Timestamp-based ordering for cross-key dependencies
- Idempotency keys prevent duplicate processing

### Out-of-Order Handling
- Use event_timestamp for logical ordering
- Buffer late-arriving events
- Reconciliation jobs for consistency
