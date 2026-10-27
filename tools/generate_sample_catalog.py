#!/usr/bin/env python3
"""
Sample Product Catalog Generator

Generates realistic sample product catalog data for testing the data pipeline.
Follows the schema defined in schemas/product_catalog_schema.json

Usage:
    python generate_sample_catalog.py [--count 100] [--output output.csv]
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


# Category hierarchies based on schema validation rules
CATEGORY_HIERARCHIES = {
    "Apparel": {
        "Men's Clothing": ["T-Shirts & Tanks", "Shirts", "Pants & Jeans", "Outerwear", "Activewear"],
        "Women's Clothing": ["Dresses", "Tops & Blouses", "Jeans", "Skirts", "Activewear"],
        "Kids Clothing": ["Boys", "Girls", "Toddler", "Baby"],
        "Shoes & Footwear": ["Sneakers", "Boots", "Sandals", "Dress Shoes"],
        "Accessories": ["Bags", "Belts", "Hats", "Scarves", "Jewelry"]
    },
    "Electronics": {
        "Computers": ["Laptops", "Desktops", "Tablets", "Accessories"],
        "Mobile Devices": ["Smartphones", "Smart Watches", "Phone Cases", "Chargers"],
        "Audio": ["Headphones", "Speakers", "Microphones", "Sound Systems"],
        "Gaming": ["Consoles", "Games", "Controllers", "Accessories"],
        "Computer Accessories": ["Mice & Keyboards", "Monitors", "Storage", "Networking"]
    },
    "Home & Garden": {
        "Furniture": ["Living Room", "Bedroom", "Office", "Outdoor"],
        "Kitchen Appliances": ["Coffee Makers", "Blenders", "Toasters", "Cookware"],
        "Home Decor": ["Wall Art", "Lighting", "Rugs", "Curtains"],
        "Garden Tools": ["Hand Tools", "Power Tools", "Lawn Care", "Planters"],
        "Bedding & Bath": ["Sheets", "Towels", "Pillows", "Bath Accessories"]
    },
    "Sports & Outdoors": {
        "Exercise & Fitness": ["Cardio Equipment", "Weights", "Yoga", "Accessories"],
        "Outdoor Recreation": ["Camping", "Hiking", "Fishing", "Cycling"],
        "Team Sports": ["Basketball", "Soccer", "Baseball", "Football"],
        "Footwear": ["Running Shoes", "Hiking Boots", "Cleats", "Sandals"],
        "Sports Apparel": ["Athletic Wear", "Swimwear", "Jackets", "Accessories"]
    },
    "Beauty & Health": {
        "Skincare": ["Cleansers", "Moisturizers", "Serums", "Sunscreen"],
        "Makeup": ["Face", "Eyes", "Lips", "Tools"],
        "Hair Care": ["Shampoo", "Conditioner", "Styling", "Tools"],
        "Personal Care": ["Oral Care", "Body Care", "Grooming", "Hygiene"],
        "Wellness": ["Vitamins", "Supplements", "First Aid", "Medical Devices"]
    },
    "Books & Media": {
        "Books": ["Fiction", "Non-Fiction", "Children's", "Educational"],
        "Movies & TV": ["DVD", "Blu-ray", "Digital", "Box Sets"],
        "Music": ["CDs", "Vinyl", "Digital", "Instruments"],
        "Magazines": ["News", "Fashion", "Science", "Hobby"],
        "Educational Media": ["Textbooks", "Online Courses", "Study Guides", "Reference"]
    }
}

# Brand names by category
BRANDS = {
    "Apparel": ["Nike", "Adidas", "H&M", "Zara", "Gap", "Uniqlo", "Levi's", "Ralph Lauren", "Tommy Hilfiger"],
    "Electronics": ["Apple", "Samsung", "Sony", "LG", "Dell", "HP", "Lenovo", "Asus", "Logitech", "Bose"],
    "Home & Garden": ["IKEA", "Cuisinart", "KitchenAid", "Black+Decker", "Dyson", "Philips", "West Elm"],
    "Sports & Outdoors": ["Nike", "Adidas", "Under Armour", "The North Face", "Coleman", "REI", "Patagonia"],
    "Beauty & Health": ["L'Oréal", "Neutrogena", "Dove", "CeraVe", "Olay", "Maybelline", "Garnier"],
    "Books & Media": ["Penguin", "HarperCollins", "Simon & Schuster", "Random House", "O'Reilly"]
}

# Lifecycle status distribution (weighted)
LIFECYCLE_STATUS_WEIGHTS = {
    "active": 0.70,        # 70% active products
    "pre_launch": 0.10,    # 10% upcoming products
    "discontinued": 0.15,  # 15% discontinued
    "end_of_life": 0.04,   # 4% end of life
    "archived": 0.01       # 1% archived
}


class ProductCatalogGenerator:
    """Generate sample product catalog data following the schema"""

    def __init__(self, count: int = 100):
        self.count = count
        self.used_product_ids = set()
        self.product_id_counter = random.randint(10000, 99999)

    def generate_unique_product_id(self) -> str:
        """Generate unique product ID following pattern ^[A-Z0-9-]+$"""
        while True:
            self.product_id_counter += 1
            product_id = f"PROD-{self.product_id_counter}"
            if product_id not in self.used_product_ids:
                self.used_product_ids.add(product_id)
                return product_id

    def select_category_hierarchy(self) -> tuple:
        """Select random category hierarchy (level_1, level_2, level_3)"""
        level_1 = random.choice(list(CATEGORY_HIERARCHIES.keys()))
        level_2_dict = CATEGORY_HIERARCHIES[level_1]
        level_2 = random.choice(list(level_2_dict.keys()))
        level_3_list = level_2_dict[level_2]
        # 80% of products have level_3, 20% don't
        level_3 = random.choice(level_3_list) if random.random() < 0.8 else ""
        return level_1, level_2, level_3

    def generate_product_name(self, category_l1: str, category_l2: str, category_l3: str, brand: str) -> str:
        """Generate realistic product name based on category"""

        # Product type templates by category
        product_types = {
            "Apparel": [
                f"{fake.color_name()} {category_l3 or category_l2}",
                f"Premium {category_l3 or category_l2}",
                f"Classic {fake.color_name()} {category_l3 or category_l2}"
            ],
            "Electronics": [
                f"{category_l3 or category_l2} - {fake.bothify('Model ###??')}",
                f"Wireless {category_l3 or category_l2}",
                f"Professional {category_l3 or category_l2}"
            ],
            "Home & Garden": [
                f"{fake.bothify('## Cup')} {category_l3 or category_l2}",
                f"Modern {category_l3 or category_l2}",
                f"Classic {category_l3 or category_l2}"
            ],
            "Sports & Outdoors": [
                f"Performance {category_l3 or category_l2}",
                f"Pro {category_l3 or category_l2}",
                f"All-Weather {category_l3 or category_l2}"
            ],
            "Beauty & Health": [
                f"Advanced {category_l3 or category_l2}",
                f"Natural {category_l3 or category_l2}",
                f"Professional {category_l3 or category_l2}"
            ],
            "Books & Media": [
                f"{fake.catch_phrase()}",
                f"The Complete Guide to {category_l3 or category_l2}",
                f"{fake.word().title()} {category_l3 or category_l2}"
            ]
        }

        name = random.choice(product_types.get(category_l1, [category_l3 or category_l2]))
        return name[:255]  # Max length validation

    def select_lifecycle_status(self) -> tuple:
        """Select lifecycle status and corresponding is_active flag"""
        # Weighted random selection
        statuses = list(LIFECYCLE_STATUS_WEIGHTS.keys())
        weights = list(LIFECYCLE_STATUS_WEIGHTS.values())
        lifecycle_status = random.choices(statuses, weights=weights)[0]

        # is_active aligns with lifecycle_status per data quality rules
        is_active = lifecycle_status in ["active", "pre_launch"]

        return lifecycle_status, is_active

    def generate_timestamps(self, lifecycle_status: str) -> tuple:
        """Generate created_at, updated_at, event_timestamp"""
        # Products created between 6 months ago and now
        if lifecycle_status == "archived":
            # Archived products are older
            created_at = fake.date_time_between(start_date="-2y", end_date="-1y")
        elif lifecycle_status == "discontinued" or lifecycle_status == "end_of_life":
            # Discontinued products created some time ago
            created_at = fake.date_time_between(start_date="-1y", end_date="-3m")
        elif lifecycle_status == "pre_launch":
            # Pre-launch products are recent
            created_at = fake.date_time_between(start_date="-1m", end_date="now")
        else:
            # Active products have varied creation dates
            created_at = fake.date_time_between(start_date="-6m", end_date="now")

        # updated_at is between created_at and now
        updated_at = fake.date_time_between(start_date=created_at, end_date="now")

        # event_timestamp is the same as updated_at (most recent change)
        event_timestamp = updated_at

        return (
            created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            event_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def generate_product(self) -> Dict[str, Any]:
        """Generate a single product record"""
        # Category hierarchy
        category_l1, category_l2, category_l3 = self.select_category_hierarchy()

        # Brand
        brand = random.choice(BRANDS.get(category_l1, ["Generic Brand"]))

        # Product name
        product_name = self.generate_product_name(category_l1, category_l2, category_l3, brand)

        # Lifecycle and active status
        lifecycle_status, is_active = self.select_lifecycle_status()

        # Pricing (ensure price >= cost per data quality rules)
        cost = round(random.uniform(5.0, 200.0), 2)
        markup = random.uniform(1.3, 3.0)  # 30% to 200% markup
        price = round(cost * markup, 2)

        # Timestamps
        created_at, updated_at, event_timestamp = self.generate_timestamps(lifecycle_status)

        # Optional fields (70% probability)
        description = fake.text(max_nb_chars=300) if random.random() < 0.7 else ""
        supplier_id = f"SUP-{random.randint(1000, 9999)}" if random.random() < 0.5 else ""
        weight_kg = round(random.uniform(0.1, 25.0), 3) if random.random() < 0.7 else ""

        # Product attributes (JSON field)
        product_attributes = {}
        if category_l1 == "Apparel":
            product_attributes = {
                "size": random.choice(["XS", "S", "M", "L", "XL", "XXL"]),
                "color": fake.color_name(),
                "material": random.choice(["100% Cotton", "Polyester", "Wool", "Blend"])
            }
        elif category_l1 == "Electronics":
            product_attributes = {
                "warranty_months": random.choice([12, 24, 36]),
                "power_rating": f"{random.randint(5, 500)}W"
            }

        product_attributes_str = json.dumps(product_attributes) if product_attributes else ""

        # Dimensions (JSON field)
        dimensions = {
            "length_cm": round(random.uniform(5, 100), 1),
            "width_cm": round(random.uniform(5, 80), 1),
            "height_cm": round(random.uniform(2, 50), 1)
        } if random.random() < 0.6 else {}
        dimensions_str = json.dumps(dimensions) if dimensions else ""

        # Image URLs (array field - represented as JSON string in CSV)
        image_count = random.randint(1, 4)
        image_urls = [f"https://cdn.example.com/products/{self.product_id_counter}/image_{i}.jpg"
                     for i in range(1, image_count + 1)] if random.random() < 0.8 else []
        image_urls_str = json.dumps(image_urls) if image_urls else ""

        # Tags (array field)
        tag_pools = ["bestseller", "new", "sale", "trending", "featured", "seasonal", "limited"]
        tags = random.sample(tag_pools, k=random.randint(0, 3))
        tags_str = json.dumps(tags) if tags else ""

        # Build product record
        product = {
            "product_id": self.generate_unique_product_id(),
            "product_name": product_name,
            "category_level_1": category_l1,
            "category_level_2": category_l2,
            "category_level_3": category_l3,
            "brand": brand,
            "description": description,
            "price": f"{price:.2f}",
            "cost": f"{cost:.2f}",
            "currency": "USD",
            "lifecycle_status": lifecycle_status,
            "product_attributes": product_attributes_str,
            "supplier_id": supplier_id,
            "weight_kg": f"{weight_kg:.3f}" if weight_kg else "",
            "dimensions": dimensions_str,
            "image_urls": image_urls_str,
            "tags": tags_str,
            "is_active": str(is_active).lower(),
            "created_at": created_at,
            "updated_at": updated_at,
            "event_timestamp": event_timestamp
        }

        return product

    def generate_catalog(self) -> List[Dict[str, Any]]:
        """Generate complete product catalog"""
        print(f"Generating {self.count} sample products...")
        products = [self.generate_product() for _ in range(self.count)]
        print(f"✓ Generated {len(products)} products")
        return products

    def save_to_csv(self, products: List[Dict[str, Any]], output_file: str):
        """Save products to CSV file"""
        if not products:
            print("Error: No products to save")
            return

        # Define field order based on schema
        fieldnames = [
            "product_id", "product_name", "category_level_1", "category_level_2", "category_level_3",
            "brand", "description", "price", "cost", "currency", "lifecycle_status",
            "product_attributes", "supplier_id", "weight_kg", "dimensions",
            "image_urls", "tags", "is_active", "created_at", "updated_at", "event_timestamp"
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)

        print(f"✓ Saved to {output_file}")

        # Print summary statistics
        self.print_statistics(products)

    def print_statistics(self, products: List[Dict[str, Any]]):
        """Print summary statistics of generated catalog"""
        print("\n=== Catalog Statistics ===")
        print(f"Total Products: {len(products)}")

        # Lifecycle status distribution
        lifecycle_counts = {}
        for p in products:
            status = p['lifecycle_status']
            lifecycle_counts[status] = lifecycle_counts.get(status, 0) + 1

        print("\nLifecycle Status Distribution:")
        for status, count in sorted(lifecycle_counts.items()):
            pct = (count / len(products)) * 100
            print(f"  {status}: {count} ({pct:.1f}%)")

        # Category distribution
        category_counts = {}
        for p in products:
            cat = p['category_level_1']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        print("\nCategory Distribution:")
        for cat, count in sorted(category_counts.items()):
            pct = (count / len(products)) * 100
            print(f"  {cat}: {count} ({pct:.1f}%)")

        # Price range
        prices = [float(p['price']) for p in products]
        print(f"\nPrice Range:")
        print(f"  Min: ${min(prices):.2f}")
        print(f"  Max: ${max(prices):.2f}")
        print(f"  Avg: ${sum(prices)/len(prices):.2f}")

        # Data quality check
        print("\n=== Data Quality Checks ===")
        unique_ids = len(set(p['product_id'] for p in products))
        print(f"✓ Unique product_ids: {unique_ids}/{len(products)}")

        # Check price >= cost
        price_violations = sum(1 for p in products if float(p['price']) < float(p['cost']))
        print(f"✓ Price >= Cost violations: {price_violations}/{len(products)}")

        # Check is_active alignment with lifecycle_status
        status_violations = sum(
            1 for p in products
            if (p['is_active'] == 'true' and p['lifecycle_status'] in ['discontinued', 'end_of_life', 'archived']) or
               (p['is_active'] == 'false' and p['lifecycle_status'] in ['active', 'pre_launch'])
        )
        print(f"✓ is_active/lifecycle_status alignment violations: {status_violations}/{len(products)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample product catalog data for testing"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of products to generate (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="schemas/samples/product_catalog_generated.csv",
        help="Output CSV file path (default: schemas/samples/product_catalog_generated.csv)"
    )

    args = parser.parse_args()

    # Add Unix timestamp to output filename
    output_path = Path(args.output)
    timestamp = int(time.time())
    output_filename = f"{output_path.stem}_{timestamp}{output_path.suffix}"
    output_file = output_path.parent / output_filename

    # Generate catalog
    generator = ProductCatalogGenerator(count=args.count)
    products = generator.generate_catalog()

    # Save to CSV
    generator.save_to_csv(products, str(output_file))

    print("\n✓ Sample catalog generation complete!")


if __name__ == "__main__":
    main()
