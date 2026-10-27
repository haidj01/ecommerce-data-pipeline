# Additional Business Validation Rules

## Business Context
These validation rules complement the existing data quality rules with a focus on **business risk management**, **fraud prevention**, **customer experience protection**, and **revenue integrity**.

## 5 Critical Business Validation Rules

### 1. Fraud Prevention - Excessive Discount Rule

**Business Rationale:**
- Excessive discounts can indicate fraudulent activity (employee fraud, coupon abuse, system exploit)
- Protect company revenue from unauthorized or erroneous discount application
- Average discount rate in e-commerce is 10-20%; anything above 50% is highly suspicious

**Validation Logic:**
```
Rule: discount_total must not exceed 50% of subtotal

Calculation:
  discount_percentage = (discount_total / subtotal) × 100

Severity Levels:
  - CRITICAL (auto-reject): discount_percentage > 80%
  - HIGH (auto-flag for review): discount_percentage > 50%
  - WARNING (log for analysis): discount_percentage > 30%

Exception Handling:
  - Allow exceptions for pre-approved promotional campaigns (require campaign_id)
  - Allow exceptions for manager-approved special deals (require approval_code)
```

**Impact if Violated:**
- **Revenue Loss**: Unauthorized 80% discount on $1M daily orders = $640K daily revenue loss
- **Fraud Risk**: Organized discount fraud schemes
- **Margin Erosion**: Below-cost selling

**Implementation:**
```sql
-- Pre-ingestion check
SELECT
  order_id,
  subtotal,
  discount_total,
  ROUND((discount_total / NULLIF(subtotal, 0)) * 100, 2) as discount_percentage
FROM orders
WHERE (discount_total / NULLIF(subtotal, 0)) > 0.50
  AND campaign_id IS NULL
  AND approval_code IS NULL
```

**Business Owner:** Finance Team, Fraud Prevention Team

---

### 2. Inventory Availability Validation at Order Placement

**Business Rationale:**
- Prevent overselling and customer disappointment
- Maintain accurate inventory levels and demand forecasting
- Reduce order cancellation rate and improve customer satisfaction
- Overselling leads to backorders, delayed shipments, and negative reviews

**Validation Logic:**
```
Rule: For each line item, ordered quantity must not exceed available inventory at order placement

Check at order creation:
  For each order_item in order_items:
    ordered_qty = order_item.quantity
    available_qty = inventory.quantity_available
      WHERE inventory.product_id = order_item.product_id
        AND inventory.warehouse_id = order_item.warehouse_id

    IF ordered_qty > available_qty THEN
      REJECT order with error: "Insufficient inventory for {product_name}"

Severity: CRITICAL (auto-reject order)

Exception Handling:
  - Allow backorders for products with inventory_status = "in_stock"
    AND supply_on_order > 0
    AND expected_delivery_date within 7 days
  - Require explicit customer consent for backorder items
```

**Impact if Violated:**
- **Customer Dissatisfaction**: Oversold items lead to order cancellations
- **Operational Cost**: Manual intervention to resolve overselling issues
- **Reputation Damage**: Negative reviews for "out of stock after ordering"
- **Lost Sales**: Customer abandonment after cancellation

**Example Scenario:**
```
Product: PROD-12345 (Popular T-Shirt)
Available Inventory: 50 units
Incoming Orders:
  - Order 1: 30 units (ACCEPTED)
  - Order 2: 25 units (REJECTED - only 20 available)

Without this rule: Both orders accepted → overselling by 5 units → customer disappointment
```

**Implementation:**
```sql
-- Real-time validation during order placement
SELECT
  o.order_id,
  oi.product_id,
  oi.quantity as ordered_qty,
  i.quantity_available,
  CASE
    WHEN oi.quantity > i.quantity_available THEN 'REJECT'
    ELSE 'ACCEPT'
  END as validation_status
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN inventory i ON oi.product_id = i.product_id
  AND oi.warehouse_id = i.warehouse_id
WHERE oi.quantity > i.quantity_available
```

**Business Owner:** Warehouse Operations, Customer Experience Team

---

### 3. High-Risk Order Auto-Flagging (Fraud Score Threshold)

**Business Rationale:**
- Automated fraud detection to prevent fraudulent transactions
- Reduce chargebacks and payment disputes
- Protect customer accounts from unauthorized purchases
- Industry standard: fraud score > 70 indicates high risk

