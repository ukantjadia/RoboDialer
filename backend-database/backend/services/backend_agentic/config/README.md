# Configuration Management

This directory contains the configuration management system for the agentic backend, providing secure, environment-aware configuration with validation.

## Overview

The configuration system supports:
- Environment-specific configurations (development, production, testing)
- Secure API key management with validation
- Environment variable substitution
- Configuration validation and error reporting
- Type-safe configuration models with Pydantic

## Files

- `models.py` - Pydantic models for type-safe configuration
- `config_manager.py` - Configuration loading and management logic
- `__init__.py` - Module exports
- `development.yaml` - Development environment configuration
- `production.yaml` - Production environment configuration  
- `testing.yaml` - Testing environment configuration
- `README.md` - This documentation

## Usage

### Basic Usage

```python
from config import get_config

# Auto-loads configuration based on ENVIRONMENT variable
config = get_config()

# Access configuration sections
print(config.deepseek.model)
print(config.haystack.document_store)
print(config.system.log_level)
```

### Loading Specific Environment

```python
from config import load_config

# Load specific environment configuration
config = load_config("production")
```

### Configuration Validation

```python
from config import validate_config

# Validate current configuration
report = validate_config()
print(f"Valid: {report['valid']}")
print(f"Warnings: {report['warnings']}")
print(f"Errors: {report['errors']}")
```

### Using Configuration Manager Directly

```python
from config import ConfigManager

manager = ConfigManager()
config = manager.load_config("development")
validation_report = manager.validate_configuration()
```

## Environment Variables

The configuration system supports environment variable substitution using the `${VAR:default}` syntax:

```yaml
deepseek:
  api_key: ${DEEPSEEK_API_KEY}
  timeout: ${DEEPSEEK_TIMEOUT:30}
  enable_mock_fallback: ${ENABLE_MOCK_FALLBACK:true}
```

### Required Environment Variables

#### Development
- `DEEPSEEK_API_KEY` - DeepSeek API key (can be test key)

#### Production
- `DEEPSEEK_API_KEY` - Valid DeepSeek API key (must start with 'sk-')
- `QDRANT_HOST` - Qdrant server host (if using Qdrant)
- `QDRANT_PORT` - Qdrant server port (if using Qdrant)

#### Optional Environment Variables
- `ENVIRONMENT` - Environment name (development, production, testing)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `HAYSTACK_DOCUMENT_STORE` - Document store type (qdrant, faiss, inmemory)
- `CSV_DATA_PATH` - Path to CSV data file
- `SCRAPER_TIMEOUT` - Web scraper timeout in seconds
- `MAX_CONCURRENT_TOOLS` - Maximum concurrent tool executions

## Configuration Sections

### DeepSeek API (`deepseek`)
- `api_key` - API key for DeepSeek service
- `base_url` - API base URL
- `model` - Model name to use
- `timeout` - Request timeout in seconds
- `max_retries` - Maximum retry attempts
- `enable_mock_fallback` - Enable fallback to mock responses

### Data Management (`data`)
- `csv_path` - Path to CSV data file
- `enable_hot_reload` - Enable hot reload of data changes
- `validation_enabled` - Enable data validation

### Web Scraper (`scraper`)
- `timeout` - Scraping timeout in seconds
- `max_retries` - Maximum retry attempts
- `user_agent` - User agent string for requests
- `respect_robots_txt` - Whether to respect robots.txt
- `delay_between_requests` - Delay between requests in seconds

### Haystack RAG (`haystack`)
- `document_store` - Document store type (qdrant, faiss, inmemory)
- `embedding_model` - Embedding model name
- `top_k` - Number of top results to retrieve
- `index_name` - Index name for document store
- `qdrant` - Qdrant-specific configuration
- `faiss` - FAISS-specific configuration
- `inmemory` - In-memory store configuration

### LangGraph (`langgraph`)
- `recursion_limit` - Maximum recursion depth for workflows
- `checkpoint_enabled` - Enable workflow checkpoints
- `debug_mode` - Enable debug mode

### System (`system`)
- `log_level` - Logging level
- `enable_metrics` - Enable metrics collection
- `max_concurrent_tools` - Maximum concurrent tool executions
- `environment` - Environment name

## Document Store Configuration

### Qdrant
```yaml
haystack:
  document_store: qdrant
  qdrant:
    host: localhost
    port: 6333
    collection_name: company_documents
    vector_size: 384
    distance: Cosine
```

### FAISS
```yaml
haystack:
  document_store: faiss
  faiss:
    index_path: ./data/faiss_index
    index_type: IndexFlatIP
```

### In-Memory
```yaml
haystack:
  document_store: inmemory
  inmemory:
    embedding_dim: 384
```

## Validation

The configuration system provides comprehensive validation:

### API Key Validation
- Production environments require valid API keys (starting with 'sk-')
- Development/testing can use test keys (starting with 'test-')

### File Path Validation
- CSV paths must end with '.csv'
- File existence is checked (warnings for missing files)

### Numeric Validation
- Timeouts must be between 1-300 seconds
- Retry counts must be between 0-10
- Port numbers must be valid (1-65535)

### Environment-Specific Validation
- Production environments have stricter requirements
- Development environments allow mock fallbacks
- Testing environments use minimal timeouts

## Command Line Validation

Use the validation script to check configuration:

```bash
# Validate development configuration
python scripts/validate_config.py --environment development

# Validate production configuration
python scripts/validate_config.py --environment production

# Validate with custom config directory
python scripts/validate_config.py --config-dir /path/to/configs --environment production
```

## Security Considerations

### API Key Security
- API keys are stored as `SecretStr` to prevent accidental logging
- Keys are validated for proper format
- Production environments require real API keys

### Environment Variable Security
- Sensitive values should be stored in environment variables
- Configuration files should not contain hardcoded secrets
- Use `.env` files for local development (not committed to git)

### Access Control
- Configuration validation prevents invalid configurations
- Type safety prevents runtime configuration errors
- Environment-specific settings prevent development settings in production

## Error Handling

The configuration system provides detailed error reporting:

### Configuration Errors
- Missing configuration files
- Invalid YAML syntax
- Missing required environment variables
- Invalid configuration values

### Validation Errors
- Invalid API key formats
- Missing required files
- Invalid numeric ranges
- Environment-specific requirement violations

### Recovery Strategies
- Graceful degradation for non-critical configuration issues
- Clear error messages for debugging
- Validation warnings for potential issues

## Best Practices

1. **Environment Variables**: Use environment variables for sensitive data
2. **Validation**: Always validate configuration before deployment
3. **Documentation**: Document any new configuration options
4. **Testing**: Test configuration changes in all environments
5. **Security**: Never commit API keys or secrets to version control
6. **Defaults**: Provide sensible defaults for optional settings
7. **Validation**: Use the validation script in CI/CD pipelines