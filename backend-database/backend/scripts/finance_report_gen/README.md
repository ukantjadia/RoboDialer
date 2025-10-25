# Financial Database Population Scripts

This directory contains Python scripts to populate the financial database tables with KPI data extracted from the CSV file.

## 📁 Files

- **`kpi_data_structured.csv`** - Structured KPI data with all required fields
- **`populate_standard_columns.py`** - Populates the `standard_column_definitions` table
- **`populate_kpi_definitions.py`** - Populates the `kpi_definitions` table
- **`populate_industry_benchmarks.py`** - Populates the `industry_benchmarks` table
- **`populate_all_tables.py`** - Master script that runs all three scripts in order
- **`README.md`** - This documentation file

## 🔬 How Data Is Generated and Calculated

### Standard Column Definitions (`standard_column_definitions`)
- Source: Unique values extracted from the CSV column `Column Name(s)`.
- Normalization and de-duplication:
  - Trims whitespace, collapses multiple spaces, preserves business casing where meaningful (e.g., PPE, SG&A).
  - De-duplicates across all rows; case-insensitive comparison to avoid duplicates like "Revenue" vs "revenue".
- File-type tagging:
  - Uses the CSV `Files Used` context plus keyword heuristics to map to one or more types: `income_statement`, `balance_sheet`, `cash_flow`, `external_data`, `market_data`, `budget`, `process`, `documentation`, etc.
  - If no match, defaults to `financial_statement` so a column remains discoverable across statements.
- Categorization and subcategories:
  - Deterministic mapping places each column into a top-level bucket such as Revenue, Income, Assets, Liabilities, Equity, Costs, Cash Flow, Market Data, Working Capital, Operating Metrics, Budget, Marketing, Accounts Receivable, Procurement, Financial Metrics, Dividends.
  - Subcategories standardize variants (e.g., `Operating Income`, `Net Sales`, `Cash & Equivalents`, `Accounts Receivable`).
- Expected data type inference:
  - Currency for monetary metrics (revenue, income, assets, liabilities, equity, expenses, cash, debt).
  - Percentage for ratios/margins/rates regardless of percent sign presence.
  - Integer for counts, shares, employees, days, months, years.
  - Decimal fallback when none of the above apply.
- Validation profile:
  - `pattern_matches` enforce basic formatting per type (numeric with thousands separators for currency, optional percent sign for percentages, digits-only for integers).
  - `validation_rules` set min/max where sensible; e.g., default non-negative for currency/integer/percentage. You can later relax these for domains that accept negatives (losses, working capital deficits).
- Synonyms and searchability:
  - Generates common aliases to improve matching from user-uploaded files (e.g., Revenue → Sales, Turnover; Net Income → Earnings).
  - Synonyms are stored as JSON for future NLP-assisted mapping.
- Administrative fields:
  - `is_required` toggled for critical metrics (revenue, income, assets, equity, cash, debt).
  - `priority_score` emphasizes important columns in UIs/suggestions.
- Idempotency and safety:
  - Upserts are conservative: if a `column_name` already exists, it is skipped to prevent accidental overrides.

### KPI Definitions (`kpi_definitions`)
- Source: Each CSV row describes one KPI definition.
- Field construction:
  - `kpi_name`, `description`, `category`, `priority_order` copied from CSV after trimming.
  - `formula` stored verbatim for transparency; evaluation is out of scope here and belongs to the KPI engine.
  - `required_columns` parsed from `Column Name(s)` preserving business labels to be mapped later against standard columns.
  - `optional_columns` left empty by default; can be extended to list alternates or substitutes.
- Formula typing:
  - If `Formula Type` exists, it is respected.
  - Otherwise inferred: presence of arithmetic operators suggests a complex formula; terms like DSO/DIO/DPO/AVG/NOPAT/WACC escalate to `custom_logic` due to multi-step derivations.
- Dependencies and compute order:
  - Heuristics add dependency hints (e.g., DSO requires average AR and revenue across periods; CCC depends on DSO/DIO/DPO).
  - `dependency_level` summarizes complexity (1=base KPI, 2=derived, 3=multi-layer/custom). This can drive calculation sequencing.
- Industry benchmark payload within KPI definitions:
  - The `Industry Thresholds` string is parsed into structured JSON capturing industry, operator, benchmark type, and value.
  - Values are numeric-normalized; percent symbols are optional and do not block parsing.