**Validation Logic:**
```
Rule: Orders with fraud_score > threshold must be flagged for manual review

Severity Levels:
  - CRITICAL (hold shipment): fraud_score > 80
  - HIGH (flag for review): fraud_score > 70
  - MEDIUM (enhanced monitoring): fraud_score > 50

Required Actions by Threshold:
  fraud_score > 80:
    - Set order_status = "pending_verification"
    - Hold inventory reservation
    - Send to fraud team for manual review
    - Require customer verification (phone call, email confirmation)
    - Do NOT ship until cleared

  fraud_score > 70:
    - Flag order in review queue
    - Enhanced address verification
    - Contact customer to confirm order
    - Proceed only after confirmation

  fraud_score > 50:
    - Log for post-fulfillment review
    - Enhanced delivery signature requirement
    - Monitor for chargeback
```

**Impact if Violated:**
- **Financial Loss**: Chargebacks cost $15-25 per incident + product loss
- **Payment Processor Risk**: High chargeback rate can lead to merchant account suspension
- **Reputation Damage**: Fraudulent account usage damages customer trust
- **Regulatory Risk**: Payment Card Industry (PCI) compliance violations

**Example Metrics:**
```
Daily Orders: 1,000,000
Fraud Rate without rule: 0.5% (5,000 fraudulent orders)
Average Order Value: $150
Daily Fraud Loss: 5,000 × $150 = $750,000

With auto-flagging:
  - Detect 80% of fraud (4,000 orders)
  - Prevent $600,000 daily fraud loss
  - Monthly savings: $18M
```

**Implementation:**
```sql
-- Post-order creation check
UPDATE orders
SET order_status = CASE
  WHEN fraud_score > 80 THEN 'pending_verification'
  WHEN fraud_score > 70 THEN 'flagged_for_review'
  ELSE order_status
END,
review_required = CASE
  WHEN fraud_score > 70 THEN true
  ELSE false
END
WHERE fraud_score > 70
  AND order_status = 'pending'
```

**Business Owner:** Fraud Prevention Team, Risk Management

---

### 4. Product Lifecycle Order Prevention

**Business Rationale:**
- Prevent orders for products that should not be sold (discontinued, archived)
- Maintain catalog accuracy and customer experience
- Avoid fulfillment issues with discontinued products
- Ensure only active products are available for purchase

**Validation Logic:**
```
Rule: Orders must not contain products with lifecycle_status in ["discontinued", "end_of_life", "archived"]

Validation at order creation:
  For each order_item in order_items:
    product_lifecycle = product_catalog.lifecycle_status
      WHERE product_catalog.product_id = order_item.product_id

    IF product_lifecycle IN ["discontinued", "end_of_life", "archived"] THEN
      REJECT order with error: "Product {product_id} is no longer available"

    IF product_lifecycle = "pre_launch" THEN
      REJECT order with error: "Product {product_id} is not yet available"
      (Exception: allow if customer has early_access_flag = true)

Severity: CRITICAL (auto-reject order)

Valid product lifecycle for orders:
  - "active" (standard purchases)
  - "pre_launch" with early_access (limited releases)
```

**Impact if Violated:**
- **Customer Dissatisfaction**: Ordering products that cannot be fulfilled
- **Operational Inefficiency**: Manual cancellation and customer communication
- **Inventory Confusion**: Attempting to pick discontinued items
- **Reputation Risk**: Selling products past end-of-life date

**Example Scenario:**
```
Product: PROD-33333 (Running Shoes)
Current Status: lifecycle_status = "discontinued"
Catalog Display: Should be hidden from storefront

If order placed:
  - Without rule: Order accepted → warehouse cannot fulfill → manual cancellation
  - With rule: Order rejected immediately → customer sees "no longer available"
```

**Implementation:**
```sql
-- Pre-order validation
SELECT
  o.order_id,
  oi.product_id,
  p.lifecycle_status,
  p.is_active,
  CASE
    WHEN p.lifecycle_status IN ('discontinued', 'end_of_life', 'archived')
      THEN 'REJECT - Product discontinued'
    WHEN p.lifecycle_status = 'pre_launch' AND c.early_access_flag != true
      THEN 'REJECT - Product not yet available'
    WHEN p.is_active = false
      THEN 'REJECT - Product inactive'
    ELSE 'ACCEPT'
  END as validation_status
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN product_catalog p ON oi.product_id = p.product_id
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE p.lifecycle_status NOT IN ('active', 'pre_launch')
   OR (p.lifecycle_status = 'pre_launch' AND c.early_access_flag != true)
   OR p.is_active = false
```

