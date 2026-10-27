#!/usr/bin/env python3
"""
Schema Diagram Generator

Generates a comprehensive ERD diagram of all data schemas with relationships.
Output: PDF file with visual representation of schema structure.

Usage:
    python generate_schema_diagram.py [--output schema_diagram.pdf]
"""

import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.patches import Rectangle
import time

# Schema file paths
SCHEMA_DIR = Path("schemas")
SCHEMAS = {
    "customer": SCHEMA_DIR / "customer_schema.json",
    "product_catalog": SCHEMA_DIR / "product_catalog_schema.json",
    "inventory": SCHEMA_DIR / "inventory_schema.json",
    "order": SCHEMA_DIR / "order_schema.json",
    "shipping": SCHEMA_DIR / "shipping_schema.json"
}

# Color scheme
COLORS = {
    "customer": "#FFE5B4",      # Peach
    "product": "#B4E5FF",       # Light blue
    "inventory": "#C8E6C9",     # Light green
    "order": "#FFD9B3",         # Light orange
    "shipping": "#E1BEE7"       # Light purple
}

# Schema positions for layout (x, y)
POSITIONS = {
    "customer": (0.5, 7.5),
    "product_catalog": (6, 7.5),
    "inventory": (6, 4),
    "order": (0.5, 4),
    "shipping": (3.25, 0.5)
}


def load_schema(schema_path: Path) -> dict:
    """Load schema JSON file"""
    with open(schema_path, 'r') as f:
        return json.load(f)


def get_key_fields(schema: dict, max_fields: int = 10) -> list:
    """Extract key fields from schema"""
    fields = schema.get("fields", [])
    key_fields = []

    # Always include primary key and foreign keys first
    for field in fields:
        if field.get("primary_key") or field.get("foreign_key"):
            key_fields.append({
                "name": field["name"],
                "type": field["type"],
                "is_pk": field.get("primary_key", False),
                "is_fk": field.get("foreign_key"),
                "required": field.get("required", False)
            })

    # Add other important required fields
    for field in fields:
        if len(key_fields) >= max_fields:
            break
        if field.get("required") and not field.get("primary_key") and not field.get("foreign_key"):
            # Skip timestamp fields for brevity
            if field["name"] not in ["created_at", "updated_at", "event_timestamp"]:
                key_fields.append({
                    "name": field["name"],
                    "type": field["type"],
                    "is_pk": False,
                    "is_fk": False,
                    "required": True
                })

    return key_fields[:max_fields]


def extract_relationships(schemas: dict) -> list:
    """Extract foreign key relationships between schemas"""
    relationships = []

    for schema_name, schema_data in schemas.items():
        fields = schema_data.get("fields", [])
        for field in fields:
            fk = field.get("foreign_key")
            if fk:
                # Parse foreign key: "table.column"
                parts = fk.split(".")
                if len(parts) == 2:
                    target_table = parts[0]
                    relationships.append({
                        "from": schema_name,
                        "to": target_table,
                        "from_field": field["name"],
                        "to_field": parts[1]
                    })

    return relationships


def draw_table(ax, name, display_name, fields, position, color, width=2.5, height=None):
    """Draw a table box with fields"""
    x, y = position

    # Calculate height based on number of fields
    if height is None:
        header_height = 0.4
        field_height = 0.25
        height = header_height + (len(fields) * field_height) + 0.2

    # Draw table box
    table_box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.05",
        edgecolor='black',
        facecolor=color,
        linewidth=2,
        zorder=2
    )
    ax.add_patch(table_box)

    # Draw header
    header_box = Rectangle(
        (x, y + height - 0.4), width, 0.4,
        facecolor='#333333',
        edgecolor='black',
        linewidth=1.5,
        zorder=3
    )
    ax.add_patch(header_box)

    # Table name
    ax.text(
        x + width/2, y + height - 0.2,
        display_name.upper(),
        ha='center', va='center',
        fontsize=11, fontweight='bold',
        color='white',
        zorder=4
    )

    # Draw fields
    field_y = y + height - 0.6
    for field in fields:
        # Field name and type
        field_name = field["name"]
        field_type = field["type"][:15]  # Truncate long types

        # Add indicators
        indicator = ""
        if field.get("is_pk"):
            indicator = "🔑 "
        elif field.get("is_fk"):
            indicator = "🔗 "

        field_text = f"{indicator}{field_name}: {field_type}"

        ax.text(
            x + 0.1, field_y,
            field_text,
            ha='left', va='center',
            fontsize=8,
            fontweight='bold' if field.get("is_pk") or field.get("is_fk") else 'normal',
            zorder=4
        )

        field_y -= 0.25

    return (x + width/2, y + height/2)  # Return center point


