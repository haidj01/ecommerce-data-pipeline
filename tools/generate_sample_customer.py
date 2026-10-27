#!/usr/bin/env python3
"""
Sample Customer Data Generator

Generates realistic sample customer data for testing the data pipeline.
Follows the schema defined in schemas/customer_schema.json

Usage:
    python generate_sample_customer.py [--count 100] [--output output.csv]
"""

import argparse
import csv
import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    print("Error: faker library is required. Install with: pip install faker")
    exit(1)


# Customer segment distribution (weighted)
CUSTOMER_SEGMENT_WEIGHTS = {
    "new": 0.15,        # 15% new customers
    "regular": 0.40,    # 40% regular customers
    "premium": 0.25,    # 25% premium customers
    "vip": 0.10,        # 10% VIP customers
    "at_risk": 0.07,    # 7% at-risk customers
    "churned": 0.03     # 3% churned customers
}

# Account status distribution
ACCOUNT_STATUS_WEIGHTS = {
    "active": 0.80,      # 80% active
    "inactive": 0.12,    # 12% inactive
    "suspended": 0.05,   # 5% suspended
    "closed": 0.03       # 3% closed
}

# Referral source distribution
REFERRAL_SOURCES = ["organic", "google_ads", "facebook_ads", "referral", "email", "direct", "other"]
REFERRAL_SOURCE_WEIGHTS = [0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05]

# Payment method types
PAYMENT_TYPES = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]

# Language preferences (ISO 639-1)
LANGUAGES = ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"]


