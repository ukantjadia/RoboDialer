#!/usr/bin/env python3
"""
Import data from preview CSVs into the database.
- Reads:
  - preview_standard_columns.csv -> standard_column_definitions
  - preview_kpi_definitions.csv  -> kpi_definitions
  - preview_industry_benchmarks.csv -> industry_benchmarks

Before importing, this script clears existing rows in these tables, then overwrites with preview data.
The script converts JSON-string fields to native types, clamps numerics to DB precision,
performs idempotent inserts, and uses per-record flush/rollback so failures don't block others.
Note: Upper-bound benchmark types use 'industry_average' (not 'maximum') to match the DB Enum.
"""

import os
import sys
import csv
import json
import logging
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
from models.finance_report_gen.standard_column_definitions_model import StandardColumnDefinitions
from models.finance_report_gen.kpi_definitions_model import KPIDefinitions
from models.finance_report_gen.industry_benchmarks_model import IndustryBenchmarks
from config.config import config as app_config

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('import_from_preview.log', encoding='utf-8'),
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)


def create_minimal_app():
	"""Create a minimal Flask app and bind SQLAlchemy using project config."""
	app = Flask(__name__)
	app.config.from_object(app_config)
	db.init_app(app)
	# Import models to ensure mapper relationships are registered (User -> UserSubscription, etc.)
	with app.app_context():
		try:
			from models.user_model import User  # noqa: F401
			from models.user_subscription_model import UserSubscription  # noqa: F401
			from models.plan_model import Plan  # noqa: F401
		except Exception:
			# Not critical for these inserts if not present
			pass
	return app


# --------------------- Helpers ---------------------

def parse_json_field(value):
	"""Parse a JSON-encoded string field. Returns Python object or None."""
	if value in (None, ''):
		return None
	try:
		return json.loads(value)
	except Exception:
		return None


def parse_bool(value):
	"""Parse a truthy string to bool; pass through bools; default False for unknown."""
	if isinstance(value, bool):
		return value
	if value is None:
		return False
	v = str(value).strip().lower()
	return v in ['true', '1', 'yes', 'y']


def parse_int(value):
	if value in (None, ''):
		return None
	try:
		return int(str(value).strip())
	except Exception:
		return None


def clamp_decimal_str_to_numeric_10_4(value_str):
	"""Clamp string numeric to Decimal within [-999999.9999, 999999.9999]. Returns Decimal or None."""
	if value_str in (None, ''):
		return None
	try:
		val = Decimal(str(value_str))
		max_abs = Decimal('999999.9999')
		if val > max_abs:
			val = max_abs
		if val < -max_abs:
			val = -max_abs
		return val.quantize(Decimal('0.0001'))
	except (InvalidOperation, ValueError, TypeError):
		return None


def clamp_confidence_to_numeric_3_2(value_str):
	"""Convert confidence string (e.g., '0.9500') to Decimal('0.95') within [0, 1] and 2 d.p."""
	if value_str in (None, ''):
		return None
	try:
		val = Decimal(str(value_str))
		if val < Decimal('0'):
			val = Decimal('0')
		if val > Decimal('1'):
			val = Decimal('1')
		return val.quantize(Decimal('0.01'))
	except (InvalidOperation, ValueError, TypeError):
		return None


def clear_table(model, label: str) -> bool:
	"""Delete all rows from a table safely and commit."""
	try:
		deleted = db.session.query(model).delete(synchronize_session=False)
		db.session.commit()
		logger.info(f"Cleared {deleted} rows from {label}")
		return True
	except Exception as e:
		db.session.rollback()
		logger.error(f"Failed clearing {label}: {e}")
		return False


# --------------------- Importers ---------------------

