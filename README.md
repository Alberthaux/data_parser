
# Care Label Parsing & Data Pipeline

This repository provides a **data pipeline** for parsing clothing care labels, extracting fiber compositions, weights, and various metadata fields (e.g., brand names, “made in France,” “solution-dyed,” “recycled,” etc.). The parsed results are then stored in a relational database.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
  - [1. Data Cleaning & Parsing](#1-data-cleaning--parsing)
  - [2. Running the Pipeline](#2-running-the-pipeline)
- [Configuration](#configuration)
- [Extending & Customizing](#extending--customizing)
- [License](#license)

---

## Overview

Many clothing products specify their **fiber composition** (“50% cotton, 30% polyester, …”) along with **fabric part labels** (“Main: …”, “Lining: …”, etc.). This pipeline:

1. **Reads** CSV files containing columns like `product_id`, `product_category`, and `care_label`.
2. **Parses** each care label, extracting:
   - **Parts** (e.g. “Main,” “Contrast,” “Lining,” “Unknown”).
   - **Fibers** and their percentages.
   - **Weight** (e.g. “300 g/m²”).
   - **Metadata** like brand names (“cordura,” “sorona”) or flags for “made_in_france,” “recycled,” etc.
3. **Stores** the parsed information in a SQLite database (or any other DB supported by the included exporter).

---

## Features

- **Regex-based** extraction of:
  - Fiber percentages (e.g. `(\d+)% cotton`).
  - Fabric weights (e.g. `300 g/m²`).
  - Labeled sections (`Main: …`, `Reinforcement: …`, etc.).
- **Metadata detection** (brands, “fr,” “solution dyed,” “recycled,” …) with easy extension in `METADATA_DICT`.
- **Fuzzy matching** of fiber names to canonical forms (`FuzzyFiberMatcher`).
- **Two-phase** approach:
  1. Build frequency maps of all encountered fiber names.
  2. Pre-populate fuzzy matching with frequent terms.
- **Data schema**:
  - **Product** (product-level info like category, sub-category).
  - **Part** (each labeled part in the care label).
  - **Fiber** (each fiber composition line).
- **SQL export** with `SQLExporter`: automatically creates tables and inserts data.

---

## Project Structure

A typical layout might look like this:

```
├── /data
│   └──data.csv
├── /src
│   └── constants.py
│      ├── PART_REGEX
│      ├── FIBER_REGEX
│      ├── WEIGHT_REGEX
│      └── METADATA_DICT
│   └── data_cleaning.py
│      ├── class FiberParser
│      ├── class FuzzyFiberMatcher
│      └── helpers (normalize_fiber_name, split_category_subcategory, etc.)
│   └── models.py
│      ├── class Fiber
│      ├── class Part
│      └── class Product
│   └── sql_export.py
│      ├── class SQLExporter class to help export data using sqlite
├── main.py
│   ├── build_frequency_map
│   ├── load_csv_and_parse
│   ├── parse_product_care_label
│   ├── main() -> orchestrates the pipeline
├── requirements.txt
├── notebook.ipynb notebook to validate the results
├── README.md (this file)

```

### Key Files

- **`constants.py`**  
  Contains compiled regex objects and metadata tokens (`METADATA_DICT`).
- **`data_cleaning.py`**  
  Houses the **`FiberParser`** (core parsing logic) and **`FuzzyFiberMatcher`**.  
- **`models.py`**  
  Pydantic data models for `Product`, `Part`, and `Material`.  
- **`main.py`**  
  The main pipeline script, including:
  - CSV reading,
  - Frequency map building,
  - Pre-populating fuzzy matcher,
  - Parsing each line’s care label,
  - Exporting to a database.  
- **`requirements.txt`**  
  Lists Python dependencies (e.g. `pytest`, `fuzzywuzzy`, `sqlite3`, etc.).

---

## Installation

1. **Clone** this repository:

   ```bash
   git clone https://github.com/yourusername/care-label-parser.git
   cd care-label-parser
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### 1. Data Cleaning & Parsing

The **`data_cleaning.FiberParser`** class is the primary entry point for parsing. For example:

```python
from data_cleaning import FiberParser

care_label_text = "Main: 50% HPPE, 16% nylon, 9% spandex, 25% metal fibre...
Reinforcement: 100% Cordura® Recycled"

parsed = FiberParser.parse_care_label(care_label_text, verbose=True)

print(parsed)
```

### 2. Running the Pipeline

To run the **entire pipeline**:

1. Ensure your CSV has columns like:
   - `product_id`
   - `product_category`
   - `care_label`
2. Update paths and DB settings in **`main.py`** if necessary.
3. Run:

   ```bash
   python main.py
   ```

---

## Configuration

- **`METADATA_DICT`** in `constants.py`:
  ```python
  METADATA_DICT = {
      "brand": ["sorona", "cordura", "repreve"],
      "made_in_france": ["fr"],
      "solution_dyed": ["solution dyed"],
      "recycled": ["recycled"]
  }
  ```
  Add or remove keywords as needed.

- **Regex Patterns** in `constants.py` can be customized if care labels have unusual formatting.

---

## Extending & Customizing

1. **Add new metadata fields**  
   - Update `METADATA_DICT` with new tokens.
   - Extend `METADATA_SPECS` with new fields.

2. **Fuzzy Matching**  
   - Tweak `FuzzyFiberMatcher` to adjust threshold or implement advanced matching logic.

3. **Custom DB**  
   - Modify `SQLExporter` for PostgreSQL, MySQL, or other database systems.

---

## License

```
MIT License

Copyright (c) 2025 Alice Berthaux

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
...
```

---