**Business Owner:** Catalog Management Team, Product Team

---

### 5. Suspended Account Order Prevention

**Business Rationale:**
- Prevent orders from customers with suspended or closed accounts
- Enforce account status business rules and compliance
- Reduce payment risk from problematic accounts
- Accounts suspended for reason: fraud, payment issues, TOS violations

**Validation Logic:**
```
Rule: Orders cannot be placed by customers with account_status in ["suspended", "closed"]

Validation at order creation:
  customer_status = customers.account_status
    WHERE customers.customer_id = order.customer_id

  IF customer_status = "closed" THEN
    REJECT order with error: "Account closed. Please contact customer support."

  IF customer_status = "suspended" THEN
    REJECT order with error: "Account suspended. Please resolve account issues before placing orders."

  IF customer_status = "inactive" THEN
    WARNING: "Account inactive - may require reactivation"
    Allow order but flag for review

Severity: CRITICAL (auto-reject)

Valid account_status for orders:
  - "active" (standard orders)
  - "inactive" (allow with warning - dormant customers)
```

**Impact if Violated:**
- **Payment Risk**: Suspended accounts often have payment/chargeback history
- **Compliance Risk**: Accounts suspended for fraud/TOS violations
- **Resource Waste**: Processing orders that will be cancelled
- **Customer Confusion**: Unclear why order was cancelled post-payment

**Example Scenarios:**
```
Scenario 1: Fraud Suspension
  - Customer CUST-555 suspended for chargebacks
  - account_status = "suspended"
  - Attempts to place $500 order
  - Without rule: Order placed → high fraud risk → manual review
  - With rule: Order blocked immediately → prevents fraud attempt

Scenario 2: Account Closure
  - Customer CUST-999 closed account per GDPR request
  - account_status = "closed"
  - Attempts to place order (account still has stored credentials)
  - Without rule: Order placed → privacy violation → manual intervention
  - With rule: Order blocked → customer must create new account
```

**Implementation:**
```sql
-- Pre-order validation
SELECT
  o.order_id,
  o.customer_id,
  c.account_status,
  CASE
    WHEN c.account_status = 'closed'
      THEN 'REJECT - Account closed'
    WHEN c.account_status = 'suspended'
      THEN 'REJECT - Account suspended'
    WHEN c.account_status = 'inactive'
      THEN 'WARNING - Account inactive'
    ELSE 'ACCEPT'
  END as validation_status,
  c.account_suspension_reason
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE c.account_status IN ('suspended', 'closed')
```

**Business Owner:** Customer Service, Compliance Team, Risk Management

---

## Summary Table

| Rule # | Rule Name | Business Impact | Severity | Estimated Cost if Violated |
|--------|-----------|----------------|----------|---------------------------|
| 1 | Excessive Discount Prevention | Revenue protection, fraud prevention | CRITICAL | $640K/day (80% discount on $1M orders) |
| 2 | Inventory Availability Check | Customer satisfaction, operational efficiency | CRITICAL | 5-10% order cancellation rate |
| 3 | Fraud Score Threshold | Fraud prevention, chargeback reduction | CRITICAL | $18M/month in prevented fraud |
| 4 | Product Lifecycle Validation | Catalog accuracy, fulfillment efficiency | CRITICAL | Manual handling of 100-500 orders/day |
| 5 | Suspended Account Prevention | Compliance, payment risk reduction | CRITICAL | Increased fraud/chargeback exposure |

## Implementation Priority

1. **Immediate (Week 1)**: Rule #2 (Inventory), Rule #5 (Suspended Account) - Prevent operational issues
2. **High Priority (Week 2)**: Rule #3 (Fraud Score), Rule #1 (Excessive Discount) - Financial protection
3. **Standard Priority (Week 3)**: Rule #4 (Product Lifecycle) - Catalog integrity

## Monitoring and Alerting

Each rule should have:
- Real-time rejection counter (metric)
- Daily summary report of blocked transactions
- False positive tracking
- Exception/override audit log
- Business impact dashboard

## Review Cycle

- **Monthly**: Review rejection rates and false positives
- **Quarterly**: Adjust thresholds based on business trends
- **Annually**: Comprehensive rule effectiveness analysis