- Ranges and numeric constraints:
  - `expected_range_min` and `expected_range_max` are parsed and clamped into the database’s Numeric(10,4) safe range. This protects against overflow while preserving intent.
- Notes and provenance:
  - `calculation_notes` embeds a compact provenance trail: key inputs (files used) and formula expression to aid auditors or an LLM.
- Write-path behavior:
  - Per-record flush detects individual issues early; on any error the session is rolled back for that record only and processing continues.
  - Existing `kpi_name` entries are skipped; no destructive updates occur from these scripts.

### Industry Benchmarks (`industry_benchmarks`)
- Parsing grammar for `Industry Thresholds` values:
  - Comparatives: patterns like `Retail > 5%`, `Tech < 30`, `Mfg >= 7%` produce a single record with `benchmark_type` inferred from the operator (minimum for greater-than comparisons, maximum for less-than).
  - Ranged thresholds: `Retail: 15-25%` expands to two records, one minimum and one maximum, creating an allowable band.
  - Universal constraints: phrases like `All > 1 preferred` map to `All Industries` for portability across sectors.
  - Composite descriptors: Altman Z-Score conventions are split into multiple entries capturing separate safe/gray/distress boundaries with `score` unit.
- Unit inference:
  - KPI family drives unit selection: margins and ratios as percentage, cycle metrics as days, turnover as times, solvency coverage as ratio, valuation multiples as ratio, Altman as score, currency for large absolute values when appropriate.
  - Ambiguous cases use magnitude-aware defaults but remain editable later.
- Numeric normalization and integrity:
  - All benchmark values are clamped to Numeric(10,4) safety bounds and rounded to four decimals to match storage precision.
  - Year, sample size, and confidence level are populated with sensible defaults to keep records analytically useful while you refine sources.
- Idempotent inserts and per-record isolation:
  - A benchmark is uniquely identified by `(industry_name, kpi_name, benchmark_type)`; duplicates are skipped.
  - Per-record flush and rollback allow partial success and full visibility into failures.



## Outputs
- `preview_standard_columns.csv`
- `preview_kpi_definitions.csv`
- `preview_industry_benchmarks.csv`

## Shared utilities
- File-type parsing: Normalizes `Files Used` labels and supports multi-mapped entries (e.g., `Marketing/Income` → `marketing`, `income_statement`).
- Numeric clamping: Values destined for Numeric(10,4) are clamped to ±999,999.9999 and rounded to 4 decimals.
- Units: Inferred from KPI name keywords and value magnitude (`percentage`, `days`, `times`, `ratio`, `score`, `currency`, fallback `units`).
- Synonyms: Generated via normalized forms (snake_case, camelCase, nospace, hyphenated), curated aliases (e.g., SG&A, COGS), and light typo generation (duplicated last character for short words).

## 1) Standard columns (preview_standard_columns.csv)
For each row in the input CSV:
- Parse `Files Used` to a canonical list of file types using a synonym map and simple heuristics.
- Split `Column Name(s)` by comma to collect referenced columns.
- Build a mapping: `column_name` → union of all file types encountered across rows.
- For each unique `column_name`:
  - `applicable_file_types`: sorted unique list from the mapping (JSON string in CSV).
  - `expected_data_type`: inferred by keywords in the column name (currency/percentage/integer/decimal).
  - `column_category`: simple keyword-based categorization (Revenue, Income, Assets, Liabilities, Equity, Costs, Cash Flow, Market Data, Working Capital; otherwise `Financial Metrics`).
  - `column_subcategory`: set to `General` in the preview.
  - `is_required`: true if column name contains any of revenue, income, assets, equity, cash, debt.
  - `priority_score`: 1 if required else 2.
  - `synonyms`: generated list serialized as JSON.
  - `validation_rules`: JSON with basic min/max/required/data_type hints.
  - `description`: generic description.

## 2) KPI definitions (preview_kpi_definitions.csv)
For each KPI row:
- `kpi_name`, `description`, `formula`, `category`, `priority_order`: taken from CSV (trimmed).
- `required_columns`: parsed from `Column Name(s)` (JSON in CSV). `optional_columns` is an empty list.
- `formula_type`:
  - If CSV provides it, use it.
  - Else infer: if arithmetic is present, `complex_formula`; if special terms (DSO/DIO/DPO/AVG/NOPAT/WACC) appear, `custom_logic`; otherwise `simple_ratio`.
