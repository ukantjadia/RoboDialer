#!/usr/bin/env python3
"""
Script to populate the standard_column_definitions table with financial column definitions.
This script reads from the KPI CSV file and extracts unique column names to create standard definitions.
"""

import os
import sys
import csv
import logging
from datetime import datetime
from pathlib import Path

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
from models.finance_report_gen.standard_column_definitions_model import StandardColumnDefinitions
from config.config import config as app_config

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('standard_columns_population.log', encoding='utf-8'),
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)


def create_minimal_app():
	"""Create a minimal Flask app and bind SQLAlchemy using project config."""
	app = Flask(__name__)
	app.config.from_object(app_config)
	db.init_app(app)
	# Import models to ensure mapper relationships are registered (e.g., User -> UserSubscription)
	with app.app_context():
		from models.user_model import User  # noqa: F401
		from models.user_subscription_model import UserSubscription  # noqa: F401
		from models.plan_model import Plan  # noqa: F401
	return app

def extract_unique_columns_from_csv(csv_file_path):
    """
    Extract unique column names from the KPI CSV file.
    Returns a set of unique column names.
    """
    unique_columns = set()

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)

            for row in csv_reader:
                # Extract column names from the "Column Name(s)" field
                column_names = row.get('Column Name(s)', '')
                if column_names:
                    # Split by comma and clean up each column name
                    columns = [col.strip() for col in column_names.split(',')]
                    for col in columns:
                        if col:  # Skip empty strings
                            unique_columns.add(col)

        logger.info(f"Extracted {len(unique_columns)} unique column names from CSV")
        return unique_columns

    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return set()

def get_file_type_mapping():
    """
    Define mapping between file types mentioned in CSV and applicable file types.
    """
    return {
        'Income Statement': ['income_statement', 'financial_statement'],
        'Balance Sheet': ['balance_sheet', 'financial_statement'],
        'Cash Flow': ['cash_flow', 'financial_statement'],
        'Cash Flow Statement': ['cash_flow', 'financial_statement'],
        'External Input': ['external_data', 'market_data'],
        'Stock Data': ['external_data', 'market_data'],
        'Budget vs Actuals': ['budget', 'actuals'],
        'Budget Process Records': ['budget', 'process'],
        'Budget Documentation': ['budget', 'documentation'],
        'AP Records': ['accounts_payable', 'procurement'],
        'Cost Accounting': ['cost_accounting', 'management_accounting'],
        'HR Records': ['human_resources', 'payroll'],
        'AR Aging': ['accounts_receivable', 'aging'],
        'Debt schedules': ['debt', 'schedules'],
        'Shareholder reports': ['shareholder', 'reports'],
        'Marketing/Income': ['marketing', 'income'],
        'Debt schedules': ['debt', 'schedules']
    }

