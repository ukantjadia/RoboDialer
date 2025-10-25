#!/usr/bin/env python3
"""
Preview generator for database inserts.
Reads kpi_data_structured.csv and produces three preview CSVs showing what
would be inserted into:
- standard_column_definitions
- kpi_definitions
- industry_benchmarks

No database writes are performed.
"""

import csv
import json
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime

INPUT_CSV = Path(__file__).parent / 'kpi_data_structured.csv'
OUT_STD_COLS = Path(__file__).parent / 'preview_standard_columns.csv'
OUT_KPI_DEFS = Path(__file__).parent / 'preview_kpi_definitions.csv'
OUT_BENCH = Path(__file__).parent / 'preview_industry_benchmarks.csv'


# --------------------- Utilities shared with population scripts ---------------------

def normalize_token(token: str) -> str:
    return token.strip().lower()


def get_file_type_synonym_map():
    return {
        'income statement': 'income_statement',
        'income st.': 'income_statement',
        'income statement (modified)': 'income_statement',
        'balance sheet': 'balance_sheet',
        'cash flow': 'cash_flow',
        'cash flow statement': 'cash_flow',
        'cash flow/income statement': None,
        'external input': 'external_input',
        'stock data': 'stock_data',
        'shareholder reports': 'shareholder_reports',
        'debt schedules': 'debt_schedules',
        'ar aging': 'ar_aging',
        'ap records': 'ap_records',
        'cost accounting': 'cost_accounting',
        'budget vs actuals': 'budget_vs_actuals',
        'budget process records': 'budget_process_records',
        'budget documentation': 'budget_documentation',
        'hr records': 'hr_records',
        # multi-map
        'marketing/income': ['marketing', 'income_statement'],
    }


def parse_files_used_cell(files_used_raw: str) -> list:
    if not files_used_raw:
        return []
    syn = get_file_type_synonym_map()
    parts = [p.strip() for p in files_used_raw.split(',') if p and p.strip()]
    tokens = []
    for p in parts:
        tokens.extend([s.strip() for s in p.replace(' / ', '/').split('/') if s and s.strip()])
    canonical = []
    for t in tokens:
        key = normalize_token(t)
        mapped = syn.get(key)
        if mapped is None:
            # not explicitly handled, try heuristics
            if 'income' in key:
                mapped = 'income_statement'
            elif 'balance' in key:
                mapped = 'balance_sheet'
            elif 'cash flow' in key or 'cashflow' in key:
                mapped = 'cash_flow'
        if mapped:
            if isinstance(mapped, list):
                canonical.extend(mapped)
            else:
                canonical.append(mapped)
    # dedupe
    seen, result = set(), []
    for c in canonical:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def clamp_decimal_str_to_numeric_10_4(value_str):
    if value_str in (None, ''):
        return None
    try:
        val = Decimal(value_str)
        max_abs = Decimal('999999.9999')
        if val > max_abs:
            val = max_abs
        if val < -max_abs:
            val = -max_abs
        return val.quantize(Decimal('0.0001'))
    except (InvalidOperation, ValueError, TypeError):
        return None


def clamp_decimal_to_numeric_10_4(val):
    try:
        dec = Decimal(str(val))
        max_abs = Decimal('999999.9999')
        if dec > max_abs:
            dec = max_abs
        if dec < -max_abs:
            dec = -max_abs
        return dec.quantize(Decimal('0.0001'))
    except (InvalidOperation, ValueError, TypeError):
        return None


def determine_unit(kpi_name, value):
    k = (kpi_name or '').lower()
    if any(x in k for x in ['ratio', 'margin', 'percentage', 'rate']):
        return 'percentage'
    if any(x in k for x in ['days', 'dso', 'dio', 'dpo']):
        return 'days'
    if any(x in k for x in ['turnover', 'times']):
        return 'times'
    if any(x in k for x in ['months', 'years']):
        return 'months' if (value or 0) < 24 else 'years'
    if any(x in k for x in ['score', 'z-score']):
        return 'score'
    if any(x in k for x in ['cost', 'dollars']):
        return 'dollars'
    if value is not None:
        try:
            v = float(value)
            if abs(v) > 1000:
                return 'currency'
            if abs(v) <= 1:
                return 'ratio'
        except Exception:
            pass
    return 'units'