- `dependencies`: heuristic hints (period comparison if "average" in required columns; inventory/receivables/payables metrics based on formula keywords). `dependency_level` derived from dependency complexity.
- `industry_benchmarks`: parsed from `Industry Thresholds` into structured JSON (see below) and serialized to CSV.
- `expected_range_min/max`: clamped to Numeric(10,4) and stringified.
- `calculation_notes`: compact provenance with formula and files used.
- `is_active`: true.

## 3) Industry benchmarks (preview_industry_benchmarks.csv)
For each KPI row with `Industry Thresholds`:
- Split thresholds by comma and parse each segment.
- Comparatives: `Industry > X` or `Industry >= X` create a record with `benchmark_type = minimum` and value X.
- Upper bounds: `Industry < X` or `Industry <= X` create a record with `benchmark_type = industry_average` and value X (aligned to DB Enum).
- Ranges: `Industry: A-B%` create two records: `minimum` for A, `industry_average` for B.
- Altman Z-Score descriptors: create `minimum` (safe) and `industry_average` (distress) records with `score` unit.
- Strong/Adequate/Weak patterns: create `minimum` (strong) and `industry_average` (weak) records with `ratio` unit.
- Universal rules: `All > X` maps to `industry_name = All Industries` with `minimum`; `All < X` uses `industry_average`.
- Each record includes: `industry_name`, `kpi_name`, `benchmark_type`, `benchmark_value` (clamped), `benchmark_unit` (inferred), `data_source`, `data_year`, `sample_size`, `confidence_level` (string `'0.9500'`), `is_active`.

## Parity and limitations
- The preview mirrors DB insertion logic for parsing, clamping, units, file-type mapping, synonyms, and benchmark typing.
- Differences vs DB scripts:
  - Preview serializes JSON fields as strings and writes numerics as strings for CSV.
  - Preview uses a simple category and sets subcategory to `General`; DB insertion uses a richer subcategory map and may add `pattern_matches`.
  - `confidence_level` is a string in preview (e.g., `'0.9500'`), converted to Decimal(0.95) during DB import.


## 📊 What Each Script Does

### 1. Standard Column Definitions (`populate_standard_columns.py`)
- Extracts unique column names from the KPI CSV
- Creates standard definitions for each financial column
- Maps columns to appropriate categories and file types
- Sets validation rules and expected data types
- **Table**: `standard_column_definitions`

### 2. KPI Definitions (`populate_kpi_definitions.py`)
- Creates KPI definition records from the CSV data
- Parses formulas and determines formula types
- Identifies required columns and dependencies
- Sets priority orders and expected ranges
- **Table**: `kpi_definitions`

### 3. Industry Benchmarks (`populate_industry_benchmarks.py`)
- Extracts industry threshold data from the CSV
- Creates benchmark records for each industry
- Handles various threshold formats (>, <, ranges)
- Sets appropriate units and confidence levels
- **Table**: `industry_benchmarks`

## 🔧 Prerequisites

1. **Database Connection**: Ensure your database is running and accessible
2. **Models**: The scripts import from `models.lead_model` and the finance models
3. **Python Path**: Scripts automatically add the correct paths for imports
4. **CSV File**: The `kpi_data_structured.csv` file must be present

## 📝 Logging

Each script creates detailed logs:
- **Console Output**: Real-time progress and errors
- **Log Files**: Detailed logs saved to files:
  - `standard_columns_population.log`
  - `kpi_definitions_population.log`
  - `industry_benchmarks_population.log`
  - `master_population.log` (when using the master script)

## ⚠️ Error Handling

- **Duplicate Prevention**: Scripts check for existing records and skip them
- **Graceful Failures**: If one record fails, the script continues with others
- **Transaction Safety**: Database changes are committed only if successful
- **Detailed Error Logging**: All errors are logged with context

## 📋 CSV Structure

The `kpi_data_structured.csv` file contains these columns:
- `S.No.` - Serial number
- `KPI Name` - Name of the KPI
- `Description` - Description of what the KPI measures
- `Formula` - Mathematical formula for calculation
- `Files Used` - Which financial statements are needed
- `Column Name(s)` - Required data columns
- `Category` - KPI category (Profitability, Liquidity, etc.)
- `Industry Thresholds` - Industry-specific benchmark values
- `Formula Type` - Type of formula (simple_ratio, complex_formula, custom_logic)
- `Priority Order` - Priority ranking
- `Expected Range Min` - Minimum expected value
- `Expected Range Max` - Maximum expected value

**Note**: These scripts are designed to be safe and can be run multiple times without causing data duplication or corruption.