class CustomerDataGenerator:
    """Generate sample customer data following the schema"""

    def __init__(self, count: int = 100):
        self.count = count
        self.used_emails = set()
        self.customer_id_counter = random.randint(1000000, 9999999)

    def generate_unique_customer_id(self) -> str:
        """Generate unique customer ID following pattern ^CUST-[0-9]+$"""
        self.customer_id_counter += 1
        return f"CUST-{self.customer_id_counter}"

    def generate_unique_email(self, first_name: str, last_name: str) -> str:
        """Generate unique email address"""
        while True:
            # Generate various email patterns
            patterns = [
                f"{first_name.lower()}.{last_name.lower()}@{fake.free_email_domain()}",
                f"{first_name.lower()}{last_name.lower()}@{fake.free_email_domain()}",
                f"{first_name.lower()}_{last_name.lower()}@{fake.free_email_domain()}",
                f"{first_name.lower()}{random.randint(1, 999)}@{fake.free_email_domain()}"
            ]
            email = random.choice(patterns)

            if email not in self.used_emails:
                self.used_emails.add(email)
                return email

    def select_customer_segment(self) -> str:
        """Select customer segment based on weighted distribution"""
        segments = list(CUSTOMER_SEGMENT_WEIGHTS.keys())
        weights = list(CUSTOMER_SEGMENT_WEIGHTS.values())
        return random.choices(segments, weights=weights)[0]

    def select_account_status(self, segment: str) -> str:
        """Select account status based on segment"""
        # Churned segment should have closed/inactive status
        if segment == "churned":
            return random.choice(["closed", "inactive"])

        # At-risk might be inactive
        if segment == "at_risk":
            return random.choice(["active", "inactive", "suspended"])

        # Others are mostly active
        statuses = list(ACCOUNT_STATUS_WEIGHTS.keys())
        weights = list(ACCOUNT_STATUS_WEIGHTS.values())
        return random.choices(statuses, weights=weights)[0]

    def generate_phone(self) -> str:
        """Generate phone number (70% probability)"""
        if random.random() < 0.7:
            # E.164 format: +[country code][number]
            country_codes = [1, 44, 49, 33, 81, 82]  # US, UK, DE, FR, JP, KR
            country = random.choice(country_codes)
            number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
            return f"+{country}{number}"
        return ""

    def generate_date_of_birth(self) -> str:
        """Generate date of birth (must be at least 13 years ago, 80% probability)"""
        if random.random() < 0.8:
            # Generate age between 13 and 80 years
            years_ago = random.randint(13, 80)
            dob = datetime.now() - timedelta(days=years_ago * 365 + random.randint(0, 365))
            return dob.strftime("%Y-%m-%d")
        return ""

    def generate_billing_address(self) -> str:
        """Generate billing address JSON (70% probability)"""
        if random.random() < 0.7:
            address = {
                "street_address": fake.street_address(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postal_code": fake.postcode(),
                "country": fake.country_code()
            }
            # 30% chance to include apartment
            if random.random() < 0.3:
                address["apartment"] = f"Apt {random.randint(1, 999)}"

            return json.dumps(address)
        return ""

    def generate_shipping_addresses(self) -> str:
        """Generate shipping addresses array (60% probability)"""
        if random.random() < 0.6:
            num_addresses = random.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
            addresses = []

            for i in range(num_addresses):
                address = {
                    "address_id": f"ADDR-{random.randint(1000, 9999)}",
                    "is_default": i == 0,  # First address is default
                    "street_address": fake.street_address(),
                    "city": fake.city(),
                    "state": fake.state_abbr(),
                    "postal_code": fake.postcode(),
                    "country": fake.country_code()
                }
                addresses.append(address)

            return json.dumps(addresses)
        return ""

    def generate_payment_methods(self) -> str:
        """Generate payment methods array (70% probability)"""
        if random.random() < 0.7:
            num_methods = random.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
            methods = []

            for i in range(num_methods):
                method = {
                    "payment_method_id": f"PM-{random.randint(10000, 99999)}",
                    "type": random.choice(PAYMENT_TYPES),
                    "last_four": f"{random.randint(1000, 9999)}",
                    "is_default": i == 0  # First method is default
                }
                methods.append(method)

            return json.dumps(methods)
        return ""

    def generate_marketing_consent(self) -> str:
        """Generate marketing consent preferences (80% probability)"""
        if random.random() < 0.8:
            consent = {
                "email_marketing": random.choice([True, False]),
                "sms_marketing": random.choice([True, False]),
                "push_notifications": random.choice([True, False])
            }
            return json.dumps(consent)
        return ""

    def generate_timestamps(self, segment: str) -> tuple:
        """Generate registration_date, created_at, updated_at, event_timestamp"""
        # Registration date based on segment
        if segment == "new":
            # New customers registered in last month
            registration_date = fake.date_time_between(start_date="-1M", end_date="now")
        elif segment == "churned":
            # Churned customers registered long ago
            registration_date = fake.date_time_between(start_date="-2y", end_date="-6M")
        elif segment == "vip":
            # VIP customers are long-term customers
            registration_date = fake.date_time_between(start_date="-3y", end_date="-6M")
        else:
            # Regular, premium, at-risk customers
            registration_date = fake.date_time_between(start_date="-2y", end_date="-1M")

        # created_at is same as registration_date
        created_at = registration_date

        # updated_at is between registration and now
        updated_at = fake.date_time_between(start_date=registration_date, end_date="now")

        # event_timestamp is the same as updated_at
        event_timestamp = updated_at

        return (
            registration_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            event_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def generate_customer(self) -> Dict[str, Any]:
        """Generate a single customer record"""
        # Basic info
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = self.generate_unique_email(first_name, last_name)

        # Segment and status
        segment = self.select_customer_segment()
        account_status = self.select_account_status(segment)

        # Timestamps
        registration_date, created_at, updated_at, event_timestamp = self.generate_timestamps(segment)

        # Optional fields
        phone = self.generate_phone()
        date_of_birth = self.generate_date_of_birth()
        billing_address = self.generate_billing_address()
        shipping_addresses = self.generate_shipping_addresses()
        payment_methods = self.generate_payment_methods()
        marketing_consent = self.generate_marketing_consent()

        # Language preference (60% probability)
        language_preference = random.choice(LANGUAGES) if random.random() < 0.6 else ""

        # Referral source (80% probability)
        referral_source = ""
        if random.random() < 0.8:
            referral_source = random.choices(REFERRAL_SOURCES, weights=REFERRAL_SOURCE_WEIGHTS)[0]

        # Build customer record
        customer = {
            "customer_id": self.generate_unique_customer_id(),
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
            "customer_segment": segment,
            "account_status": account_status,
            "billing_address": billing_address,
            "shipping_addresses": shipping_addresses,
            "payment_methods": payment_methods,
            "marketing_consent": marketing_consent,
            "registration_date": registration_date,
            "language_preference": language_preference,
            "referral_source": referral_source,
            "created_at": created_at,
            "updated_at": updated_at,
            "event_timestamp": event_timestamp
        }

        return customer

    def generate_customers(self) -> List[Dict[str, Any]]:
        """Generate complete customer dataset"""
        print(f"Generating {self.count} sample customers...")
        customers = [self.generate_customer() for _ in range(self.count)]
        print(f"✓ Generated {len(customers)} customers")
        return customers

    def save_to_csv(self, customers: List[Dict[str, Any]], output_file: str):
        """Save customers to CSV file"""
        if not customers:
            print("Error: No customers to save")
            return

        # Define field order based on schema
        fieldnames = [
            "customer_id", "email", "phone", "first_name", "last_name", "date_of_birth",
            "customer_segment", "account_status", "billing_address", "shipping_addresses",
            "payment_methods", "marketing_consent", "registration_date", "language_preference",
            "referral_source", "created_at", "updated_at", "event_timestamp"
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(customers)

        print(f"✓ Saved to {output_file}")

        # Print summary statistics
        self.print_statistics(customers)

    def print_statistics(self, customers: List[Dict[str, Any]]):
        """Print summary statistics of generated customers"""
        print("\n=== Customer Statistics ===")
        print(f"Total Customers: {len(customers)}")

        # Customer segment distribution
        segment_counts = {}
        for c in customers:
            segment = c['customer_segment']
            segment_counts[segment] = segment_counts.get(segment, 0) + 1

        print("\nCustomer Segment Distribution:")
        for segment, count in sorted(segment_counts.items()):
            pct = (count / len(customers)) * 100
            print(f"  {segment}: {count} ({pct:.1f}%)")

        # Account status distribution
        status_counts = {}
        for c in customers:
            status = c['account_status']
            status_counts[status] = status_counts.get(status, 0) + 1

        print("\nAccount Status Distribution:")
        for status, count in sorted(status_counts.items()):
            pct = (count / len(customers)) * 100
            print(f"  {status}: {count} ({pct:.1f}%)")

        # Referral source distribution
        referral_counts = {}
        for c in customers:
            source = c['referral_source'] if c['referral_source'] else "unknown"
            referral_counts[source] = referral_counts.get(source, 0) + 1

        print("\nReferral Source Distribution:")
        for source, count in sorted(referral_counts.items()):
            pct = (count / len(customers)) * 100
            print(f"  {source}: {count} ({pct:.1f}%)")

        # Data quality checks
        print("\n=== Data Quality Checks ===")
        unique_ids = len(set(c['customer_id'] for c in customers))
        print(f"✓ Unique customer_ids: {unique_ids}/{len(customers)}")

        unique_emails = len(set(c['email'] for c in customers))
        print(f"✓ Unique emails: {unique_emails}/{len(customers)}")

        # Check age validation (at least 13 years old)
        age_violations = 0
        for c in customers:
            if c['date_of_birth']:
                dob = datetime.strptime(c['date_of_birth'], "%Y-%m-%d")
                age = (datetime.now() - dob).days / 365.25
                if age < 13:
                    age_violations += 1
        print(f"✓ Age validation violations (< 13 years): {age_violations}/{len(customers)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample customer data for testing"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of customers to generate (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="schemas/samples/customer_generated.csv",
        help="Output CSV file path (default: schemas/samples/customer_generated.csv)"
    )

    args = parser.parse_args()

    # Add Unix timestamp to output filename
    output_path = Path(args.output)
    timestamp = int(time.time())
    output_filename = f"{output_path.stem}_{timestamp}{output_path.suffix}"
    output_file = output_path.parent / output_filename

    # Generate customers
    generator = CustomerDataGenerator(count=args.count)
    customers = generator.generate_customers()

    # Save to CSV
    generator.save_to_csv(customers, str(output_file))

    print("\n✓ Sample customer generation complete!")


if __name__ == "__main__":
    main()