# --------------------- Synonym generation (parity with DB script) ---------------------

def tokenize_words(s: str) -> list:
    import re
    s = s.replace('&', ' and ')
    s = re.sub(r'[^A-Za-z0-9\s]', ' ', s)
    parts = [p for p in s.strip().split() if p]
    return parts


def to_snake(parts: list) -> str:
    return '_'.join(p.lower() for p in parts)


def to_camel(parts: list) -> str:
    if not parts:
        return ''
    return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])


def to_nospace(parts: list) -> str:
    return ''.join(p.lower() for p in parts)


def dup_last_char(word: str) -> str:
    if not word:
        return word
    if len(word) <= 5:
        return word + word[-1]
    return word


def predefined_synonyms_map():
    return {
        'Total Debt': ['debt', 'total_debt', 'debt_total', 'ttl_debt'],
        'Long-Term Debt': ['long term debt', 'lt debt', 'ltd', 'longterm debt', 'lt_debt'],
        'Tax Rate': ['tax rate', 'tax', 'taxes', 'tax pct', 'tax percent', 'effective tax rate', 'income tax rate'],
        'Operating Income (EBIT)': ['operating income', 'operating profit', 'operating earnings', 'ebit', 'earnings before interest and taxes'],
        'Operating Income': ['operating income', 'operating profit', 'operating earnings', 'ebit'],
        'EBIT': ['ebit', 'earnings before interest and taxes'],
        'EBITDA': ['ebitda', 'earnings before interest taxes depreciation and amortization', 'earnings before interest, taxes, depreciation and amortization'],
        'SG&A': ['sga', 'sg and a', 'selling general and administrative', 'selling, general and administrative'],
        'SG&A Expenses': ['sg&a', 'sga', 'selling general and administrative', 'selling, general and administrative'],
        'COGS': ['cogs', 'cost of goods sold', 'cost_of_goods_sold', 'cost of sales', 'cost_of_sales'],
        'Cost of Revenue': ['cost of revenue', 'cor', 'cost of sales', 'cost_of_sales'],
        'Net Income': ['net income', 'profit', 'earnings', 'net profit', 'ni'],
        'Total Revenue': ['revenue', 'sales', 'turnover', 'total revenue'],
        'Operating Cash Flow': ['operating cash flow', 'ocf', 'cash from operations', 'cash flow from operations', 'operating cashflow', 'operating_cf'],
        'Accounts Receivable': ['accounts receivable', 'ar', 'trade receivables', 'receivables'],
        'Accounts Payable': ['accounts payable', 'ap', 'trade payables', 'payables'],
        'Inventory': ['inventory', 'inventories', 'stock'],
        'Current Assets': ['current assets', 'current_assets', 'ca'],
        'Current Liabilities': ['current liabilities', 'current_liabilities', 'cl'],
        'Total Assets': ['total assets', 'assets total', 'ta'],
        'Total Liabilities': ['total liabilities', 'liabilities total', 'tl'],
        'Total Equity': ['total equity', 'equity total', 'net assets', "shareholders' equity", 'shareholder equity', 'stockholders equity'],
        'Shareholder Equity': ["shareholders' equity", 'shareholder equity', 'stockholders equity', 'equity'],
        'WACC': ['wacc', 'weighted average cost of capital', 'weighted avg cost of capital'],
        'NOPAT': ['nopat', 'net operating profit after tax'],
        'Capex': ['capex', 'capital expenditure', 'capital expenditures', 'capital exp', 'capital_expenditure'],
        'Market Cap': ['market cap', 'market capitalization', 'marketcapitalization', 'mkt cap'],
        'EPS': ['eps', 'earnings per share', 'earnings/share'],
        'Dividends per Share': ['dividend per share', 'dps', 'dividends/share'],
        'Annual Dividend per Share': ['dividend per share', 'dps', 'annual dividend/share'],
        'Tax Provision': ['income tax expense', 'tax expense', 'provision for income taxes'],
        'Operating Expense': ['operating expenses', 'opex', 'operating expenditure'],
        'Net PPE': ['pp&e', 'ppe', 'property plant and equipment', 'property, plant & equipment'],
        'Interest Expense': ['interest expense', 'interest', 'finance cost', 'financing cost'],
        'Working Capital': ['working capital', 'net working capital', 'nwc'],
    }


