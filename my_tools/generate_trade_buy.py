#!/usr/bin/env python3
"""
generate_trade_buy.py

Reads trade_categories.ltx and trader_categories_multipliers.ltx and outputs
a [trade_generic_buy] section populated with items and their min/max multipliers.

Usage:
    python generate_trade_buy.py
    python generate_trade_buy.py --categories my_categories.ltx --multipliers my_multipliers.ltx --output output.ltx
    python generate_trade_buy.py --help
"""

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_ltx_sections(filepath):
    """
    Parse a simple LTX file into a dict of { section_name: [list of lines] }.
    
    Handles:
      - [section_name] headers
      - key = value pairs
      - bare item names (no value)
      - ; comments (stripped)
      - blank lines (ignored)
      - inheritance suffixes like [section]:parent are ignored (parent stripped)
    """
    sections = {}
    current_section = None

    with open(filepath, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            # strip inline comments
            if ";" in line:
                line = line[:line.index(";")].strip()

            if not line:
                continue

            # section header
            if line.startswith("["):
                end = line.index("]")
                header = line[1:end].strip()
                # strip inheritance (e.g. [section]:parent -> section)
                if ":" in header:
                    header = header[:header.index(":")].strip()
                current_section = header
                if current_section not in sections:
                    sections[current_section] = []
                continue

            if current_section is None:
                continue

            sections[current_section].append(line)

    return sections


def parse_categories(filepath):
    """
    Returns { category_name: [item_name, ...] }
    Each line in a category section is a bare item name.
    """
    raw = parse_ltx_sections(filepath)
    categories = {}
    for section, lines in raw.items():
        items = []
        for line in lines:
            item = line.strip()
            if item:
                items.append(item)
        categories[section] = items
    return categories


def parse_multipliers(filepath):
    """
    Returns { category_name: (max_multiplier, min_multiplier) }
    Each line is expected to be:   category_name = max, min
    """
    raw = parse_ltx_sections(filepath)
    multipliers = {}

    for section, lines in raw.items():
        for line in lines:
            if "=" not in line:
                print(f"  [warning] skipping malformed line in [{section}]: '{line}'")
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            parts = [p.strip() for p in value.split(",")]

            if len(parts) != 2:
                print(f"  [warning] expected 'max, min' for '{key}' in [{section}], got: '{value}'")
                continue

            try:
                max_val = float(parts[0])
                min_val = float(parts[1])
            except ValueError:
                print(f"  [warning] non-numeric values for '{key}' in [{section}]: '{value}'")
                continue

            if min_val > max_val:
                print(f"  [warning] min ({min_val}) > max ({max_val}) for '{key}' in [{section}] — swapping")
                max_val, min_val = min_val, max_val

            multipliers[key] = (max_val, min_val)

    return multipliers


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_trade_generic_buy(categories, multipliers):
    """
    Build the lines for a [trade_generic_buy] section.
    Returns (output_lines, warnings) where output_lines is a list of strings.
    """
    lines = []
    warnings = []

    # find which categories appear in multipliers
    used_categories = []
    for cat_name in multipliers:
        if cat_name not in categories:
            warnings.append(f"category '{cat_name}' defined in multipliers but not found in categories file — skipped")
        else:
            used_categories.append(cat_name)

    # warn about categories defined but never assigned a multiplier
    for cat_name in categories:
        if cat_name not in multipliers:
            warnings.append(f"category '{cat_name}' defined in categories file but has no multiplier — skipped")

    # build section
    for cat_name in used_categories:
        max_val, min_val = multipliers[cat_name]
        items = categories[cat_name]

        if not items:
            warnings.append(f"category '{cat_name}' has no items — skipped")
            continue

        lines.append(f"; --- {cat_name} (max={max_val}, min={min_val})")
        for item in items:
            # format floats cleanly: use 2 decimal places, strip trailing zeros
            max_str = f"{max_val:.2f}".rstrip("0").rstrip(".")
            min_str = f"{min_val:.2f}".rstrip("0").rstrip(".")
            lines.append(f"{item:<40} = {max_str}, {min_str}")
        lines.append("")  # blank line between categories

    return lines, warnings


def write_output(output_path, section_lines):
    """Write the final LTX file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("; Auto-generated by generate_trade_buy.py\n")
        f.write("; Do not edit manually — edit trade_categories.ltx and\n")
        f.write("; trader_categories_multipliers.ltx then re-run the generator.\n")
        f.write("\n")
        f.write("[trade_generic_buy]:trasher\n")
        for line in section_lines:
            f.write(line + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a [trade_generic_buy] LTX section from category and multiplier definitions."
    )
    parser.add_argument(
        "--categories",
        default="trade_categories.ltx",
        help="Path to the categories file (default: trade_categories.ltx)"
    )
    parser.add_argument(
        "--multipliers",
        default="trader_categories_multipliers.ltx",
        help="Path to the multipliers file (default: trader_categories_multipliers.ltx)"
    )
    parser.add_argument(
        "--output",
        default="trade_generic_buy_output.ltx",
        help="Path for the output file (default: trade_generic_buy_output.ltx)"
    )
    args = parser.parse_args()

    # validate input files exist
    categories_path = Path(args.categories)
    multipliers_path = Path(args.multipliers)

    if not categories_path.exists():
        print(f"Error: categories file not found: {categories_path}")
        sys.exit(1)

    if not multipliers_path.exists():
        print(f"Error: multipliers file not found: {multipliers_path}")
        sys.exit(1)

    print(f"Reading categories from:  {categories_path}")
    print(f"Reading multipliers from: {multipliers_path}")

    categories = parse_categories(categories_path)
    multipliers = parse_multipliers(multipliers_path)

    print(f"  Found {len(categories)} categories, {sum(len(v) for v in categories.values())} total items")
    print(f"  Found {len(multipliers)} category multiplier entries")

    section_lines, warnings = generate_trade_generic_buy(categories, multipliers)

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")

    output_path = Path(args.output)
    write_output(output_path, section_lines)

    item_count = sum(1 for l in section_lines if l and not l.startswith(";") and "=" in l)
    print(f"\nOutput written to: {output_path}")
    print(f"  {item_count} items written to [trade_generic_buy]")


if __name__ == "__main__":
    main()
