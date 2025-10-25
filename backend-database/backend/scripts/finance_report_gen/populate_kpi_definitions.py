#!/usr/bin/env python3
"""
Script to populate the kpi_definitions table with financial KPI definitions.
This script reads from the KPI CSV file and creates KPI definition records.
"""

import os
import sys
import csv
import logging
import re
from datetime import datetime
from pathlib import Path
from decimal import Decimal, InvalidOperation

# Ensure console uses UTF-8 on Windows to avoid UnicodeEncodeError
try:
	sys.stdout.reconfigure(encoding='utf-8')
	sys.stderr.reconfigure(encoding='utf-8')
except Exception:
	pass

# Add the parent directory to the Python path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask
from models.lead_model import db
from models.finance_report_gen.kpi_definitions_model import KPIDefinitions
from config.config import config as app_config

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('kpi_definitions_population.log', encoding='utf-8'),
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)

def create_minimal_app():
	"""Create a minimal Flask app and bind SQLAlchemy using project config."""
	app = Flask(__name__)
	app.config.from_object(app_config)
	db.init_app(app)
	# Import models to ensure mapper relationships are registered
	with app.app_context():
		from models.user_model import User  # noqa: F401
		from models.user_subscription_model import UserSubscription  # noqa: F401
		from models.plan_model import Plan  # noqa: F401
	return app

def parse_industry_thresholds(thresholds_str):
	"""
	Parse industry thresholds string and extract benchmark values.
	Returns a list of dictionaries with industry and threshold info.
	"""
	if not thresholds_str or thresholds_str.strip() == '':
		return []

	thresholds = []

	# Split by comma and process each threshold
	parts = thresholds_str.split(',')
	for part in parts:
		part = part.strip()
		if not part:
			continue

		# Extract industry and value
		# Pattern: "Industry > value" or "Industry < value" or "Industry: value"
		match = re.match(r'([A-Za-z\s&]+)\s*([><:]+)\s*([0-9.]+)\s*%?', part)
		if match:
			industry = match.group(1).strip()
			operator = match.group(2).strip()
			value = float(match.group(3))

			# Determine benchmark type based on operator
			if operator in ['>', '>=']:
				benchmark_type = 'minimum'
			elif operator in ['<', '<=']:
				benchmark_type = 'maximum'
			else:
				benchmark_type = 'target'

			thresholds.append({
				'industry': industry,
				'benchmark_type': benchmark_type,
				'value': value,
				'operator': operator
			})
		else:
			# Handle special cases like "All > 1 preferred"
			if 'All' in part:
				match = re.search(r'([><]+)\s*([0-9.]+)', part)
				if match:
					operator = match.group(1)
					value = float(match.group(2))
					benchmark_type = 'minimum' if operator == '>' else 'maximum'
					thresholds.append({
						'industry': 'All Industries',
						'benchmark_type': benchmark_type,
						'value': value,
						'operator': operator
					})

	return thresholds

def extract_required_columns(column_names_str):
    """
    Extract required columns from the column names string.
    Returns a list of column names.
    """
    if not column_names_str:
        return []

    # Split by comma and clean up
    columns = [col.strip() for col in column_names_str.split(',')]
    return [col for col in columns if col]

def determine_formula_type(formula, formula_type_str):
    """
    Determine the formula type based on the formula string and explicit type.
    """
    if formula_type_str and formula_type_str.strip():
        return formula_type_str.strip()

    # Analyze formula to determine type
    formula_lower = formula.lower()

    if any(op in formula_lower for op in ['+', '-', '*', '/', '(', ')']):
        if any(complex_term in formula_lower for complex_term in ['average', 'dsi', 'dso', 'dpo', 'nopat', 'wacc']):
            return 'custom_logic'
        else:
            return 'complex_formula'
    else:
        return 'simple_ratio'

def get_dependencies(required_columns, formula):
    """
    Determine dependencies based on required columns and formula complexity.
    """
    dependencies = []

    # Add basic dependencies based on required columns
    for col in required_columns:
        if 'average' in col.lower():
            dependencies.append({
                'type': 'period_comparison',
                'description': f'Requires {col} from two periods for average calculation'
            })

    # Add formula-specific dependencies
    if 'dsi' in formula.lower() or 'dio' in formula.lower():
        dependencies.append({
            'type': 'inventory_metrics',
            'description': 'Requires inventory and COGS data from two periods'
        })

    if 'dso' in formula.lower():
        dependencies.append({
            'type': 'receivables_metrics',
            'description': 'Requires accounts receivable and revenue data from two periods'
        })

    if 'dpo' in formula.lower():
        dependencies.append({
            'type': 'payables_metrics',
            'description': 'Requires accounts payable and COGS data from two periods'
        })

    return dependencies

def calculate_dependency_level(dependencies):
    """
    Calculate dependency level based on number and complexity of dependencies.
    """
    if not dependencies:
        return 1

    # Count complex dependencies
    complex_deps = sum(1 for dep in dependencies if dep['type'] in ['period_comparison', 'custom_logic'])

    if complex_deps > 2:
        return 3  # High dependency
    elif complex_deps > 0:
        return 2  # Medium dependency
    else:
        return 1  # Low dependency

def clamp_decimal_str_to_numeric_10_4(value_str):
	"""Clamp string numeric to Decimal within [-999999.9999, 999999.9999]. Returns Decimal or None."""
	if not value_str:
		return None
	try:
		val = Decimal(value_str)
		max_abs = Decimal('999999.9999')
		if val > max_abs:
			return max_abs
		if val < -max_abs:
			return -max_abs
		# Round to 4 decimal places
		return val.quantize(Decimal('0.0001'))
	except (InvalidOperation, ValueError, TypeError):
		return None

