"""Configuration manager with validation and secure handling."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from functools import lru_cache
import logging
from string import Template

from .models import AppConfig

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass


class ConfigManager:
    """Manages application configuration with environment-based loading."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir or Path(__file__).parent
        self._config: Optional[AppConfig] = None
        self._environment = os.getenv("ENVIRONMENT", "development")

    def load_config(self, environment: Optional[str] = None) -> AppConfig:
        """Load configuration for the specified environment.
        
        Args:
            environment: Environment name (development, production, testing)
            
        Returns:
            Loaded and validated configuration
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        env = environment or self._environment
        config_file = self.config_dir / f"{env}.yaml"
        
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_file}")
        
        try:
            # Load YAML configuration
            with open(config_file, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Substitute environment variables
            resolved_config = self._resolve_environment_variables(raw_config)
            
            # Validate and create configuration object
            self._config = AppConfig(**resolved_config)
            
            logger.info(f"Configuration loaded successfully for environment: {env}")
            return self._config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _resolve_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve environment variables in configuration.
        
        Args:
            config: Configuration dictionary with potential ${VAR} placeholders
            
        Returns:
            Configuration with resolved environment variables
        """
        if isinstance(config, dict):
            return {key: self._resolve_environment_variables(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._resolve_environment_variables(item) for item in config]
        elif isinstance(config, str):
            return self._substitute_env_vars(config)
        else:
            return config

    def _substitute_env_vars(self, value: str) -> Any:
        """Substitute environment variables in a string value.
        
        Args:
            value: String potentially containing ${VAR} or ${VAR:default} patterns
            
        Returns:
            Substituted value with appropriate type conversion
        """
        if not isinstance(value, str) or '${' not in value:
            return value
        
        # Extract all variable names from the template
        import re
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        matches = re.findall(pattern, value)
        
        if not matches:
            return value
        
        # If the entire string is a single variable substitution, return the converted value
        if len(matches) == 1 and value == f"${{{matches[0][0]}" + (f":{matches[0][1]}" if matches[0][1] else "") + "}":
            var_name, default_value = matches[0]
            env_value = os.getenv(var_name, default_value)
            return self._convert_type(env_value)
        
        # Handle multiple substitutions or partial substitutions
        template = Template(value)
        env_vars = {}
        
        for var_name, default_value in matches:
            env_value = os.getenv(var_name, default_value)
            env_vars[var_name] = str(env_value)  # Keep as string for template substitution
        
        try:
            result = template.safe_substitute(env_vars)
            return self._convert_type(result)
        except KeyError as e:
            raise ConfigurationError(f"Environment variable not found: {e}")

    def _convert_type(self, value: str) -> Any:
        """Convert string values to appropriate types.
        
        Args:
            value: String value to convert
            
        Returns:
            Converted value (bool, int, float, or str)
        """
        if not isinstance(value, str):
            return value
        
        # Boolean conversion
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Numeric conversion
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        return value

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return validation report.
        
        Returns:
            Dictionary containing validation results and any issues found
        """
        if not self._config:
            return {"valid": False, "error": "No configuration loaded"}
        
        validation_report = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "environment": self._config.system.environment
        }
        
        # Validate API key
        if self._config.system.environment == "production":
            api_key = self._config.deepseek.api_key.get_secret_value()
            if not api_key or api_key.startswith('test-'):
                validation_report["errors"].append(
                    "Production environment requires a valid DeepSeek API key"
                )
        
        # Validate file paths
        csv_path = Path(self._config.data.csv_path)
        if not csv_path.exists() and self._config.system.environment != "testing":
            validation_report["warnings"].append(f"CSV data file not found: {csv_path}")
        
        # Validate document store configuration
        if self._config.haystack.document_store == "qdrant":
            # Check if Qdrant is accessible (in production)
            if self._config.system.environment == "production":
                validation_report["warnings"].append(
                    "Qdrant connectivity should be verified in production"
                )
        
        # Check for development-specific warnings
        if self._config.system.environment == "development":
            if not self._config.deepseek.enable_mock_fallback:
                validation_report["warnings"].append(
                    "Mock fallback disabled in development environment"
                )
        
        validation_report["valid"] = len(validation_report["errors"]) == 0
        return validation_report

    def get_config(self) -> AppConfig:
        """Get current configuration.
        
        Returns:
            Current configuration object
            
        Raises:
            ConfigurationError: If no configuration is loaded
        """
        if not self._config:
            raise ConfigurationError("No configuration loaded. Call load_config() first.")
        return self._config

    def reload_config(self) -> AppConfig:
        """Reload configuration from file.
        
        Returns:
            Reloaded configuration object
        """
        self._config = None
        return self.load_config()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


@lru_cache(maxsize=1)
def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance.
    
    Returns:
        Global ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get current application configuration.
    
    Returns:
        Current configuration object
        
    Raises:
        ConfigurationError: If configuration is not loaded
    """
    manager = get_config_manager()
    try:
        return manager.get_config()
    except ConfigurationError:
        # Auto-load configuration if not already loaded
        return manager.load_config()


def load_config(environment: Optional[str] = None) -> AppConfig:
    """Load configuration for specified environment.
    
    Args:
        environment: Environment name
        
    Returns:
        Loaded configuration object
    """
    manager = get_config_manager()
    return manager.load_config(environment)


def validate_config() -> Dict[str, Any]:
    """Validate current configuration.
    
    Returns:
        Validation report dictionary
    """
    manager = get_config_manager()
    return manager.validate_configuration()