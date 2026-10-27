-- Customer Registry Database Schema
-- Single source of truth for customer data (registration + updates)
-- Dev: local PostgreSQL (Docker), AWS: RDS PostgreSQL db.t3.micro

-- Drop existing table if needed (for dev/testing)
DROP TABLE IF EXISTS customer_registry;

-- Customer registry table
CREATE TABLE customer_registry (
    -- Primary identifiers
    customer_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,

    -- Basic information
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,

    -- Account details
    customer_segment VARCHAR(20) CHECK (customer_segment IN ('new', 'regular', 'premium', 'vip', 'at_risk', 'churned')),
    account_status VARCHAR(20) NOT NULL CHECK (account_status IN ('active', 'inactive', 'suspended', 'closed')),

    -- Complex fields (JSONB for nested structures)
    billing_address JSONB,
    shipping_addresses JSONB,
    payment_methods JSONB,
    marketing_consent JSONB,

    -- Metadata
    language_preference VARCHAR(2) CHECK (language_preference ~ '^[a-z]{2}$'),
    referral_source VARCHAR(20) CHECK (referral_source IN ('organic', 'google_ads', 'facebook_ads', 'referral', 'email', 'direct', 'other')),
    registration_date TIMESTAMP NOT NULL,

    -- Tracking timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_customer_email ON customer_registry(email);
CREATE INDEX idx_customer_segment ON customer_registry(customer_segment);
CREATE INDEX idx_account_status ON customer_registry(account_status);
CREATE INDEX idx_registration_date ON customer_registry(registration_date);
CREATE INDEX idx_last_updated_at ON customer_registry(last_updated_at);

-- JSONB indexes for nested queries
CREATE INDEX idx_billing_address_gin ON customer_registry USING GIN (billing_address);
CREATE INDEX idx_shipping_addresses_gin ON customer_registry USING GIN (shipping_addresses);

-- Trigger to auto-update last_updated_at
CREATE OR REPLACE FUNCTION update_last_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_last_updated_at
    BEFORE UPDATE ON customer_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated_at();

-- Comments for documentation
COMMENT ON TABLE customer_registry IS 'Single source of truth for customer data. Registration producer writes new customers; batch update DAG modifies existing customers (10% daily).';
COMMENT ON COLUMN customer_registry.customer_id IS 'Unique customer identifier, pattern: CUST-[0-9]+';
COMMENT ON COLUMN customer_registry.email IS 'Unique email address, used for identity resolution';
COMMENT ON COLUMN customer_registry.billing_address IS 'Billing address: {street_address, apartment, city, state, postal_code, country}';
COMMENT ON COLUMN customer_registry.shipping_addresses IS 'Array of shipping addresses: [{address_id, is_default, street_address, city, state, postal_code, country}]';
COMMENT ON COLUMN customer_registry.payment_methods IS 'Array of tokenized payment methods: [{payment_method_id, type, last_four, is_default}]';
COMMENT ON COLUMN customer_registry.marketing_consent IS 'Marketing preferences: {email_marketing, sms_marketing, push_notifications}';
COMMENT ON COLUMN customer_registry.last_updated_at IS 'Auto-updated on every UPDATE via trigger';
