# main.py

import csv
import logging
from typing import List, Dict
from src.data_cleaning import (
    FiberParser,
    FuzzyFiberMatcher,
    normalize_fiber_name,
    split_category_subcategory,
    clean_text
)
from src.models import Product, Part, Fiber
from src.sql_export import SQLExporter
from src.constants import METADATA_DICT

logging.basicConfig(level=logging.INFO)

def is_not_empty_or_false(s: str|bool) -> bool:
    if isinstance(s, bool):
        return s
    
    return not (s is None or s == "")


def build_frequency_map(csv_path: str) -> Dict[str, int]:
    """
    Reads the CSV once to gather all fiber names, normalizes them,
    and counts how often each appears. We only look at the 'care_label'
    column, parse it, and accumulate.
    """
    freq_map: Dict[str, int] = {}
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            care = row["care_label"]
            # parse
            parsed = FiberParser.parse_care_label(care)
            for part_dict in parsed["parts"]:
                for fiber_info in part_dict["fibers"]:
                    norm = normalize_fiber_name(fiber_info["name"])
                    freq_map[norm] = freq_map.get(norm, 0) + 1
    return freq_map


def parse_product_care_label(
    product_id: str,
    category: str,
    care_label: str,
    part_id_start: int,
    fuzzy_matcher: FuzzyFiberMatcher,
    verbose=False,
) -> Product:
    """
    Splits category into (product_category, product_sub_category).
    Parses the care label -> build a Product with parts, each part having a unique part_id,
    and each Fiber storing product_id, part_id, original_fiber_name, brand, etc.
    """
    product_category, product_sub_category = split_category_subcategory(category)
    parsed = FiberParser.parse_care_label(care_label, verbose=verbose)
    parts_data = parsed["parts"]

    parts_list = []
    current_part_id = part_id_start

    for part_dict in parts_data:
        # Build fiber list
        fibers_list = []
        for fiber_info in part_dict["fibers"]:
            # normalized name
            normalized_name = normalize_fiber_name(fiber_info["name"])
            canonical_name = fuzzy_matcher.get_canonical_fiber(normalized_name)

            mat = Fiber(
                product_id=product_id,
                part_id=current_part_id,
                name=canonical_name,
                proportion=fiber_info["mix"],
                brand=fiber_info.get("brand", ""),
                original_fiber_name=fiber_info["original_fiber_name"],
                made_in_france=fiber_info.get("made_in_france", False),
                solution_dyed=fiber_info.get("solution_dyed", False),
                recycled=fiber_info.get("recycled", False),
            )
            fibers_list.append(mat)

        part_obj = Part(
            part_id=current_part_id,
            product_id=product_id,
            name=clean_text(part_dict["fabric_part"]),
            weight=part_dict["weight"],
            weight_unit=part_dict["weight_unit"],
            fibers=fibers_list,
        )
        parts_list.append(part_obj)
        current_part_id += 1

    product_obj = Product(
        product_id=product_id,
        product_category=clean_text(product_category),
        product_sub_category=clean_text(product_sub_category),
        original_care_label=care_label,
        parts=parts_list,
    )
    return product_obj


def load_csv_and_parse(
    csv_path: str, fuzzy_matcher: FuzzyFiberMatcher, verbose=False
) -> List[Product]:
    """
    Reads CSV columns: product_id, product_category, care_label
    Returns a list of Product objects.
    """
    products = []
    part_id_counter = 1  # We'll increment for each part across all products

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["product_id"]
            cat = row["product_category"]
            care = row["care_label"]

            product_obj = parse_product_care_label(
                pid, cat, care, part_id_counter, fuzzy_matcher, verbose=verbose
            )

            # We need to update the part_id_counter for the next product
            # by how many parts this product just used.
            part_count = len(product_obj.parts)
            part_id_counter += part_count
            products.append(product_obj)

    return products


