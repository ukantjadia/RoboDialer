# Agentic Backend Logging

This document describes the dedicated logging system for the backend_agentic service.

## Overview

The backend_agentic service now has its own dedicated logging system that creates a separate log file (`agentic_backend.log`) specifically for agentic operations, separate from the main backend application logs.

## Log File Location

```
LeadGenAI/backend-database/backend/services/backend_agentic/agentic_backend.log
```

## Features

- **Dedicated Log File**: Separate from main backend app.log
- **Rotating File Handler**: 10MB max size, keeps 7 backup files
- **Detailed Formatting**: Includes timestamp, log level, module, line number, and message
- **Component-Specific Loggers**: Different loggers for different components
- **Third-Party Log Capture**: Captures logs from libraries like asyncio, httpx, langchain, etc.
- **Context-Aware Logging**: Uses context managers to capture all logs during agentic operations
- **No Propagation**: Prevents duplicate logs in main backend log

## Usage

### In Python Code

```python
from agentic_logging import get_agentic_logger, AgenticLogContext

# Get logger for specific component
logger = get_agentic_logger('component_name')

# Log messages
logger.info("Information message")
logger.debug("Debug message")
logger.warning("Warning message")
logger.error("Error message")

# Capture all logs during an operation (including third-party libraries)
with AgenticLogContext():
    # All logs within this context will go to agentic_backend.log
    some_operation_that_uses_third_party_libs()
```

### Component Loggers

The following component-specific loggers are available:

- `agentic_backend.routes` - Main route handlers
- `agentic_backend.workers` - Worker components (scraper, fact retriever)
- `agentic_backend.services` - Service components (orchestrator, etc.)
- `agentic_backend.llm` - LLM client components
- `agentic_backend.aggregator` - Aggregator and prompt builder
- `agentic_backend.context` - Context management components

### Log Format

```
[TIMESTAMP] LEVEL in LOGGER_NAME:MODULE:LINE_NUMBER: MESSAGE
```

Example:
```
[2025-09-12 18:01:13,059] INFO in agentic_backend.routes:main:45: Processing query: tell me about company X
```

## Configuration

The logging system is automatically initialized when the agentic backend starts. You can customize the log file location by passing a path to `setup_agentic_logging()`:

```python
from agentic_logging import setup_agentic_logging

# Custom log file location
setup_agentic_logging('/path/to/custom/agentic.log')
```

## Log Rotation

- **Max File Size**: 10MB
- **Backup Count**: 7 files
- **Rotation**: Automatic when size limit is reached
- **Backup Naming**: `agentic_backend.log.1`, `agentic_backend.log.2`, etc.

## Benefits

1. **Isolation**: Agentic logs are separate from main backend logs
2. **Focused Debugging**: Easier to debug agentic-specific issues
3. **Performance**: No interference with main backend logging
4. **Scalability**: Independent log rotation and management
5. **Monitoring**: Can monitor agentic operations separately

## Monitoring

You can monitor the agentic backend logs using:

```bash
# Follow live logs
tail -f LeadGenAI/backend-database/backend/services/backend_agentic/agentic_backend.log

# Search for specific patterns
grep "ERROR" LeadGenAI/backend-database/backend/services/backend_agentic/agentic_backend.log

# View recent logs
tail -n 100 LeadGenAI/backend-database/backend/services/backend_agentic/agentic_backend.log
```

## Integration

The logging system is automatically integrated into all major agentic backend components:

- ✅ Main route handlers (`main.py`)
- ✅ Aggregator (`aggregator/aggregator.py`)
- ✅ Prompt Builder (`aggregator/prompt_builder.py`)
- ✅ DeepSeek Client (`llm/deepseek_client.py`)
- ✅ Scraper Worker (`workers/scraper_worker.py`)
- ✅ Fact Retriever Worker (`workers/fact_retriever_worker.py`)
- ✅ Router Client (`services/orchestrator/router_client.py`)

## Utility Functions

```python
from agentic_logging import log_capture_status, clear_agentic_log_capture

# Check which loggers are being captured
log_capture_status()

# Clear all agentic log capture (for cleanup/testing)
clear_agentic_log_capture()
```

## Troubleshooting

If you encounter logging issues:

1. **Check file permissions**: Ensure the service can write to the log directory
2. **Check disk space**: Ensure sufficient disk space for log files
3. **Check imports**: Ensure `agentic_logging` module is properly imported
4. **Check initialization**: Ensure `setup_agentic_logging()` is called before using loggers
5. **Check capture status**: Use `log_capture_status()` to see which loggers are being captured
6. **Third-party logs missing**: Ensure `capture_all_logs_to_agentic()` is called or use `AgenticLogContext()`

## Example Usage

```python
# In a new component
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('my_component')

def my_function():
    logger.info("Starting function execution")
    try:
        # Your code here
        result = some_operation()
        logger.debug(f"Operation result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in my_function: {str(e)}", exc_info=True)
        raise
```