#!/usr/bin/env python3
"""
Master script to populate all financial database tables.
This script runs the three population scripts in the correct order:
1. Standard Column Definitions
2. KPI Definitions
3. Industry Benchmarks

The order is important as KPI definitions may reference standard columns.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('master_population.log', encoding='utf-8'),
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)

def run_script(script_name, description):
	"""
	Run a Python script and return success status.
	"""
	logger.info(f"Starting {description}...")

	try:
		# Run the script
		result = subprocess.run(
			[sys.executable, script_name],
			capture_output=True,
			text=True,
			cwd=Path(__file__).parent
		)

		if result.returncode == 0:
			logger.info(f"{description} completed successfully.")
			if result.stdout:
				logger.info(f"Output: {result.stdout}")
			return True
		else:
			logger.error(f"{description} failed with return code {result.returncode}")
			if result.stderr:
				logger.error(f"Error: {result.stderr}")
			if result.stdout:
				logger.info(f"Output: {result.stdout}")
			return False

	except Exception as e:
		logger.error(f"Error running {description}: {e}")
		return False

def check_csv_file():
	"""
	Check if the required CSV file exists.
	"""
	script_dir = Path(__file__).parent
	csv_file_path = script_dir / 'kpi_data_structured.csv'

	if not csv_file_path.exists():
		logger.error(f"Required CSV file not found: {csv_file_path}")
		logger.error("Please ensure 'kpi_data_structured.csv' exists in the scripts directory.")
		return False

	logger.info(f"Found CSV file: {csv_file_path}")
	return True

def main():
	"""
	Main function to run all population scripts.
	"""
	start_time = datetime.now()
	logger.info("Starting master population script...")
	logger.info(f"Working directory: {Path(__file__).parent}")

	# Check if CSV file exists
	if not check_csv_file():
		return False

	# Define scripts to run in order
	scripts = [
		{
			'name': 'populate_standard_columns.py',
			'description': 'Standard Column Definitions Population'
		},
		{
			'name': 'populate_kpi_definitions.py',
			'description': 'KPI Definitions Population'
		},
		{
			'name': 'populate_industry_benchmarks.py',
			'description': 'Industry Benchmarks Population'
		}
	]

	success_count = 0
	total_scripts = len(scripts)

	# Run each script in order
	for script in scripts:
		script_path = Path(__file__).parent / script['name']

		if not script_path.exists():
			logger.error(f"Script not found: {script_path}")
			continue

		logger.info(f"Running {script['name']}...")

		if run_script(script['name'], script['description']):
			success_count += 1
		else:
			logger.warning(f"{script['description']} failed, but continuing with remaining scripts...")

	# Summary
	end_time = datetime.now()
	duration = end_time - start_time

	logger.info("=" * 60)
	logger.info("POPULATION SUMMARY")
	logger.info("=" * 60)
	logger.info(f"Successful: {success_count}/{total_scripts}")
	logger.info(f"Failed: {total_scripts - success_count}/{total_scripts}")
	logger.info(f"Total Duration: {duration}")

	if success_count == total_scripts:
		logger.info("All tables populated successfully.")
		return True
	elif success_count > 0:
		logger.warning("Some tables were populated successfully, but some failed.")
		return False
	else:
		logger.error("All population scripts failed.")
		return False

if __name__ == "__main__":
	success = main()
	sys.exit(0 if success else 1)