def get_column_category_mapping():
    """
    Define mapping between column names and their categories.
    """
    return {
        # Revenue related
        'Total Revenue': 'Revenue',
        'Revenue': 'Revenue',
        'Net Sales': 'Revenue',
        'Revenue This Year': 'Revenue',
        'Revenue Last Year': 'Revenue',
        'Net Credit Sales': 'Revenue',

        # Income related
        'Net Income': 'Income',
        'Net Income TY': 'Income',
        'Net Income LY': 'Income',
        'Operating Income': 'Income',
        'EBIT': 'Income',
        'Pretax Income': 'Income',
        'Gross Profit': 'Income',

        # Asset related
        'Total Assets': 'Assets',
        'Current Assets': 'Assets',
        'Total Current Assets': 'Assets',
        'Net PPE': 'Assets',
        'Intangibles': 'Assets',
        'Goodwill': 'Assets',
        'Cash': 'Assets',
        'Cash and Cash Equivalents': 'Assets',
        'Accounts Receivable': 'Assets',
        'Inventory': 'Assets',
        'Marketable Securities': 'Assets',

        # Liability related
        'Total Liabilities': 'Liabilities',
        'Current Liabilities': 'Liabilities',
        'Total Current Liabilities': 'Liabilities',
        'Accounts Payable': 'Liabilities',
        'Long-Term Debt': 'Liabilities',
        'Total Debt': 'Liabilities',
        'Interest Expense': 'Liabilities',

        # Equity related
        'Shareholder Equity': 'Equity',
        'Total Equity': 'Equity',
        'Retained Earnings': 'Equity',
        'Number of Shares': 'Equity',
        'Total Shares': 'Equity',
        'Diluted Average Shares': 'Equity',
        'Weighted Average Shares Outstanding': 'Equity',

        # Cost related
        'Cost of Revenue': 'Costs',
        'COGS': 'Costs',
        'Total Variable Costs': 'Costs',
        'Operating Expense': 'Costs',
        'Operating Expenses': 'Costs',
        'SG&A': 'Costs',
        'SG&A Expenses': 'Costs',
        'R&D Expense': 'Costs',
        'Depreciation & Amortization': 'Costs',
        'D&A': 'Costs',
        'Tax Provision': 'Costs',
        'Overhead Costs': 'Costs',

        # Cash flow related
        'Operating Cash Flow': 'Cash Flow',
        'Operating CF': 'Cash Flow',
        'Capex': 'Cash Flow',
        'Capital Expenditures': 'Cash Flow',
        'Dividends': 'Cash Flow',
        'Dividends per Share': 'Cash Flow',
        'Annual Dividend per Share': 'Cash Flow',
        'Net Debt Issued': 'Cash Flow',
        'Debt Repayments': 'Cash Flow',

        # Market data
        'Share Price': 'Market Data',
        'Market Price per Share': 'Market Data',
        'Market Cap': 'Market Data',
        'EPS': 'Market Data',

        # Other
        'Working Capital': 'Working Capital',
        'WC': 'Working Capital',
        'Change in Working Capital': 'Working Capital',
        'Daily Operating Expenses': 'Operating Metrics',
        'Monthly Operating Expenses': 'Operating Metrics',
        'Total AP Processing Costs': 'Operating Metrics',
        'Number of Invoices': 'Operating Metrics',
        'Number of Invoices Processed': 'Operating Metrics',
        'Total Employees': 'Operating Metrics',
        'HR Staff Count': 'Operating Metrics',
        'Budget Start Date': 'Budget',
        'Budget Completion Date': 'Budget',
        'Budgeted Amount': 'Budget',
        'Actual Results': 'Budget',
        'Total Acquisition Cost': 'Marketing',
        'New Customers': 'Marketing',
        'Past Due AR': 'Accounts Receivable',
        'Total AR': 'Accounts Receivable',
        'Purchases': 'Procurement',
        'WACC': 'Financial Metrics',
        'NOPAT': 'Financial Metrics',
        'Invested Capital': 'Financial Metrics',
        'MVE': 'Financial Metrics',
        'Sales': 'Revenue',
        'Preferred Dividends': 'Dividends'
    }

def get_column_subcategory_mapping():
    """
    Define mapping between column names and their subcategories.
    """
    return {
        # Revenue subcategories
        'Total Revenue': 'Total Revenue',
        'Revenue': 'Total Revenue',
        'Net Sales': 'Net Sales',
        'Net Credit Sales': 'Credit Sales',

        # Income subcategories
        'Net Income': 'Net Income',
        'Operating Income': 'Operating Income',
        'EBIT': 'Operating Income',
        'Gross Profit': 'Gross Profit',

        # Asset subcategories
        'Total Assets': 'Total Assets',
        'Current Assets': 'Current Assets',
        'Cash': 'Cash & Equivalents',
        'Inventory': 'Inventory',
        'Accounts Receivable': 'Accounts Receivable',
        'Net PPE': 'Property Plant Equipment',

        # Liability subcategories
        'Current Liabilities': 'Current Liabilities',
        'Accounts Payable': 'Accounts Payable',
        'Long-Term Debt': 'Long Term Debt',
        'Interest Expense': 'Interest Expense',

        # Equity subcategories
        'Shareholder Equity': 'Shareholder Equity',
        'Number of Shares': 'Share Count',
        'Retained Earnings': 'Retained Earnings'
    }

def get_expected_data_type(column_name):
    """
    Determine the expected data type for a column based on its name.
    """
    if any(keyword in column_name.lower() for keyword in ['revenue', 'income', 'assets', 'liabilities', 'equity', 'cost', 'expense', 'cash', 'debt']):
        return 'currency'
    elif any(keyword in column_name.lower() for keyword in ['ratio', 'margin', 'percentage', 'rate']):
        return 'percentage'
    elif any(keyword in column_name.lower() for keyword in ['count', 'number', 'shares', 'employees']):
        return 'integer'
    elif any(keyword in column_name.lower() for keyword in ['days', 'months', 'years']):
        return 'integer'
    else:
        return 'decimal'

