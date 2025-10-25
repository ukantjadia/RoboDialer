# Service - CSV Combination API Processor

This folder contains the CSV Combination API Processor service that generates all possible combinations of industry and location pairs, makes streaming API calls to scrape company data, and saves the results back to CSV files.

## Features

- **Streaming API Support**: Handles real-time streaming responses from the scraping API
- **Authentication**: Logs in once and reuses cookies for all calls (auto re-login on 401/403)
- **Sequential Processing**: Processes API calls sequentially (required for streaming)
- **Incremental Saving**: Writes company rows to a partial CSV after each batch so no progress is lost
- **Timestamped Outputs**: Each run writes to a new `results_output_YYYYMMDD_HHMMSS.csv`
- **Resource Control**: Monitors and limits memory and CPU usage
- **Progress Tracking**: Real-time progress monitoring with detailed streaming status
- **Duplicate Detection**: Prevents duplicate companies within each API call (Company + Industry)

## 📁 Files Overview

### Core Scripts
- **`combination_api_processor.py`** - Main processor script with resource control and streaming
- **`run_combination_processor.py`** - Python wrapper script; writes timestamped output files
- **`test_setup.py`** - Setup verification test script
- **`test_streaming.py`** - Streaming/auth sanity tests

### Configuration
- **`config_combination_processor.json`** - API URL, auth, limits, CSV columns
- **`requirements_combination_processor.txt`** - Python dependencies

### Execution Scripts
- **`run_combination_processor.sh`** - Linux/Mac shell script (supports `--check`, `--install`, `--test`, `--latest`)
- **`run_combination_processor.bat`** - Windows batch script

### Documentation & Examples
- **`README_combination_processor.md`** - Detailed documentation
- **`sample_input.csv`** - Example input file format

## 🚀 Quick Start

### Linux/Mac
```bash
# Make script executable (if needed)
chmod +x run_combination_processor.sh

# Run the processor (writes results_output_YYYYMMDD_HHMMSS.csv)
./run_combination_processor.sh

# Show most recent results
./run_combination_processor.sh --latest

# Check setup only
./run_combination_processor.sh --check

# Install dependencies only
./run_combination_processor.sh --install

# Run setup test
./run_combination_processor.sh --test
```

### Windows
```cmd
# Double-click or run from command prompt
run_combination_processor.bat
```

### Python Direct
```bash
# Install dependencies
pip install -r requirements_combination_processor.txt

# Run processor (timestamped output)
python run_combination_processor.py
```

## ⚙️ Configuration

Edit `config_combination_processor.json` to customize:
- API endpoint URL (streaming)
- Auth login URL and credentials (cookies-based)
- Resource limits (memory, CPU)
- Processing parameters (workers, rate limiting)
- CSV column names (`industry`, `city`, `state`, `country`)

## 📊 Input Format

Your CSV should have these columns:
```csv
industry,city,state,country
software development,Dallas,TX,USA
healthcare,Los Angeles,CA,USA
```

## 📈 Output Files

The service generates (in `LeadGenAI/service`):
- `results_output_YYYYMMDD_HHMMSS.csv` – Final output: all scraped companies (one row per company)
- `results_output_YYYYMMDD_HHMMSS_partial.csv` – Incremental/partial output written after every batch
- `results_output_YYYYMMDD_HHMMSS_batch_N.csv` – Intermediate metadata per processed batch window
- `combination_processor.log` – Processing logs with streaming progress

## 🔧 Resource Control

The service automatically:
- Monitors system memory and CPU; pauses when over limits
- Processes combinations sequentially (streaming cannot run concurrently)

## 📖 Detailed Documentation

See `README_combination_processor.md` for:
- Advanced usage examples and CLI flags
- Authentication details
- Troubleshooting and performance tips

## 🛠️ Requirements

- Python 3.7+
- pandas, requests, psutil
- **Streaming API endpoint**: `https://sandbox-api.saasquatchleads.com/scraper/scrape-stream`
- **Processing time**: 5–8 minutes per API call (streaming)
- **Sequential processing**: Only one API call at a time

## 🔐 Authentication (Cookies)

Configured via `config_combination_processor.json`:
```json
{
  "auth": {
    "login_url": "https://sandbox-api.saasquatchleads.com/api/auth/login",
    "email": "developer@example.com",
    "password": "****"
  }
}
```

Test auth/streaming:
```bash
python test_streaming.py
```

If cookies expire or login fails, the processor auto re-logins once.