def import_standard_columns(preview_path: Path) -> bool:
	"""Import standard column definitions from preview_standard_columns.csv"""
	if not preview_path.exists():
		logger.error(f"Preview CSV not found: {preview_path}")
		return False

	success_count = 0
	error_count = 0
	errors = []

	with open(preview_path, 'r', encoding='utf-8') as f:
		reader = csv.DictReader(f)
		for row in reader:
			try:
				column_name = (row.get('column_name') or '').strip()
				if not column_name:
					continue

				std = StandardColumnDefinitions(
					column_name=column_name,
					column_category=(row.get('column_category') or '').strip() or None,
					column_subcategory=(row.get('column_subcategory') or '').strip() or None,
					applicable_file_types=parse_json_field(row.get('applicable_file_types')),
					is_required=parse_bool(row.get('is_required')),
					priority_score=parse_int(row.get('priority_score')),
					description=(row.get('description') or '').strip() or None,
					synonyms=parse_json_field(row.get('synonyms')),
					pattern_matches=parse_json_field(row.get('pattern_matches')),
					expected_data_type=((row.get('expected_data_type') or '').strip() or None),
					validation_rules=parse_json_field(row.get('validation_rules')),
					is_active=parse_bool(row.get('is_active')) if 'is_active' in row else True,
				)

				db.session.add(std)
				db.session.flush()
				success_count += 1
				logger.info(f"Inserted standard column: {column_name}")

			except Exception as e:
				db.session.rollback()
				error_count += 1
				msg = f"Error inserting standard column '{row.get('column_name', '')}': {e}"
				errors.append(msg)
				logger.error(msg)
				continue

	try:
		db.session.commit()
		logger.info(f"Committed {success_count} standard columns (errors: {error_count})")
	except Exception as e:
		logger.error(f"Commit failed for standard columns: {e}")
		db.session.rollback()
		return False

	if errors:
		logger.error("Standard columns errors:")
		for e in errors:
			logger.error(f"  - {e}")
	return True


def import_kpi_definitions(preview_path: Path) -> bool:
	"""Import KPI definitions from preview_kpi_definitions.csv"""
	if not preview_path.exists():
		logger.error(f"Preview CSV not found: {preview_path}")
		return False

	success_count = 0
	error_count = 0
	errors = []

	with open(preview_path, 'r', encoding='utf-8') as f:
		reader = csv.DictReader(f)
		for row in reader:
			try:
				kpi_name = (row.get('kpi_name') or '').strip()
				if not kpi_name:
					continue

				required_columns = parse_json_field(row.get('required_columns')) or []
				optional_columns = parse_json_field(row.get('optional_columns')) or []
				dependencies = parse_json_field(row.get('dependencies')) or []
				industry_benchmarks = parse_json_field(row.get('industry_benchmarks')) or []

				kpi = KPIDefinitions(
					kpi_name=kpi_name,
					kpi_category=(row.get('kpi_category') or '').strip() or 'Financial Metrics',
					kpi_subcategory=(row.get('kpi_subcategory') or '').strip() or 'General',
					formula=(row.get('formula') or '').strip() or None,
					formula_type=(row.get('formula_type') or '').strip() or None,
					required_columns=required_columns,
					optional_columns=optional_columns,
					dependencies=dependencies,
					dependency_level=parse_int(row.get('dependency_level')),
					industry_benchmarks=industry_benchmarks,
					description=(row.get('description') or '').strip() or None,
					calculation_notes=(row.get('calculation_notes') or '').strip() or None,
					expected_range_min=clamp_decimal_str_to_numeric_10_4(row.get('expected_range_min')),
					expected_range_max=clamp_decimal_str_to_numeric_10_4(row.get('expected_range_max')),
					is_active=parse_bool(row.get('is_active')),
					priority_order=parse_int(row.get('priority_order')),
				)

				db.session.add(kpi)
				db.session.flush()
				success_count += 1
				logger.info(f"Inserted KPI: {kpi_name}")

			except Exception as e:
				db.session.rollback()
				error_count += 1
				msg = f"Error inserting KPI '{row.get('kpi_name', '')}': {e}"
				errors.append(msg)
				logger.error(msg)
				continue

	try:
		db.session.commit()
		logger.info(f"Committed {success_count} KPIs (errors: {error_count})")
	except Exception as e:
		logger.error(f"Commit failed for KPIs: {e}")
		db.session.rollback()
		return False

	if errors:
		logger.error("KPI errors:")
		for e in errors:
			logger.error(f"  - {e}")
	return True