def generate_synonyms(column_name: str) -> list:
    base = column_name.strip()
    parts = tokenize_words(base)
    syns = set()

    pre = predefined_synonyms_map().get(base)
    if pre:
        for p in pre:
            syns.add(p)

    snake = to_snake(parts)
    camel = to_camel(parts)
    nospace = to_nospace(parts)
    hyphen = '-'.join(p.lower() for p in parts)

    for v in [base.lower(), snake, camel, nospace, hyphen]:
        if v:
            syns.add(v)

    if ' and ' in base.lower() or '&' in base:
        amp = base.replace(' and ', ' & ').replace(' And ', ' & ').replace('AND', '&')
        syns.add(amp.lower())
        words = tokenize_words(amp)
        syns.add(to_snake(words))
        syns.add(to_nospace(words))

    if parts:
        last = parts[-1]
        typo = dup_last_char(last)
        if typo != last:
            for t in [typo, f"{to_snake(parts[:-1] + [typo])}", f"{to_nospace(parts[:-1] + [typo])}"]:
                syns.add(t)

    if base.lower() in ['sg&a', 'sg&a expenses']:
        syns.add('sga')
        syns.add('sg and a')
        syns.add('sg-a')

    ordered = []
    for v in [base.lower(), snake, nospace, camel, hyphen] + list(sorted(syns)):
        if v and v not in ordered:
            ordered.append(v)
    return ordered[:20]


# --------------------- Standard Columns Preview ---------------------

def build_standard_columns_preview(rows):
    # Build column -> file types mapping and collect unique columns
    column_to_types = {}
    unique_columns = set()
    for r in rows:
        file_types = parse_files_used_cell(r.get('Files Used', ''))
        col_names = [c.strip() for c in (r.get('Column Name(s)', '') or '').split(',') if c and c.strip()]
        for col in col_names:
            unique_columns.add(col)
            column_to_types.setdefault(col, set()).update(file_types)

    def expected_type(col):
        lc = col.lower()
        if any(k in lc for k in ['revenue', 'income', 'assets', 'liabilities', 'equity', 'cost', 'expense', 'cash', 'debt']):
            return 'currency'
        if any(k in lc for k in ['ratio', 'margin', 'percentage', 'rate']):
            return 'percentage'
        if any(k in lc for k in ['count', 'number', 'shares', 'employees', 'days', 'months', 'years']):
            return 'integer'
        return 'decimal'

    def category_for(col):
        mapping = {
            'revenue': 'Revenue', 'net sales': 'Revenue',
            'income': 'Income', 'ebit': 'Income', 'gross profit': 'Income',
            'asset': 'Assets', 'ppe': 'Assets', 'intangibles': 'Assets', 'goodwill': 'Assets',
            'liabilit': 'Liabilities', 'payable': 'Liabilities', 'debt': 'Liabilities',
            'equity': 'Equity', 'retained': 'Equity', 'shares': 'Equity',
            'cogs': 'Costs', 'expense': 'Costs', 'sg&a': 'Costs', 'r&d': 'Costs', 'overhead': 'Costs',
            'cash': 'Cash Flow', 'capex': 'Cash Flow', 'dividend': 'Cash Flow',
            'price': 'Market Data', 'market cap': 'Market Data', 'eps': 'Market Data',
            'working capital': 'Working Capital',
        }
        lc = col.lower()
        for key, cat in mapping.items():
            if key in lc:
                return cat
        return 'Financial Metrics'

    records = []
    for col in sorted(unique_columns):
        app_types = list(sorted(column_to_types.get(col, set()))) or ['financial_statement']
        etype = expected_type(col)
        is_required = any(k in col.lower() for k in ['revenue', 'income', 'assets', 'equity', 'cash', 'debt'])
        priority = 1 if is_required else 2
        synonyms = generate_synonyms(col)

        records.append({
            'column_name': col,
            'column_category': category_for(col),
            'column_subcategory': 'General',
            'applicable_file_types': json.dumps(app_types),
            'expected_data_type': etype,
            'is_required': is_required,
            'priority_score': priority,
            'synonyms': json.dumps(synonyms),
            'validation_rules': json.dumps({
                'min_value': 0 if etype in ['currency', 'percentage', 'integer'] else None,
                'max_value': None,
                'required': is_required,
                'data_type': etype,
            }),
            'description': f'Standard column for {col.lower()} data',
        })
    return records