def create_standard_column_definitions(unique_columns):
    """
    Create standard column definition records for each unique column.
    """
    file_type_mapping = get_file_type_mapping()
    category_mapping = get_column_category_mapping()
    subcategory_mapping = get_column_subcategory_mapping()

    column_definitions = []

    for column_name in unique_columns:
        # Determine file types this column applies to
        applicable_file_types = []
        for file_type, mapped_types in file_type_mapping.items():
            if file_type in column_name or any(mapped in column_name for mapped in mapped_types):
                applicable_file_types.extend(mapped_types)

        # Remove duplicates and set default if none found
        applicable_file_types = list(set(applicable_file_types)) if applicable_file_types else ['financial_statement']

        # Get category and subcategory
        category = category_mapping.get(column_name, 'Financial Metrics')
        subcategory = subcategory_mapping.get(column_name, 'General')

        # Determine if required based on importance
        is_required = any(keyword in column_name.lower() for keyword in [
            'revenue', 'income', 'assets', 'equity', 'cash', 'debt'
        ])

        # Set priority score based on importance
        priority_score = 1 if is_required else 2

        # Get expected data type
        expected_data_type = get_expected_data_type(column_name)

        # Create synonyms (common variations of the column name)
        synonyms = []
        if 'revenue' in column_name.lower():
            synonyms = ['Sales', 'Income', 'Turnover']
        elif 'income' in column_name.lower():
            synonyms = ['Profit', 'Earnings', 'Net Income']
        elif 'assets' in column_name.lower():
            synonyms = ['Total Assets', 'Assets']

        # Create pattern matches for data validation
        pattern_matches = []
        if expected_data_type == 'currency':
            pattern_matches = ['^[0-9,]+\.?[0-9]*$', '^[0-9]+$']
        elif expected_data_type == 'percentage':
            pattern_matches = ['^[0-9]+\.?[0-9]*%?$', '^[0-9]+$']
        elif expected_data_type == 'integer':
            pattern_matches = ['^[0-9]+$']

        # Create validation rules
        validation_rules = {
            'min_value': 0 if expected_data_type in ['currency', 'percentage', 'integer'] else None,
            'max_value': None,
            'required': is_required,
            'data_type': expected_data_type
        }

        column_def = {
            'column_name': column_name,
            'column_category': category,
            'column_subcategory': subcategory,
            'applicable_file_types': applicable_file_types,
            'is_required': is_required,
            'priority_score': priority_score,
            'description': f'Standard column for {column_name.lower()} data',
            'synonyms': synonyms,
            'pattern_matches': pattern_matches,
            'expected_data_type': expected_data_type,
            'validation_rules': validation_rules,
            'is_active': True
        }

        column_definitions.append(column_def)

    return column_definitions

def populate_database(column_definitions):
    """
    Insert the column definitions into the database.
    """
    success_count = 0
    error_count = 0
    errors = []

    try:
        for column_def in column_definitions:
            try:
                # Check if column already exists
                existing = StandardColumnDefinitions.query.filter_by(
                    column_name=column_def['column_name']
                ).first()

                if existing:
                    logger.warning(f"Column '{column_def['column_name']}' already exists, skipping...")
                    continue

                # Create new column definition
                new_column = StandardColumnDefinitions(**column_def)
                db.session.add(new_column)
                success_count += 1

                logger.info(f"Added column definition: {column_def['column_name']}")

            except Exception as e:
                error_count += 1
                error_msg = f"Error adding column '{column_def['column_name']}': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue

        # Commit all changes
        db.session.commit()
        logger.info(f"Successfully committed {success_count} column definitions to database")

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
	Main function to run the column population script.
	"""
	logger.info("Starting standard column definitions population...")

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
			# Extract unique columns from CSV
			unique_columns = extract_unique_columns_from_csv(csv_file_path)

			if not unique_columns:
				logger.error("No unique columns found in CSV file")
				return False

			# Create column definitions
			column_definitions = create_standard_column_definitions(unique_columns)

			logger.info(f"Created {len(column_definitions)} column definitions")

			# Populate database
			success = populate_database(column_definitions)

			if success:
				logger.info("Standard column definitions population completed successfully!")
			else:
				logger.error("Standard column definitions population failed!")

			return success

		except Exception as e:
			logger.error(f"Unexpected error: {e}")
			return False

if __name__ == "__main__":
	success = main()
	sys.exit(0 if success else 1)