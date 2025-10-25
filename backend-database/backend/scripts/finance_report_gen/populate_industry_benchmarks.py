#!/usr/bin/env python3
"""
Script to populate the industry_benchmarks table with financial industry benchmarks.
This script reads from the KPI CSV file and extracts industry threshold data to create benchmark records.
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
from models.finance_report_gen.industry_benchmarks_model import IndustryBenchmarks
from config.config import config as app_config

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('industry_benchmarks_population.log', encoding='utf-8'),
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

# --- Helpers ---

def get_field(row: dict, candidates: list[str]) -> str:
	"""Return the first non-empty value for any of the candidate column names (case-insensitive)."""
	if not row:
		return ''
	lower_map = {str(k).strip().lower(): k for k in row.keys()}
	for cand in candidates:
		key_lower = str(cand).strip().lower()
		orig_key = lower_map.get(key_lower)
		if orig_key is not None:
			val = row.get(orig_key)
			if val is not None and str(val).strip() != '':
				return str(val)
	return ''

def normalize_benchmark_type(bt: str) -> str | None:
	"""Normalize incoming benchmark_type to match DB enum.
	Allowed: minimum, target, excellent, industry_average
	Maps common synonyms: maximum -> industry_average; avg/average -> industry_average.
	"""
	if bt is None:
		return None
	v = str(bt).strip().lower()
	if v in ("minimum", "target", "excellent", "industry_average"):
		return v
	if v in ("maximum", "upper", "upper_bound", "max", "<=", "<"):
		return "industry_average"
	if v in ("average", "avg", "mean", "industry avg", "industry average"):
		return "industry_average"
	return None

def parse_decimal_10_4(value) -> Decimal | None:
	"""Parse to Decimal within Numeric(10,4) bounds; returns None if invalid."""
	if value in (None, ''):
		return None
	try:
		dec = Decimal(str(value))
		max_abs = Decimal('999999.9999')
		if dec > max_abs:
			dec = max_abs
		if dec < -max_abs:
			dec = -max_abs
		return dec.quantize(Decimal('0.0001'))
	except (InvalidOperation, ValueError, TypeError):
		return None

def parse_confidence_3_2(value) -> Decimal | None:
	"""Clamp confidence to [0,1] with 2 d.p., e.g., 0.95."""
	if value in (None, ''):
		return None
	try:
		val = Decimal(str(value))
		if val < Decimal('0'):
			val = Decimal('0')
		if val > Decimal('1'):
			val = Decimal('1')
		return val.quantize(Decimal('0.01'))
	except (InvalidOperation, ValueError, TypeError):
		return None

def parse_industry_thresholds(thresholds_str, kpi_name):
	"""
	Parse industry thresholds string and extract benchmark values.
	Returns a list of dictionaries with industry and threshold info.
	"""
	if not thresholds_str or thresholds_str.strip() == '':
		return []

	benchmarks = []

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
				benchmark_type = 'industry_average'
			else:
				benchmark_type = 'target'

			# Determine unit based on KPI type
			unit = determine_unit(kpi_name, value)

			benchmarks.append({
				'industry_name': industry,
				'kpi_name': kpi_name,
				'benchmark_type': benchmark_type,
				'benchmark_value': clamp_decimal_to_numeric_10_4(value),
				'benchmark_unit': unit,
				'data_source': 'Industry Standards',
				'data_year': datetime.now().year,
				'sample_size': 100,  # Default sample size
				'confidence_level': Decimal('0.95'),  # 95% confidence
				'is_active': True
			})
		else:
			# Handle special cases like "All > 1 preferred"
			if 'All' in part:
				match = re.search(r'([><]+)\s*([0-9.]+)', part)
				if match:
					operator = match.group(1)
					value = float(match.group(2))
					benchmark_type = 'minimum' if operator == '>' else 'industry_average'
					unit = determine_unit(kpi_name, value)

					benchmarks.append({
						'industry_name': 'All Industries',
						'kpi_name': kpi_name,
						'benchmark_type': benchmark_type,
						'benchmark_value': clamp_decimal_to_numeric_10_4(value),
						'benchmark_unit': unit,
						'data_source': 'Industry Standards',
						'data_year': datetime.now().year,
						'sample_size': 100,
						'confidence_level': Decimal('0.95'),
						'is_active': True
					})

			# Handle special cases like ">2.99 Safe, 1.81-2.99 Gray Zone, <1.81 Distress"
			elif 'Safe' in part or 'Gray Zone' in part or 'Distress' in part:
				# Extract numeric values and create multiple benchmarks
				numbers = re.findall(r'([0-9.]+)', part)
				if len(numbers) >= 2:
					# Create safe zone benchmark
					safe_value = float(numbers[0])
					benchmarks.append({
						'industry_name': 'All Industries',
						'kpi_name': kpi_name,
						'benchmark_type': 'minimum',
						'benchmark_value': clamp_decimal_to_numeric_10_4(safe_value),
						'benchmark_unit': 'score',
						'data_source': 'Altman Z-Score Model',
						'data_year': datetime.now().year,
						'sample_size': 100,
						'confidence_level': Decimal('0.95'),
						'is_active': True
					})

					# Create distress zone benchmark
					distress_value = float(numbers[1])
					benchmarks.append({
						'industry_name': 'All Industries',
						'kpi_name': kpi_name,
						'benchmark_type': 'industry_average',
						'benchmark_value': clamp_decimal_to_numeric_10_4(distress_value),
						'benchmark_unit': 'score',
						'data_source': 'Altman Z-Score Model',
						'data_year': datetime.now().year,
						'sample_size': 100,
						'confidence_level': Decimal('0.95'),
						'is_active': True
					})

			# Handle special cases like ">1.25 Strong, 1.0-1.25 Adequate, <1.0 Weak"
			elif 'Strong' in part or 'Adequate' in part or 'Weak' in part:
				numbers = re.findall(r'([0-9.]+)', part)
				if len(numbers) >= 2:
					# Strong benchmark
					strong_value = float(numbers[0])
					benchmarks.append({
						'industry_name': 'All Industries',
						'kpi_name': kpi_name,
						'benchmark_type': 'minimum',
						'benchmark_value': clamp_decimal_to_numeric_10_4(strong_value),
						'benchmark_unit': 'ratio',
						'data_source': 'Industry Standards',
						'data_year': datetime.now().year,
						'sample_size': 100,
						'confidence_level': Decimal('0.95'),
						'is_active': True
					})

					# Weak benchmark
					weak_value = float(numbers[1])
					benchmarks.append({
						'industry_name': 'All Industries',
						'kpi_name': kpi_name,
						'benchmark_type': 'industry_average',
						'benchmark_value': clamp_decimal_to_numeric_10_4(weak_value),
						'benchmark_unit': 'ratio',
						'data_source': 'Industry Standards',
						'data_year': datetime.now().year,
						'sample_size': 100,
						'confidence_level': Decimal('0.95'),
						'is_active': True
					})

			# Handle special cases like "Retail: 15-25%, Tech: 25-40%, Mfg: 10-20%, Services: 20-35%"
			elif ':' in part and '%' in part:
				industry_match = re.match(r'([A-Za-z\s&]+):\s*([0-9.]+)-([0-9.]+)%', part)
				if industry_match:
					industry = industry_match.group(1).strip()
					min_value = float(industry_match.group(2))
					max_value = float(industry_match.group(3))

					# Create minimum benchmark
					benchmarks.append({
						'industry_name': industry,
						'kpi_name': kpi_name,
						'benchmark_type': 'minimum',
						'benchmark_value': clamp_decimal_to_numeric_10_4(min_value),
						'benchmark_unit': 'percentage',
						'data_source': 'Industry Standards',
						'data_year': datetime.now().year,
						'sample_size': 100,
						'confidence_level': Decimal('0.95'),
						'is_active': True
					})

					# Create maximum benchmark
					benchmarks.append({
						'industry_name': industry,
						'kpi_name': kpi_name,
						'benchmark_type': 'industry_average',
						'benchmark_value': clamp_decimal_to_numeric_10_4(max_value),
						'benchmark_unit': 'percentage',
						'data_source': 'Industry Standards',
						'data_year': datetime.now().year,
						'sample_size': 100,
						'confidence_level': Decimal('0.95'),
						'is_active': True
					})

	return benchmarks

def determine_unit(kpi_name, value):
	"""
	Determine the appropriate unit for a benchmark value based on KPI name and value.
	"""
	kpi_lower = kpi_name.lower()

	if any(keyword in kpi_lower for keyword in ['ratio', 'margin', 'percentage', 'rate']):
		return 'percentage'
	elif any(keyword in kpi_lower for keyword in ['days', 'dso', 'dio', 'dpo']):
		return 'days'
	elif any(keyword in kpi_lower for keyword in ['turnover', 'times']):
		return 'times'
	elif any(keyword in kpi_lower for keyword in ['months', 'years']):
		return 'months' if value < 24 else 'years'
	elif any(keyword in kpi_lower for keyword in ['score', 'z-score']):
		return 'score'
	elif any(keyword in kpi_lower for keyword in ['cost', 'dollars']):
		return 'dollars'
	else:
		# Default based on value range
		if value > 1000:
			return 'currency'
		elif value <= 1:
			return 'ratio'
		else:
			return 'units'

def clamp_decimal_to_numeric_10_4(val):
	"""Clamp a float or Decimal to Decimal within [-999999.9999, 999999.9999] with 4 d.p."""
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

def create_industry_benchmarks(csv_data):
	"""
	Create industry benchmark records from CSV data (unstructured thresholds mode).
	"""
	all_benchmarks = []
	missing_kpi = 0
	missing_thresholds = 0

	for row in csv_data:
		try:
			kpi_name = get_field(row, ['KPI Name', 'KPI', 'kpi_name']).strip()
			industry_thresholds = get_field(row, ['Industry Thresholds', 'Industry thresholds', 'Industry Benchmarks', 'industry_thresholds']).strip()

			if not kpi_name:
				missing_kpi += 1
				continue
			if not industry_thresholds:
				missing_thresholds += 1
				continue

			benchmarks = parse_industry_thresholds(industry_thresholds, kpi_name)
			if benchmarks:
				all_benchmarks.extend(benchmarks)
				logger.info(f"Created {len(benchmarks)} benchmarks for KPI: {kpi_name}")

		except Exception as e:
			logger.error(f"Error processing benchmarks for KPI '{row.get('KPI Name', 'Unknown')}': {e}")
			continue

	if missing_kpi or missing_thresholds:
		logger.warning(f"Rows skipped - missing KPI Name: {missing_kpi}, missing Industry Thresholds: {missing_thresholds}")

	return all_benchmarks

def create_benchmarks_from_structured(csv_data):
	"""
	Create industry benchmark records from an already structured CSV with columns like:
	industry_name, kpi_name, benchmark_type, benchmark_value, benchmark_unit,
	data_source, data_year, sample_size, confidence_level, is_active
	"""
	all_benchmarks = []
	for row in csv_data:
		try:
			industry_name = get_field(row, ['industry_name', 'Industry Name']).strip()
			kpi_name = get_field(row, ['kpi_name', 'KPI Name', 'kpi']).strip()
			bt_raw = get_field(row, ['benchmark_type', 'Benchmark Type']).strip()
			bt = normalize_benchmark_type(bt_raw)
			bm_val = parse_decimal_10_4(get_field(row, ['benchmark_value', 'Benchmark Value']).strip())
			bm_unit = get_field(row, ['benchmark_unit', 'Benchmark Unit']).strip() or None
			source = get_field(row, ['data_source', 'Data Source']).strip() or None
			year_str = get_field(row, ['data_year', 'Data Year']).strip()
			year = int(year_str) if year_str.isdigit() else datetime.now().year
			sample_str = get_field(row, ['sample_size', 'Sample Size']).strip()
			sample = int(sample_str) if sample_str.isdigit() else 100
			conf = parse_confidence_3_2(get_field(row, ['confidence_level', 'Confidence Level']).strip()) or Decimal('0.95')
			is_active_str = get_field(row, ['is_active', 'Is Active']).strip().lower()
			is_active = True if is_active_str in ('true', '1', 'yes', 'y') else False

			if not (industry_name and kpi_name and bt):
				continue

			all_benchmarks.append({
				'industry_name': industry_name,
				'kpi_name': kpi_name,
				'benchmark_type': bt,
				'benchmark_value': bm_val,
				'benchmark_unit': bm_unit,
				'data_source': source,
				'data_year': year,
				'sample_size': sample,
				'confidence_level': conf,
				'is_active': is_active if is_active_str != '' else True,
			})
		except Exception as e:
			logger.error(f"Error processing structured row: {e}")
			continue
	return all_benchmarks

def populate_database(benchmarks):
	"""
	Insert the industry benchmarks into the database.
	"""
	success_count = 0
	error_count = 0
	errors = []

	try:
		for benchmark in benchmarks:
			try:
				# Check if benchmark already exists
				existing = IndustryBenchmarks.query.filter_by(
					industry_name=benchmark['industry_name'],
					kpi_name=benchmark['kpi_name'],
					benchmark_type=benchmark['benchmark_type']
				).first()

				if existing:
					logger.warning(f"Benchmark for {benchmark['industry_name']} - {benchmark['kpi_name']} ({benchmark['benchmark_type']}) already exists, skipping...")
					continue

				# Create new benchmark
				new_bm = IndustryBenchmarks(**benchmark)
				db.session.add(new_bm)
				db.session.flush()
				success_count += 1
				logger.info(f"Added benchmark: {benchmark['industry_name']} - {benchmark['kpi_name']} ({benchmark['benchmark_type']})")

			except Exception as e:
				error_count += 1
				db.session.rollback()
				error_msg = f"Error adding benchmark for {benchmark.get('industry_name', 'Unknown')} - {benchmark.get('kpi_name', 'Unknown')}: {str(e)}"
				errors.append(error_msg)
				logger.error(error_msg)
				continue

		# Commit all successful changes
		db.session.commit()
		logger.info(f"Successfully committed {success_count} industry benchmarks to database")

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
	Main function to run the industry benchmarks population script.
	"""
	logger.info("Starting industry benchmarks population...")

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
			with open(csv_file_path, 'r', encoding='utf-8') as file:
				csv_reader = csv.DictReader(file)
				csv_data = list(csv_reader)

			if not csv_data:
				logger.error("No data found in CSV file")
				return False

			# Detect headers
			headers = [str(h).strip().lower() for h in csv_data[0].keys()]
			logger.info(f"CSV headers detected: {headers}")

			benchmarks = []
			if 'industry thresholds' in headers:
				logger.info("Detected unstructured thresholds CSV. Using threshold parser.")
				benchmarks = create_industry_benchmarks(csv_data)
			elif {'industry_name', 'kpi_name', 'benchmark_type', 'benchmark_value'}.issubset(set(headers)):
				logger.info("Detected structured benchmark CSV. Importing directly.")
				benchmarks = create_benchmarks_from_structured(csv_data)
			else:
				logger.error("CSV format not recognized. Expected either 'Industry Thresholds' column or structured columns ('industry_name','kpi_name','benchmark_type','benchmark_value',...).")
				return False

			logger.info(f"Created {len(benchmarks)} industry benchmarks")

			# Populate database
			success = populate_database(benchmarks)

			if success:
				logger.info("Industry benchmarks population completed successfully!")
			else:
				logger.error("Industry benchmarks population failed!")

			return success

		except Exception as e:
			logger.error(f"Unexpected error: {e}")
			return False

if __name__ == "__main__":
	success = main()
	sys.exit(0 if success else 1)