# --------------------- KPI Definitions Preview ---------------------

def parse_industry_thresholds(thresholds_str):
    import re
    if not thresholds_str or thresholds_str.strip() == '':
        return []
    thresholds = []
    parts = thresholds_str.split(',')
    for part in parts:
        p = part.strip()
        if not p:
            continue
        # Align with DB: allow >, <, :
        m = re.match(r'([A-Za-z\s&]+)\s*([><:]+)\s*([0-9.]+)\s*%?', p)
        if m:
            industry = m.group(1).strip()
            operator = m.group(2).strip()
            value = float(m.group(3))
            if operator in ['>', '>=']:
                btype = 'minimum'
            elif operator in ['<', '<=']:
                btype = 'industry_average'
            else:
                btype = 'target'
            thresholds.append({'industry': industry, 'benchmark_type': btype, 'value': value, 'operator': operator})
        else:
            if 'All' in p:
                m2 = re.search(r'([><]+)\s*([0-9.]+)', p)
                if m2:
                    op = m2.group(1)
                    val = float(m2.group(2))
                    btype = 'minimum' if op == '>' else 'industry_average'
                    thresholds.append({'industry': 'All Industries', 'benchmark_type': btype, 'value': val, 'operator': op})
    return thresholds


def build_kpi_definitions_preview(rows):
    records = []
    for r in rows:
        kpi_name = (r.get('KPI Name') or '').strip()
        if not kpi_name:
            continue
        description = (r.get('Description') or '').strip()
        formula = (r.get('Formula') or '').strip()
        files_used = (r.get('Files Used') or '').strip()
        column_names = (r.get('Column Name(s)') or '').strip()
        category = (r.get('Category') or 'Financial Metrics').strip()
        industry_thresholds = (r.get('Industry Thresholds') or '').strip()
        formula_type_str = (r.get('Formula Type') or '').strip()
        priority_order = r.get('Priority Order')
        expected_range_min = r.get('Expected Range Min')
        expected_range_max = r.get('Expected Range Max')

        required_columns = [c.strip() for c in column_names.split(',') if c and c.strip()]
        if formula_type_str:
            formula_type = formula_type_str
        else:
            fl = formula.lower()
            if any(op in fl for op in ['+', '-', '*', '/', '(', ')']):
                if any(t in fl for t in ['average', 'dsi', 'dso', 'dpo', 'nopat', 'wacc']):
                    formula_type = 'custom_logic'
                else:
                    formula_type = 'complex_formula'
            else:
                formula_type = 'simple_ratio'

        dependencies = []
        if any('average' in c.lower() for c in required_columns):
            dependencies.append({'type': 'period_comparison', 'description': 'Requires values from two periods'})
        lf = formula.lower()
        if 'dsi' in lf or 'dio' in lf:
            dependencies.append({'type': 'inventory_metrics', 'description': 'Requires inventory and COGS data from two periods'})
        if 'dso' in lf:
            dependencies.append({'type': 'receivables_metrics', 'description': 'Requires AR and revenue from two periods'})
        if 'dpo' in lf:
            dependencies.append({'type': 'payables_metrics', 'description': 'Requires AP and COGS from two periods'})

        complex_deps = sum(1 for d in dependencies if d['type'] in ['period_comparison', 'custom_logic'])
        dependency_level = 3 if complex_deps > 2 else 2 if complex_deps > 0 else 1

        parsed_thresholds = parse_industry_thresholds(industry_thresholds)
        try:
            prio = int(priority_order) if priority_order not in (None, '') else None
        except Exception:
            prio = None

        records.append({
            'kpi_name': kpi_name,
            'kpi_category': category,
            'kpi_subcategory': category if category else 'General',
            'formula': formula,
            'formula_type': formula_type,
            'required_columns': json.dumps(required_columns),
            'optional_columns': json.dumps([]),
            'dependencies': json.dumps(dependencies),
            'dependency_level': dependency_level,
            'industry_benchmarks': json.dumps(parsed_thresholds),
            'description': description,
            'calculation_notes': f'Formula: {formula}. Files: {files_used}',
            'expected_range_min': str(clamp_decimal_str_to_numeric_10_4(expected_range_min) or ''),
            'expected_range_max': str(clamp_decimal_str_to_numeric_10_4(expected_range_max) or ''),
            'is_active': True,
            'priority_order': prio,
        })
    return records