def main(csv_path: str = "data/data.csv"):
    # CSV path
    logging.info(f"Reading CSV to build frequency map: {csv_path}")

    # 1) First pass: build frequency map
    freq_map = build_frequency_map(csv_path)

    # 2) Select all normalized names with freq >= 100
    initial_data = {k: v for k, v in freq_map.items() if v >= 100}
    logging.info(
        f"Pre-populating fuzzy matcher with {len(initial_data)} fibers (>= 100 occurrences)"
    )

    # 3) Build fuzzy matcher
    fuzzy_matcher = FuzzyFiberMatcher(threshold=95, initial_data=initial_data)

    # 4) Second pass: parse full CSV into Product objects
    products = load_csv_and_parse(csv_path, fuzzy_matcher=fuzzy_matcher, verbose=True)

    # Export to DB
    database_name = "products.db"
    exporter = SQLExporter(database_name)

    # ============ Export Product Table ============
    product_table_name = "products"
    product_columns = [
        "product_id TEXT",  # from CSV
        "product_category TEXT",
        "product_sub_category TEXT",
        "original_care_label TEXT",
    ]

    product_data_to_insert = []
    for p in products:
        product_data_to_insert.append(
            {
                "product_id": p.product_id,
                "product_category": p.product_category,
                "product_sub_category": p.product_sub_category,
                "original_care_label": p.original_care_label,
            }
        )

    exporter.export_to_sql(product_table_name, product_columns, product_data_to_insert)

    # ============ Export Parts ============
    # part_id is unique across entire dataset
    part_table_name = "parts"
    part_columns = [
        "part_id INTEGER PRIMARY KEY",  # We'll use the part_id from the model (unique).
        "product_id TEXT",
        "part_name TEXT",
        "part_weight REAL",
        "part_weight_unit TEXT",
    ]
    part_data_to_insert = []
    for p in products:
        for part in p.parts:
            part_data_to_insert.append(
                {
                    "part_id": part.part_id,
                    "product_id": part.product_id,
                    "part_name": part.name,
                    "part_weight": part.weight,
                    "part_weight_unit": part.weight_unit,
                }
            )

    exporter.export_to_sql(part_table_name, part_columns, part_data_to_insert)

    fiber_table_name = "fibers"
    fiber_columns = [
        "fiber_id INTEGER PRIMARY KEY AUTOINCREMENT",
        "product_id TEXT",
        "part_id INTEGER",
        "part_name TEXT",
        "fiber_name TEXT",
        "fiber_proportion REAL",
        "brand TEXT",
        "original_fiber_name TEXT",
        "made_in_france BOOLEAN",
        "solution_dyed BOOLEAN",
        "recycled BOOLEAN",
    ]

    fiber_data_to_insert = []
    for p in products:
        for part in p.parts:
            for mat in part.fibers:
                record = {
                    "product_id": mat.product_id,
                    "part_id": mat.part_id,
                    "part_name": part.name,
                    "fiber_name": mat.name,
                    "fiber_proportion": mat.proportion,
                    "brand": mat.brand,
                    "original_fiber_name": mat.original_fiber_name,
                    "made_in_france": mat.made_in_france,
                    "solution_dyed": mat.solution_dyed,
                    "recycled": mat.recycled,
                }
                if  is_not_empty_or_false(record["fiber_name"]) or any([is_not_empty_or_false(record[k]) for k in METADATA_DICT]):

                    fiber_data_to_insert.append(record)
    exporter.export_to_sql(fiber_table_name, fiber_columns, fiber_data_to_insert)

    logging.info("Done exporting data!")


if __name__ == "__main__":
    import os
    import argparse

    parser = argparse.ArgumentParser(description="Run the data parser.")
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default="data/data.csv",
        help="Path to the input CSV file."
    )
    args = parser.parse_args()
    database_name = "products.db"
    if os.path.exists(database_name):
        os.remove(database_name)
    main(csv_path=args.path)
