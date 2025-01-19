
# Care Label Parsing & Data Pipeline

This repository provides a **data pipeline** for parsing clothing care labels, extracting material compositions, weights, and various metadata fields (e.g., brand names, “made in France,” “solution-dyed,” “recycled,” etc.). The parsed results are then stored in a relational database.

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

Many clothing products specify their **material composition** (“50% cotton, 30% polyester, …”) along with **fabric part labels** (“Main: …”, “Lining: …”, etc.). This pipeline:

1. **Reads** CSV files containing columns like `product_id`, `product_category`, and `care_label`.
2. **Parses** each care label, extracting:
   - **Parts** (e.g. “Main,” “Contrast,” “Lining,” “Unknown”).
   - **Materials** and their percentages.
   - **Weight** (e.g. “300 g/m²”).
   - **Metadata** like brand names (“cordura,” “sorona”) or flags for “made_in_france,” “recycled,” etc.
3. **Stores** the parsed information in a SQLite database (or any other DB supported by the included exporter).

---

## Features

- **Regex-based** extraction of:
  - Material percentages (e.g. `(\d+)% cotton`).
  - Fabric weights (e.g. `300 g/m²`).
  - Labeled sections (`Main: …`, `Reinforcement: …`, etc.).
- **Metadata detection** (brands, “fr,” “solution dyed,” “recycled,” …) with easy extension in `METADATA_DICT`.
- **Fuzzy matching** of material names to canonical forms (`FuzzyMaterialMatcher`).
- **Two-phase** approach:
  1. Build frequency maps of all encountered material names.
  2. Pre-populate fuzzy matching with frequent terms.
- **Data schema**:
  - **Product** (product-level info like category, sub-category).
  - **Part** (each labeled part in the care label).
  - **Material** (each material composition line).
- **SQL export** with `SQLExporter`: automatically creates tables and inserts data.

---

## Project Structure

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
│      ├── class MaterialParser
│      ├── class FuzzyMaterialMatcher
│      └── helpers (normalize_material_name, split_category_subcategory, etc.)
│   └── models.py
│      ├── class Material
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

- **`notebook.ipynb`**
  Perform basic data analysis on the data to assess its quality.
- **`constants.py`**  
  Contains compiled regex objects and metadata tokens (`METADATA_DICT`).
- **`data_cleaning.py`**  
  Houses the **`MaterialParser`** (core parsing logic) and **`FuzzyMaterialMatcher`**.  
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
   git clone https://github.com/Alberthaux/data_parser.git
   cd data_parser
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### 1. Data Cleaning & Parsing

The **`data_cleaning.MaterialParser`** class is the primary entry point for parsing. For example:

```python
from data_cleaning import MaterialParser

care_label_text = "Main: 50% HPPE, 16% nylon, 9% spandex, 25% metal fibre...
Reinforcement: 100% Cordura® Recycled"

parsed = MaterialParser.parse_care_label(care_label_text, verbose=True)

print(parsed)
```

### 2. Running the Pipeline

To run the **entire pipeline**:

1. Ensure your CSV has columns like:
   - `product_id`
   - `product_category`
   - `care_label`
2. Run:

   ```bash
    python main.py -p data/data.csv 
   ```
   it will create a products.bb file

### 3. Analyse products.db 

  See notebook.ipynb for reference

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
# Text Normalization and Database Schema Explanation

## Text Normalization

Text normalization is a critical step in ensuring consistency across the parsed data. The pipeline implements normalization at several levels:

### Category, Part Name, and Subcategory
These fields are standardized by converting them to lowercase and ensuring they are in their singular form. For example, `"ACCESSORIES/PHONE-CASES"` becomes `"accessory"` for the category and `"phone-case"` for the subcategory.

### Material Name Regularization
Material names, which can often be messy due to variations in spelling, punctuation, or case, are first normalized (e.g., lowercased and stripped of extraneous characters) and then further refined using fuzzy matching with `fuzzywuzzy`. This ensures that similar material descriptions (e.g., `"Cottons"`, `"cotton"`, or `"cotton®"`) are mapped to a canonical version such as `"cotton"`. We also store brand or other metadata information in separate columns "brand", "made_in_france"...

This normalization process significantly improves the consistency and quality of the final exported data, making downstream analysis more reliable.

## Database Schema Explanation

The pipeline is designed around three core models which map directly to database tables:

### Product Table
- **Fields:** `product_id`, `product_category`, `product_sub_category`, `original_care_label`
- **Rationale:**  
  This table stores information at the product level. The category and subcategory fields are normalized (lowercase and singular) to maintain uniformity, allowing easy grouping and filtering during analysis.

### Part Table
- **Fields:** `part_id` (unique), `product_id`, `name`, `weight`, `weight_unit`
- **Rationale:**  
  A product's care label may include multiple parts (e.g., "main", "lining", "reinforcement"). By storing these in a dedicated Part table and linking them to the product via `product_id`, we capture this hierarchical structure and facilitate queries that differentiate between different fabric parts.

### Material Table
- **Fields:** `material_id`, `product_id`, `part_id`, `name`, `proportion`, `brand`, `original_material_name`, `made_in_france`, `solution_dyed`, `recycled`
- **Rationale:**  
  Each fabric part may contain multiple material types, each with its associated percentage and metadata. The material names undergo normalization and fuzzy matching to ensure consistency, and additional fields capture metadata (e.g., whether the material is recycled or made in France). This granular level of detail supports detailed material analyses and quality checks.

The separation of data into these tables follows a normalized relational design. This approach:
- Minimizes data redundancy.
- Improves data integrity.
- Facilitates complex queries (e.g., summing material percentages per part or categorizing products by subcategory).


## Extending & Customizing

1. **Add new metadata fields**  
   - Update `METADATA_DICT` with new tokens.
   - Extend `METADATA_SPECS` with new fields.

2. **Fuzzy Matching**  
   - Tweak `FuzzyMaterialMatcher` to adjust threshold or implement advanced matching logic.

3. **Custom DB**  
   - Modify `SQLExporter` for PostgreSQL, MySQL, or other database systems.

---