# --------------------- Industry Benchmarks Preview ---------------------

def parse_benchmarks_to_records(rows):
    import re
    records = []
    current_year = datetime.now().year
    for r in rows:
        kpi_name = (r.get('KPI Name') or '').strip()
        thresholds = (r.get('Industry Thresholds') or '').strip()
        if not kpi_name or not thresholds:
            continue
        parts = thresholds.split(',')
        for part in parts:
            p = part.strip()
            if not p:
                continue
            m = re.match(r'([A-Za-z\s&]+)\s*([><:]+)\s*([0-9.]+)\s*%?', p)
            if m:
                industry = m.group(1).strip()
                operator = m.group(2).strip()
                value = float(m.group(3))
                btype = 'minimum' if operator in ['>', '>='] else 'industry_average' if operator in ['<', '<='] else 'target'
                unit = determine_unit(kpi_name, value)
                records.append({
                    'industry_name': industry,
                    'kpi_name': kpi_name,
                    'benchmark_type': btype,
                    'benchmark_value': str(clamp_decimal_to_numeric_10_4(value) or ''),
                    'benchmark_unit': unit,
                    'data_source': 'Industry Standards',
                    'data_year': current_year,
                    'sample_size': 100,
                    'confidence_level': '0.9500',
                    'is_active': True,
                })
            else:
                # Ranges like Retail: 15-25%
                m2 = re.match(r'([A-Za-z\s&]+):\s*([0-9.]+)-([0-9.]+)%', p)
                if m2:
                    industry = m2.group(1).strip()
                    vmin = float(m2.group(2))
                    vmax = float(m2.group(3))
                    unit = 'percentage'
                    records.append({
                        'industry_name': industry,
                        'kpi_name': kpi_name,
                        'benchmark_type': 'minimum',
                        'benchmark_value': str(clamp_decimal_to_numeric_10_4(vmin) or ''),
                        'benchmark_unit': unit,
                        'data_source': 'Industry Standards',
                        'data_year': current_year,
                        'sample_size': 100,
                        'confidence_level': '0.9500',
                        'is_active': True,
                    })
                    records.append({
                        'industry_name': industry,
                        'kpi_name': kpi_name,
                        'benchmark_type': 'industry_average',
                        'benchmark_value': str(clamp_decimal_to_numeric_10_4(vmax) or ''),
                        'benchmark_unit': unit,
                        'data_source': 'Industry Standards',
                        'data_year': current_year,
                        'sample_size': 100,
                        'confidence_level': '0.9500',
                        'is_active': True,
                    })
                else:
                    # Altman-style descriptors (Safe/Gray/Distress)
                    if any(term in p for term in ['Safe', 'Gray', 'Distress']):
                        nums = re.findall(r'([0-9.]+)', p)
                        if len(nums) >= 2:
                            safe_v = float(nums[0])
                            distress_v = float(nums[1])
                            records.append({
                                'industry_name': 'All Industries',
                                'kpi_name': kpi_name,
                                'benchmark_type': 'minimum',
                                'benchmark_value': str(clamp_decimal_to_numeric_10_4(safe_v) or ''),
                                'benchmark_unit': 'score',
                                'data_source': 'Altman Z-Score Model',
                                'data_year': current_year,
                                'sample_size': 100,
                                'confidence_level': '0.9500',
                                'is_active': True,
                            })
                            records.append({
                                'industry_name': 'All Industries',
                                'kpi_name': kpi_name,
                                'benchmark_type': 'industry_average',
                                'benchmark_value': str(clamp_decimal_to_numeric_10_4(distress_v) or ''),
                                'benchmark_unit': 'score',
                                'data_source': 'Altman Z-Score Model',
                                'data_year': current_year,
                                'sample_size': 100,
                                'confidence_level': '0.9500',
                                'is_active': True,
                            })
                    # Strong/Adequate/Weak patterns
                    elif any(term in p for term in ['Strong', 'Adequate', 'Weak']):
                        nums = re.findall(r'([0-9.]+)', p)
                        if len(nums) >= 2:
                            strong_v = float(nums[0])
                            weak_v = float(nums[1])
                            records.append({
                                'industry_name': 'All Industries',
                                'kpi_name': kpi_name,
                                'benchmark_type': 'minimum',
                                'benchmark_value': str(clamp_decimal_to_numeric_10_4(strong_v) or ''),
                                'benchmark_unit': 'ratio',
                                'data_source': 'Industry Standards',
                                'data_year': current_year,
                                'sample_size': 100,
                                'confidence_level': '0.9500',
                                'is_active': True,
                            })
                            records.append({
                                'industry_name': 'All Industries',
                                'kpi_name': kpi_name,
                                'benchmark_type': 'industry_average',
                                'benchmark_value': str(clamp_decimal_to_numeric_10_4(weak_v) or ''),
                                'benchmark_unit': 'ratio',
                                'data_source': 'Industry Standards',
                                'data_year': current_year,
                                'sample_size': 100,
                                'confidence_level': '0.9500',
                                'is_active': True,
                            })
                    # All > X preferred
                    elif 'All' in p:
                        m3 = re.search(r'([><]+)\s*([0-9.]+)', p)
                        if m3:
                            op = m3.group(1)
                            val = float(m3.group(2))
                            btype = 'minimum' if op == '>' else 'industry_average'
                            unit = determine_unit(kpi_name, val)
                            records.append({
                                'industry_name': 'All Industries',
                                'kpi_name': kpi_name,
                                'benchmark_type': btype,
                                'benchmark_value': str(clamp_decimal_to_numeric_10_4(val) or ''),
                                'benchmark_unit': unit,
                                'data_source': 'Industry Standards',
                                'data_year': current_year,
                                'sample_size': 100,
                                'confidence_level': '0.9500',
                                'is_active': True,
                            })
    return records


# --------------------- Main ---------------------

def main():
    if not INPUT_CSV.exists():
        raise SystemExit(f"CSV not found: {INPUT_CSV}")

    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Build previews
    std_cols = build_standard_columns_preview(rows)
    kpi_defs = build_kpi_definitions_preview(rows)
    benches = parse_benchmarks_to_records(rows)

    # Write CSVs
    if std_cols:
        with open(OUT_STD_COLS, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(std_cols[0].keys()))
            writer.writeheader()
            writer.writerows(std_cols)
    if kpi_defs:
        with open(OUT_KPI_DEFS, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(kpi_defs[0].keys()))
            writer.writeheader()
            writer.writerows(kpi_defs)
    if benches:
        with open(OUT_BENCH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(benches[0].keys()))
            writer.writeheader()
            writer.writerows(benches)

    print('Preview files generated:')
    print(f'- {OUT_STD_COLS.name}')
    print(f'- {OUT_KPI_DEFS.name}')
    print(f'- {OUT_BENCH.name}')


if __name__ == '__main__':
    main()