def import_industry_benchmarks(preview_path: Path) -> bool:
	"""Import industry benchmarks from preview_industry_benchmarks.csv"""
	if not preview_path.exists():
		logger.error(f"Preview CSV not found: {preview_path}")
		return False

	success_count = 0
	error_count = 0
	errors = []

	with open(preview_path, 'r', encoding='utf-8') as f:
		reader = csv.DictReader(f)
		for row in reader:
			try:
				industry_name = (row.get('industry_name') or '').strip()
				kpi_name = (row.get('kpi_name') or '').strip()
				benchmark_type = (row.get('benchmark_type') or '').strip()
				if not (industry_name and kpi_name and benchmark_type):
					continue

				conf = clamp_confidence_to_numeric_3_2(row.get('confidence_level'))
				bm_value = clamp_decimal_str_to_numeric_10_4(row.get('benchmark_value'))

				bm = IndustryBenchmarks(
					industry_name=industry_name,
					kpi_name=kpi_name,
					benchmark_type=benchmark_type,
					benchmark_value=bm_value,
					benchmark_unit=(row.get('benchmark_unit') or '').strip() or None,
					data_source=(row.get('data_source') or '').strip() or None,
					data_year=parse_int(row.get('data_year')),
					sample_size=parse_int(row.get('sample_size')),
					confidence_level=conf,
					is_active=parse_bool(row.get('is_active')),
				)

				db.session.add(bm)
				db.session.flush()
				success_count += 1
				logger.info(f"Inserted benchmark: {industry_name} / {kpi_name} / {benchmark_type}")

			except Exception as e:
				db.session.rollback()
				error_count += 1
				msg = f"Error inserting benchmark '{row.get('industry_name','')}/{row.get('kpi_name','')}/{row.get('benchmark_type','')}': {e}"
				errors.append(msg)
				logger.error(msg)
				continue

	try:
		db.session.commit()
		logger.info(f"Committed {success_count} benchmarks (errors: {error_count})")
	except Exception as e:
		logger.error(f"Commit failed for benchmarks: {e}")
		db.session.rollback()
		return False

	if errors:
		logger.error("Benchmark errors:")
		for e in errors:
			logger.error(f"  - {e}")
	return True


# --------------------- Main ---------------------

def main():
	logger.info("Starting import from preview CSVs...")
	base = Path(__file__).parent
	std_csv = base / 'preview_standard_columns.csv'
	kpi_csv = base / 'preview_kpi_definitions.csv'
	bm_csv = base / 'preview_industry_benchmarks.csv'

	app = create_minimal_app()
	with app.app_context():
		# Clear existing data first (benchmarks -> KPIs -> standard columns) to avoid any FK issues
		ok_clear_bm = clear_table(IndustryBenchmarks, 'industry_benchmarks')
		ok_clear_kpi = clear_table(KPIDefinitions, 'kpi_definitions')
		ok_clear_std = clear_table(StandardColumnDefinitions, 'standard_column_definitions')
		if not (ok_clear_bm and ok_clear_kpi and ok_clear_std):
			logger.error("Aborting import because clearing tables failed.")
			return False

		ok_std = import_standard_columns(std_csv)
		ok_kpi = import_kpi_definitions(kpi_csv)
		ok_bm = import_industry_benchmarks(bm_csv)

		all_ok = ok_std and ok_kpi and ok_bm
		if all_ok:
			logger.info("Preview import completed successfully for all tables.")
		else:
			logger.warning("Preview import completed with some failures. Check logs.")
		return all_ok


if __name__ == '__main__':
	success = main()
	sys.exit(0 if success else 1)