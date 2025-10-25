# CSV Combination API Processor

A resource-controlled Python script that reads CSV data, generates all possible combinations of industry and location pairs, makes streaming API calls, and saves the results back to timestamped CSV files.

## Features

- **Streaming API Support** (GET with query params): `industry`, `location="City, State, Country"`
- **Authentication via Cookies**: Logs in once; reuses cookies; auto re-login on 401/403
- **Incremental Saving**: Appends company rows to partial CSV after each batch
- **Timestamped Outputs**: Each run writes `results_output_YYYYMMDD_HHMMSS.csv`
- **Resource Control**: System resource checks (memory/CPU) with throttling
- **Graceful Shutdown**: Ctrl+C closes stream and preserves progress
- **Duplicate Detection**: Within each call by Company + Industry

## Requirements

- Python 3.7+
- Install via:
```bash
pip install -r requirements_combination_processor.txt
```

## Installation

1. Configure `config_combination_processor.json`:
```json
{
  "api_settings": {
    "url": "https://sandbox-api.saasquatchleads.com/scraper/scrape-stream",
    "timeout": 600
  },
  "auth": {
    "login_url": "https://sandbox-api.saasquatchleads.com/api/auth/login",
    "email": "developer@example.com",
    "password": "****"
  },
  "resource_limits": {
    "max_memory_percent": 70.0,
    "max_cpu_percent": 50.0,
    "max_workers": 1,
    "calls_per_second": 0.1,
    "batch_size": 10
  },
  "csv_settings": {
    "industry_column": "industry",
    "city_column": "city",
    "state_column": "state",
    "country_column": "country"
  }
}
```

2. Ensure your streaming API is reachable and credentials are valid.

## Usage

### Quick Start

```bash
python run_combination_processor.py
# Writes results_output_YYYYMMDD_HHMMSS.csv and incremental results_output_..._partial.csv
```

### Linux/Mac Script
```bash
chmod +x run_combination_processor.sh
./run_combination_processor.sh          # run and show latest outputs afterwards
./run_combination_processor.sh --latest # list newest CSVs
./run_combination_processor.sh --check  # env + API check
./run_combination_processor.sh --test   # streaming/auth tests
```

### Command Line Arguments

```bash
python combination_api_processor.py input.csv output.csv \
  --api-url "https://sandbox-api.saasquatchleads.com/scraper/scrape-stream" \
  --industry-col industry \
  --city-col city --state-col state --country-col country \
  --max-workers 1 --max-memory 80 --max-cpu 60 \
  --calls-per-second 0.1 --batch-size 10 \
  --login-url "https://sandbox-api.saasquatchleads.com/api/auth/login" \
  --email "developer@example.com" --password "****"
```

## Input CSV Format

```csv
industry,city,state,country
software development,Dallas,TX,USA
healthcare,Los Angeles,CA,USA
```

## Output Files

- `results_output_YYYYMMDD_HHMMSS.csv` – Final companies (one row per company)
- `results_output_YYYYMMDD_HHMMSS_partial.csv` – Incremental companies saved after each batch
- `results_output_YYYYMMDD_HHMMSS_batch_N.csv` – Batch metadata per processed window
- `combination_processor.log` – Detailed logs

### Final CSV Columns
```
industry,location,scrape_timestamp,api_call_id,batch_number,Company,Industry,Street,City,State,BBB_rating,Business_phone,Website
```

## API Requirements

- Method: GET
- Query params: `industry` (str), `location` (str, strictly "City, State, Country")
- Streaming format:
  - `{"message":"Scraper started"}`
  - Batch objects with `batch`, `new_items`, `total_scraped`, `elapsed_time`, `processed_count`
  - `{"message":"Scraping completed", ...}`

## Progress & Reliability

- Streams last ~5–8 minutes per call.
- Progress saved incrementally to partial CSV after each batch.
- Ctrl+C stops stream promptly and preserves already-saved rows.

## Troubleshooting

- No rows in CSV:
  - Open the latest timestamped file, not the old `results_output.csv`.
  - If you interrupted early, check the `_partial.csv` file for saved batches.
  - Ensure `max_workers=1` for streaming.
  - Verify auth/login endpoints and credentials.
- Rate limits/Resources:
  - Raise memory/CPU thresholds if pausing too often (e.g., memory 85, CPU 60).

## Security

- Uses HTTPS endpoints.
- Credentials reside in local config; rotate regularly.

## License

This script is part of the LeadGenAI project and follows the same licensing terms.