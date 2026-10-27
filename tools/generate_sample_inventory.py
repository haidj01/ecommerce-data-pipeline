#!/usr/bin/env python3
"""
Sample Inventory Data Generator

Generates realistic sample inventory data for testing the data pipeline.
Follows the schema defined in schemas/inventory_schema.json

Usage:
    python generate_sample_inventory.py [--count 100] [--output output.csv]
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


# Warehouse locations (US warehouses)
WAREHOUSES = [
    "WH-NYC-01", "WH-NYC-02",      # New York
    "WH-LAX-01", "WH-LAX-02",      # Los Angeles
    "WH-CHI-01",                    # Chicago
    "WH-DAL-01",                    # Dallas
    "WH-ATL-01",                    # Atlanta
    "WH-SEA-01",                    # Seattle
    "WH-MIA-01",                    # Miami
    "WH-DEN-01"                     # Denver
]

# Inventory status distribution
INVENTORY_STATUS_WEIGHTS = {
    "in_stock": 0.60,          # 60% in stock
    "low_stock": 0.25,         # 25% low stock
    "out_of_stock": 0.08,      # 8% out of stock
    "pending_arrival": 0.05,   # 5% pending arrival
    "discontinued": 0.02       # 2% discontinued
}

# Event type distribution
EVENT_TYPE_WEIGHTS = {
    "stock_update": 0.40,
    "stock_adjustment": 0.15,
    "reorder_triggered": 0.10,
    "shipment_received": 0.20,
    "physical_count": 0.10,
    "reservation_change": 0.05
}

# Change reason options
CHANGE_REASONS = [
    "order_fulfillment", "returns", "damage", "theft",
    "restock", "adjustment", "physical_count", "transfer"
]


class InventoryDataGenerator:
    """Generate sample inventory data following the schema"""

    def __init__(self, count: int = 100):
        self.count = count
        self.inventory_id_counter = random.randint(100000, 999999)
        self.product_id_counter = random.randint(10000, 99999)

    def generate_inventory_id(self) -> str:
        """Generate unique inventory ID following pattern ^INV-[0-9-]+$"""
        self.inventory_id_counter += 1
        today = datetime.now().strftime("%Y%m%d")
        return f"INV-{today}-{self.inventory_id_counter:06d}"

    def generate_product_id(self) -> str:
        """Generate product ID (would reference product catalog in real scenario)"""
        self.product_id_counter += 1
        return f"PROD-{self.product_id_counter}"

    def generate_warehouse_id(self) -> str:
        """Select random warehouse"""
        return random.choice(WAREHOUSES)

    def generate_location_code(self) -> str:
        """Generate warehouse location code (70% probability)"""
        if random.random() < 0.7:
            aisle = chr(random.randint(65, 90))  # A-Z
            shelf = random.randint(1, 20)
            bin_num = random.randint(1, 10)
            return f"{aisle}{shelf:02d}-B{bin_num}"
        return ""

    def select_inventory_status(self) -> str:
        """Select inventory status based on weighted distribution"""
        statuses = list(INVENTORY_STATUS_WEIGHTS.keys())
        weights = list(INVENTORY_STATUS_WEIGHTS.values())
        return random.choices(statuses, weights=weights)[0]

    def generate_quantities(self, status: str) -> tuple:
        """
        Generate quantity fields ensuring data quality rules:
        - quantity_available = quantity_on_hand - quantity_reserved
        - quantity_on_hand >= quantity_reserved
        """
        if status == "out_of_stock":
            quantity_on_hand = 0
            quantity_reserved = 0
            quantity_available = 0
        elif status == "low_stock":
            quantity_on_hand = random.randint(1, 50)
            quantity_reserved = random.randint(0, min(quantity_on_hand, 20))
            quantity_available = quantity_on_hand - quantity_reserved
        elif status == "pending_arrival":
            quantity_on_hand = random.randint(0, 30)
            quantity_reserved = random.randint(0, quantity_on_hand)
            quantity_available = quantity_on_hand - quantity_reserved
        elif status == "discontinued":
            quantity_on_hand = random.randint(0, 100)
            quantity_reserved = 0
            quantity_available = quantity_on_hand
        else:  # in_stock
            quantity_on_hand = random.randint(100, 1000)
            quantity_reserved = random.randint(0, min(quantity_on_hand // 4, 200))
            quantity_available = quantity_on_hand - quantity_reserved

        # Optional quantities
        quantity_in_transit = 0
        quantity_damaged = 0

        if status == "pending_arrival" or random.random() < 0.4:
            quantity_in_transit = random.randint(50, 500)

        if random.random() < 0.2:
            quantity_damaged = random.randint(1, min(quantity_on_hand // 10 + 1, 20))

        return (
            quantity_on_hand,
            quantity_reserved,
            quantity_available,
            quantity_in_transit,
            quantity_damaged
        )

    def generate_reorder_params(self, quantity_available: int, status: str) -> tuple:
        """Generate reorder point, reorder quantity, and safety stock"""
        # Reorder point typically 20-30% of max inventory
        if status == "discontinued":
            reorder_point = 0
            reorder_quantity = 0
            safety_stock = 0
        else:
            reorder_point = random.randint(30, 100)
            reorder_quantity = random.randint(100, 500)
            safety_stock = random.randint(10, 50) if random.random() < 0.7 else 0

        return reorder_point, reorder_quantity, safety_stock

    def calculate_inventory_status_from_quantities(
        self, quantity_available: int, reorder_point: int, discontinued: bool = False
    ) -> str:
        """
        Calculate inventory_status based on data quality rules:
        - out_of_stock if quantity_available = 0
        - low_stock if quantity_available <= reorder_point
        - in_stock otherwise
        """
        if discontinued:
            return "discontinued"
        if quantity_available == 0:
            return "out_of_stock"
        if quantity_available <= reorder_point:
            return "low_stock"
        return "in_stock"

    def generate_cost_and_value(self, quantity_on_hand: int) -> tuple:
        """
        Generate unit_cost and inventory_value
        inventory_value = quantity_on_hand * unit_cost
        """
        if random.random() < 0.8:
            unit_cost = round(random.uniform(5.0, 200.0), 2)
            inventory_value = round(quantity_on_hand * unit_cost, 2)
            return unit_cost, inventory_value
        return None, None

    def generate_demand_forecasts(self) -> tuple:
        """Generate demand forecasts (70% probability)"""
        if random.random() < 0.7:
            demand_30d = random.randint(50, 500)
            demand_90d = demand_30d * random.randint(2, 4)
            return demand_30d, demand_90d
        return None, None

    def generate_supply_info(self, status: str) -> tuple:
        """Generate supply_on_order and expected_delivery_date"""
        supply_on_order = None
        expected_delivery_date = ""

        if status in ["low_stock", "out_of_stock", "pending_arrival"] or random.random() < 0.3:
            supply_on_order = random.randint(100, 800)
            # Expected delivery 1-30 days from now
            days_ahead = random.randint(1, 30)
            delivery_date = datetime.now() + timedelta(days=days_ahead)
            expected_delivery_date = delivery_date.strftime("%Y-%m-%d")

        return supply_on_order, expected_delivery_date

    def generate_dates(self) -> tuple:
        """Generate last_restock_date and last_counted_date"""
        last_restock_date = ""
        last_counted_date = ""

        if random.random() < 0.6:
            # Last restock within 60 days
            days_ago = random.randint(1, 60)
            restock = datetime.now() - timedelta(days=days_ago)
            last_restock_date = restock.strftime("%Y-%m-%dT%H:%M:%SZ")

        if random.random() < 0.5:
            # Last count within 90 days
            days_ago = random.randint(1, 90)
            counted = datetime.now() - timedelta(days=days_ago)
            last_counted_date = counted.strftime("%Y-%m-%dT%H:%M:%SZ")

        return last_restock_date, last_counted_date

    def calculate_metrics(self, quantity_available: int, demand_30d: int) -> tuple:
        """Calculate stockout_risk_score, days_of_supply, inventory_turnover_rate"""
        stockout_risk_score = None
        days_of_supply = None
        inventory_turnover_rate = None

        if demand_30d and random.random() < 0.6:
            avg_daily_demand = demand_30d / 30.0

            # Days of supply
            if avg_daily_demand > 0:
                days_of_supply = round(quantity_available / avg_daily_demand, 1)
            else:
                days_of_supply = 999.9

            # Stockout risk score (0-100)
            if days_of_supply < 7:
                stockout_risk_score = round(random.uniform(70, 95), 2)
            elif days_of_supply < 14:
                stockout_risk_score = round(random.uniform(40, 70), 2)
            elif days_of_supply < 30:
                stockout_risk_score = round(random.uniform(10, 40), 2)
            else:
                stockout_risk_score = round(random.uniform(0, 10), 2)

            # Inventory turnover rate (times per year)
            if random.random() < 0.5:
                inventory_turnover_rate = round(random.uniform(2.0, 15.0), 2)

        return stockout_risk_score, days_of_supply, inventory_turnover_rate

    def select_event_type(self) -> str:
        """Select event type based on weighted distribution"""
        events = list(EVENT_TYPE_WEIGHTS.keys())
        weights = list(EVENT_TYPE_WEIGHTS.values())
        return random.choices(events, weights=weights)[0]

    def select_change_reason(self, event_type: str) -> str:
        """Select change reason based on event type (60% probability)"""
        if random.random() < 0.6:
            # Map event types to likely change reasons
            if event_type == "stock_update":
                return random.choice(["order_fulfillment", "returns", "restock"])
            elif event_type == "stock_adjustment":
                return random.choice(["adjustment", "damage", "theft"])
            elif event_type == "shipment_received":
                return "restock"
            elif event_type == "physical_count":
                return "physical_count"
            elif event_type == "reservation_change":
                return "order_fulfillment"
            else:
                return random.choice(CHANGE_REASONS)
        return ""

    def generate_timestamps(self) -> tuple:
        """Generate created_at, updated_at, event_timestamp"""
        # Records created within last 30 days
        created_at = fake.date_time_between(start_date="-30d", end_date="now")
        updated_at = fake.date_time_between(start_date=created_at, end_date="now")
        event_timestamp = updated_at

        return (
            created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            event_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def generate_inventory_record(self) -> Dict[str, Any]:
        """Generate a single inventory record"""
        # Basic IDs
        inventory_id = self.generate_inventory_id()
        product_id = self.generate_product_id()
        warehouse_id = self.generate_warehouse_id()
        location_code = self.generate_location_code()

        # Initial status
        status = self.select_inventory_status()

        # Quantities
        (quantity_on_hand, quantity_reserved, quantity_available,
         quantity_in_transit, quantity_damaged) = self.generate_quantities(status)

        # Reorder parameters
        reorder_point, reorder_quantity, safety_stock = self.generate_reorder_params(
            quantity_available, status
        )

        # Recalculate status based on quantities (data quality rule)
        inventory_status = self.calculate_inventory_status_from_quantities(
            quantity_available, reorder_point, discontinued=(status == "discontinued")
        )

        # Cost and value
        unit_cost, inventory_value = self.generate_cost_and_value(quantity_on_hand)

        # Demand forecasts
        demand_30d, demand_90d = self.generate_demand_forecasts()

        # Supply info
        supply_on_order, expected_delivery_date = self.generate_supply_info(inventory_status)

        # Dates
        last_restock_date, last_counted_date = self.generate_dates()

        # Calculated metrics
        stockout_risk_score, days_of_supply, inventory_turnover_rate = self.calculate_metrics(
            quantity_available, demand_30d or 100
        )

        # Event info
        event_type = self.select_event_type()
        change_reason = self.select_change_reason(event_type)

        # Timestamps
        created_at, updated_at, event_timestamp = self.generate_timestamps()

        # Build inventory record
        record = {
            "inventory_id": inventory_id,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "location_code": location_code,
            "quantity_on_hand": quantity_on_hand,
            "quantity_reserved": quantity_reserved,
            "quantity_available": quantity_available,
            "quantity_in_transit": quantity_in_transit if quantity_in_transit else "",
            "quantity_damaged": quantity_damaged if quantity_damaged else "",
            "reorder_point": reorder_point,
            "reorder_quantity": reorder_quantity,
            "safety_stock": safety_stock if safety_stock else "",
            "unit_cost": f"{unit_cost:.2f}" if unit_cost is not None else "",
            "inventory_value": f"{inventory_value:.2f}" if inventory_value is not None else "",
            "supply_on_order": supply_on_order if supply_on_order is not None else "",
            "expected_delivery_date": expected_delivery_date,
            "last_restock_date": last_restock_date,
            "last_counted_date": last_counted_date,
            "inventory_status": inventory_status,
            "inventory_turnover_rate": f"{inventory_turnover_rate:.2f}" if inventory_turnover_rate is not None else "",
            "event_type": event_type,
            "change_reason": change_reason,
            "created_at": created_at,
            "updated_at": updated_at,
            "event_timestamp": event_timestamp
        }

        return record

    def generate_inventory_data(self) -> List[Dict[str, Any]]:
        """Generate complete inventory dataset"""
        print(f"Generating {self.count} sample inventory records...")
        records = [self.generate_inventory_record() for _ in range(self.count)]
        print(f"✓ Generated {len(records)} inventory records")
        return records

    def save_to_csv(self, records: List[Dict[str, Any]], output_file: str):
        """Save inventory records to CSV file"""
        if not records:
            print("Error: No records to save")
            return

        # Define field order based on schema
        fieldnames = [
            "inventory_id", "product_id", "warehouse_id", "location_code",
            "quantity_on_hand", "quantity_reserved", "quantity_available",
            "quantity_in_transit", "quantity_damaged",
            "reorder_point", "reorder_quantity", "safety_stock",
            "unit_cost", "inventory_value",
            "supply_on_order", "expected_delivery_date",
            "last_restock_date", "last_counted_date",
            "inventory_status",
            "inventory_turnover_rate", "event_type", "change_reason",
            "created_at", "updated_at", "event_timestamp"
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        print(f"✓ Saved to {output_file}")

        # Print summary statistics
        self.print_statistics(records)

    def print_statistics(self, records: List[Dict[str, Any]]):
        """Print summary statistics of generated inventory data"""
        print("\n=== Inventory Statistics ===")
        print(f"Total Records: {len(records)}")

        # Inventory status distribution
        status_counts = {}
        for r in records:
            status = r['inventory_status']
            status_counts[status] = status_counts.get(status, 0) + 1

        print("\nInventory Status Distribution:")
        for status, count in sorted(status_counts.items()):
            pct = (count / len(records)) * 100
            print(f"  {status}: {count} ({pct:.1f}%)")

        # Warehouse distribution
        warehouse_counts = {}
        for r in records:
            wh = r['warehouse_id']
            warehouse_counts[wh] = warehouse_counts.get(wh, 0) + 1

        print("\nTop 5 Warehouses:")
        for wh, count in sorted(warehouse_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            pct = (count / len(records)) * 100
            print(f"  {wh}: {count} ({pct:.1f}%)")

        # Event type distribution
        event_counts = {}
        for r in records:
            evt = r['event_type']
            event_counts[evt] = event_counts.get(evt, 0) + 1

        print("\nEvent Type Distribution:")
        for evt, count in sorted(event_counts.items()):
            pct = (count / len(records)) * 100
            print(f"  {evt}: {count} ({pct:.1f}%)")

        # Data quality checks
        print("\n=== Data Quality Checks ===")
        unique_ids = len(set(r['inventory_id'] for r in records))
        print(f"✓ Unique inventory_ids: {unique_ids}/{len(records)}")

        # Check quantity_available = quantity_on_hand - quantity_reserved
        qty_violations = sum(
            1 for r in records
            if r['quantity_available'] != (r['quantity_on_hand'] - r['quantity_reserved'])
        )
        print(f"✓ Quantity calculation violations: {qty_violations}/{len(records)}")

        # Check quantity_on_hand >= quantity_reserved
        reserved_violations = sum(
            1 for r in records
            if r['quantity_on_hand'] < r['quantity_reserved']
        )
        print(f"✓ Reserved > On-hand violations: {reserved_violations}/{len(records)}")

        # Check inventory_value calculation
        value_violations = 0
        for r in records:
            if r['unit_cost'] and r['inventory_value']:
                expected_value = round(r['quantity_on_hand'] * float(r['unit_cost']), 2)
                actual_value = float(r['inventory_value'])
                if abs(expected_value - actual_value) > 0.01:
                    value_violations += 1
        print(f"✓ Inventory value calculation violations: {value_violations}/{len(records)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample inventory data for testing"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of inventory records to generate (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="schemas/samples/inventory_generated.csv",
        help="Output CSV file path (default: schemas/samples/inventory_generated.csv)"
    )

    args = parser.parse_args()

    # Add Unix timestamp to output filename
    output_path = Path(args.output)
    timestamp = int(time.time())
    output_filename = f"{output_path.stem}_{timestamp}{output_path.suffix}"
    output_file = output_path.parent / output_filename

    # Generate inventory data
    generator = InventoryDataGenerator(count=args.count)
    records = generator.generate_inventory_data()

    # Save to CSV
    generator.save_to_csv(records, str(output_file))

    print("\n✓ Sample inventory generation complete!")


if __name__ == "__main__":
    main()