def create_kpi_definitions(csv_data):
    """
    Create KPI definition records from CSV data.
    """
    kpi_definitions = []

    for row in csv_data:
        try:
            # Extract basic information
            kpi_name = row.get('KPI Name', '').strip()
            description = row.get('Description', '').strip()
            formula = row.get('Formula', '').strip()
            files_used = row.get('Files Used', '').strip()
            column_names = row.get('Column Name(s)', '').strip()
            category = row.get('Category', '').strip()
            industry_thresholds = row.get('Industry Thresholds', '').strip()
            formula_type_str = row.get('Formula Type', '').strip()
            priority_order = row.get('Priority Order', '').strip()
            expected_range_min = row.get('Expected Range Min', '').strip()
            expected_range_max = row.get('Expected Range Max', '').strip()

            if not kpi_name:
                logger.warning(f"Skipping row with no KPI name: {row}")
                continue

            # Parse industry thresholds
            parsed_thresholds = parse_industry_thresholds(industry_thresholds)

            # Extract required columns
            required_columns = extract_required_columns(column_names)

            # Determine formula type
            formula_type = determine_formula_type(formula, formula_type_str)

            # Get dependencies
            dependencies = get_dependencies(required_columns, formula)

            # Calculate dependency level
            dependency_level = calculate_dependency_level(dependencies)

            # Parse numeric values
            try:
                priority_order_int = int(priority_order) if priority_order else None
            except (ValueError, TypeError):
                priority_order_int = None

            # Clamp to Numeric(10,4) allowable range
            expected_range_min_decimal = clamp_decimal_str_to_numeric_10_4(expected_range_min)
            expected_range_max_decimal = clamp_decimal_str_to_numeric_10_4(expected_range_max)

            # Create KPI definition
            kpi_def = {
                'kpi_name': kpi_name,
                'kpi_category': category or 'Financial Metrics',
                'kpi_subcategory': category or 'General',
                'formula': formula,
                'formula_type': formula_type,
                'required_columns': required_columns,
                'optional_columns': [],  # Could be enhanced based on business logic
                'dependencies': dependencies,
                'dependency_level': dependency_level,
                'industry_benchmarks': parsed_thresholds,
                'description': description,
                'calculation_notes': f'Formula: {formula}. Files: {files_used}',
                'expected_range_min': expected_range_min_decimal,
                'expected_range_max': expected_range_max_decimal,
                'is_active': True,
                'priority_order': priority_order_int
            }

            kpi_definitions.append(kpi_def)

        except Exception as e:
            logger.error(f"Error processing KPI '{row.get('KPI Name', 'Unknown')}': {e}")
            continue

    return kpi_definitions

def populate_database(kpi_definitions):
    """
    Insert the KPI definitions into the database.
    """
    success_count = 0
    error_count = 0
    errors = []

    try:
        for kpi_def in kpi_definitions:
            try:
                # Check if KPI already exists
                existing = KPIDefinitions.query.filter_by(
                    kpi_name=kpi_def['kpi_name']
                ).first()

                if existing:
                    logger.warning(f"KPI '{kpi_def['kpi_name']}' already exists, skipping...")
                    continue

                # Create new KPI definition
                new_kpi = KPIDefinitions(**kpi_def)
                db.session.add(new_kpi)
                # Flush per-record to catch errors early
                db.session.flush()
                success_count += 1

                logger.info(f"Added KPI definition: {kpi_def['kpi_name']}")

            except Exception as e:
                error_count += 1
                db.session.rollback()  # reset session for next record
                error_msg = f"Error adding KPI '{kpi_def.get('kpi_name', 'Unknown')}': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue

        # Commit all successful changes
        db.session.commit()
        logger.info(f"Successfully committed {success_count} KPI definitions to database")

    except Exception as e:
        logger.error(f"Database error: {e}")
        db.session.rollback()
        return False

    # Log summary
    logger.info(f"Population completed: {success_count} successful, {error_count} errors")

    # Log all errors
    if errors:
        logger.error("Errors encountered:")
        for error in errors:
            logger.error(f"  - {error}")

    return True

def main():
	"""
	Main function to run the KPI definitions population script.
	"""
	logger.info("Starting KPI definitions population...")

	# Get the CSV file path
	script_dir = Path(__file__).parent
	csv_file_path = script_dir / 'kpi_data_structured.csv'

	if not csv_file_path.exists():
		logger.error(f"CSV file not found: {csv_file_path}")
		return False

	# Ensure app context for DB operations
	app = create_minimal_app()
	with app.app_context():
		try:
			# Read CSV data
			csv_data = []
			with open(csv_file_path, 'r', encoding='utf-8') as file:
				csv_reader = csv.DictReader(file)
				csv_data = list(csv_reader)

			if not csv_data:
				logger.error("No data found in CSV file")
				return False

			logger.info(f"Read {len(csv_data)} rows from CSV file")

			# Create KPI definitions
			kpi_definitions = create_kpi_definitions(csv_data)

			logger.info(f"Created {len(kpi_definitions)} KPI definitions")

			# Populate database
			success = populate_database(kpi_definitions)

			if success:
				logger.info("KPI definitions population completed successfully!")
			else:
				logger.error("KPI definitions population failed!")

			return success

		except Exception as e:
			logger.error(f"Unexpected error: {e}")
			return False

if __name__ == "__main__":
	success = main()
	sys.exit(0 if success else 1)