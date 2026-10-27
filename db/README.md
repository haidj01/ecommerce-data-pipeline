# Customer Registry Database

PostgreSQL database serving as the single source of truth for customer data.

## Purpose

- **Registration flow:** Customer registration producer writes to both Kafka (`customer-events`) and this DB
- **Update flow:** Daily batch update DAG reads from this DB, generates updates, writes back to DB, and outputs JSONL to S3
- **Consistency:** Ensures customer data remains consistent between real-time and batch ingestion paths

## Schema

See `schema.sql` for the complete DDL.

**Table:** `customer_registry`
- Primary key: `customer_id` (VARCHAR(50), pattern: `CUST-[0-9]+`)
- Unique constraint: `email`
- JSONB fields: `billing_address`, `shipping_addresses`, `payment_methods`, `marketing_consent`
- Auto-updated: `last_updated_at` (trigger-based)

## Environment Setup

### Local Development (Docker)

```bash
# Start PostgreSQL container
docker run -d \
  --name postgres-customer-registry \
  -e POSTGRES_DB=customer_registry \
  -e POSTGRES_USER=pipeline_user \
  -e POSTGRES_PASSWORD=pipeline_password \
  -p 5432:5432 \
  postgres:15-alpine

# Initialize schema
docker cp schema.sql postgres-customer-registry:/tmp/
docker exec -it postgres-customer-registry psql -U pipeline_user -d customer_registry -f /tmp/schema.sql

# Or use psql from host
psql -h localhost -U pipeline_user -d customer_registry -f schema.sql
```

### AWS Demo (RDS)

- Instance type: `db.t3.micro` (cheapest for 1-day demo)
- Engine: PostgreSQL 15
- Database name: `customer_registry`
- Publicly accessible: No (access via VPC)
- Automated backups: Disabled (demo only)

```bash
# Initialize schema on RDS
psql -h <rds-endpoint> -U <admin-user> -d customer_registry -f schema.sql
```

## Airflow Connection

**Connection ID:** `postgres_default`

**Local (Docker):**
```
Conn Type: Postgres
Host: host.docker.internal (if Airflow is in Docker)
Schema: customer_registry
Login: pipeline_user
Password: pipeline_password
Port: 5432
```

**AWS (RDS):**
```
Conn Type: Postgres
Host: <rds-endpoint>
Schema: customer_registry
Login: <rds-user>
Password: <rds-password>
Port: 5432
```

## Usage Patterns

### Registration Producer (Python)

```python
import psycopg2
from faker import Faker

fake = Faker()
conn = psycopg2.connect(
    host="localhost",
    database="customer_registry",
    user="pipeline_user",
    password="pipeline_password"
)

customer_id = f"CUST-{fake.random_int(1000000, 9999999)}"
email = fake.email()

cursor = conn.cursor()
cursor.execute("""
    INSERT INTO customer_registry (
        customer_id, email, first_name, last_name,
        account_status, registration_date, created_at, last_updated_at
    ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())
""", (customer_id, email, fake.first_name(), fake.last_name(), 'active'))
conn.commit()
```

### Batch Update DAG (Airflow)

```python
from airflow.providers.postgres.hooks.postgres import PostgresHook

hook = PostgresHook(postgres_conn_id='postgres_default')

# Select 10% of customers randomly
customers = hook.get_records("""
    SELECT customer_id, email, first_name, last_name
    FROM customer_registry
    WHERE account_status = 'active'
    ORDER BY RANDOM()
    LIMIT (SELECT COUNT(*) * 0.1 FROM customer_registry)
""")

# Update with Faker-generated changes
for customer_id, email, first_name, last_name in customers:
    new_city = fake.city()
    hook.run("""
        UPDATE customer_registry
        SET billing_address = jsonb_set(
            COALESCE(billing_address, '{}'),
            '{city}',
            %s
        )
        WHERE customer_id = %s
    """, parameters=(f'"{new_city}"', customer_id))
```

## Data Retention

- No history table — updates overwrite in place
- For audit/compliance, consider enabling PostgreSQL WAL archiving (not in scope for this demo)
- Full history is preserved in the lakehouse (Silver: SCD Type 2)

## Teardown

```bash
# Local
docker stop postgres-customer-registry
docker rm postgres-customer-registry

# AWS
# Delete RDS instance via Console or Terraform destroy
```