def draw_relationship(ax, from_pos, to_pos, label=""):
    """Draw a relationship arrow between two tables"""
    # Draw arrow
    arrow = FancyArrowPatch(
        from_pos, to_pos,
        arrowstyle='-|>',
        mutation_scale=20,
        linewidth=1.5,
        edgecolor='#555555',
        facecolor='#555555',
        zorder=1,
        linestyle='--'
    )
    ax.add_patch(arrow)

    # Add label if provided
    if label:
        mid_x = (from_pos[0] + to_pos[0]) / 2
        mid_y = (from_pos[1] + to_pos[1]) / 2
        ax.text(
            mid_x, mid_y,
            label,
            ha='center', va='bottom',
            fontsize=7,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', linewidth=0.5),
            zorder=5
        )


def create_diagram(schemas: dict, output_file: str):
    """Create the complete schema diagram"""
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 9.5)
    ax.axis('off')

    # Title
    ax.text(
        5, 9.2,
        'E-Commerce Data Pipeline - Schema Overview',
        ha='center', va='top',
        fontsize=18, fontweight='bold'
    )

    # Subtitle
    ax.text(
        5, 8.8,
        'Entity Relationship Diagram - 5 Core Schemas',
        ha='center', va='top',
        fontsize=12, style='italic', color='gray'
    )

    # Store table centers for drawing relationships
    table_centers = {}

    # Draw all tables
    for schema_name, schema_data in schemas.items():
        display_name = schema_data.get("schema_name", schema_name)
        fields = get_key_fields(schema_data)
        position = POSITIONS[schema_name]
        color = COLORS.get(schema_name.split("_")[0], "#EEEEEE")

        center = draw_table(
            ax, schema_name, display_name,
            fields, position, color
        )
        table_centers[schema_name] = center

    # Extract and draw relationships
    relationships = extract_relationships(schemas)

    # Draw relationship arrows
    for rel in relationships:
        from_schema = rel["from"]
        to_schema = rel["to"]

        if from_schema in table_centers and to_schema in table_centers:
            from_pos = table_centers[from_schema]
            to_pos = table_centers[to_schema]

            # Adjust positions to table edges
            from_x, from_y = from_pos
            to_x, to_y = to_pos

            # Simple edge connection (can be improved)
            if from_x < to_x:
                from_edge = (from_x + 1.25, from_y)
                to_edge = (to_x - 1.25, to_y)
            elif from_x > to_x:
                from_edge = (from_x - 1.25, from_y)
                to_edge = (to_x + 1.25, to_y)
            else:
                from_edge = (from_x, from_y - 0.5)
                to_edge = (to_x, to_y + 0.5)

            draw_relationship(ax, from_edge, to_edge, rel["from_field"])

    # Legend
    legend_x = 0.5
    legend_y = 1.2

    ax.text(legend_x, legend_y, "Legend:", fontsize=10, fontweight='bold')
    ax.text(legend_x, legend_y - 0.3, "🔑 Primary Key", fontsize=8)
    ax.text(legend_x, legend_y - 0.6, "🔗 Foreign Key", fontsize=8)
    ax.text(legend_x + 2.5, legend_y - 0.3, "→  Relationship", fontsize=8)

    # Schema statistics
    stats_x = 6.5
    stats_y = 1.2
    ax.text(stats_x, stats_y, "Schema Statistics:", fontsize=10, fontweight='bold')

    total_fields = sum(len(s.get("fields", [])) for s in schemas.values())
    total_required = sum(
        len([f for f in s.get("fields", []) if f.get("required")])
        for s in schemas.values()
    )

    ax.text(stats_x, stats_y - 0.3, f"Total Schemas: {len(schemas)}", fontsize=8)
    ax.text(stats_x, stats_y - 0.6, f"Total Fields: {total_fields}", fontsize=8)
    ax.text(stats_x, stats_y - 0.9, f"Required Fields: {total_required}", fontsize=8)

    # Footer
    footer_text = f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')} | AWS Data Pipeline Project"
    ax.text(
        5, 0.1,
        footer_text,
        ha='center', va='center',
        fontsize=8, color='gray', style='italic'
    )

    plt.tight_layout()

    # Save to PDF
    plt.savefig(output_file, format='pdf', bbox_inches='tight', dpi=300)
    print(f"✓ Diagram saved to {output_file}")

    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate schema diagram as PDF"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="schemas/schema_diagram.pdf",
        help="Output PDF file path (default: schemas/schema_diagram.pdf)"
    )

    args = parser.parse_args()

    # Add Unix timestamp to output filename
    output_path = Path(args.output)
    timestamp = int(time.time())
    output_filename = f"{output_path.stem}_{timestamp}{output_path.suffix}"
    output_file = output_path.parent / output_filename

    print("Loading schemas...")
    schemas = {}
    for name, path in SCHEMAS.items():
        if path.exists():
            schemas[name] = load_schema(path)
            print(f"  ✓ Loaded {name}")
        else:
            print(f"  ✗ Schema not found: {path}")

    if not schemas:
        print("Error: No schemas found!")
        return

    print(f"\nGenerating diagram with {len(schemas)} schemas...")
    create_diagram(schemas, str(output_file))

    print("\n✓ Schema diagram generation complete!")


if __name__ == "__main__":
    main()
