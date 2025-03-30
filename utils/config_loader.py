"""
Configuration loading utilities for YouTube Shorts Automation System.
Handles loading and validation of YAML configuration files.
"""
import os
import logging
import yaml
from typing import Dict, Any, Optional
from utils.error_handling import ConfigError, safe_execute

logger = logging.getLogger(__name__)

class ConfigLoader:
    """
    Handles loading and validation of configuration files.
    Supports main config and API keys config.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the config loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.config_data = {}
        self.api_keys = {}
        
        # Create config directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            logger.info(f"Created config directory: {config_dir}")
    
    def load_config(self, filename: str = "config.yaml") -> Dict[str, Any]:
        """
        Load and parse the main configuration file.
        
        Args:
            filename: Name of the configuration file
            
        Returns:
            Dictionary containing configuration values
            
        Raises:
            ConfigError: If the configuration file is invalid or missing required values
        """
        config_path = os.path.join(self.config_dir, filename)
        
        # Check if file exists
        if not os.path.exists(config_path):
            # Create default config
            self._create_default_config(config_path)
        
        try:
            with open(config_path, 'r') as config_file:
                self.config_data = yaml.safe_load(config_file)
                logger.info(f"Loaded configuration from {config_path}")
                
                # Validate configuration
                self._validate_config(self.config_data)
                
                return self.config_data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing {config_path}: {str(e)}")
            raise ConfigError(f"Invalid YAML in configuration file: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading {config_path}: {str(e)}")
            raise ConfigError(f"Failed to load configuration: {str(e)}")
    
    def load_api_keys(self, filename: str = "api_keys.yaml") -> Dict[str, Any]:
        """
        Load and parse the API keys configuration file.
        
        Args:
            filename: Name of the API keys file
            
        Returns:
            Dictionary containing API keys and credentials
            
        Raises:
            ConfigError: If the API keys file is invalid or missing required values
        """
        api_keys_path = os.path.join(self.config_dir, filename)
        
        # Check if file exists
        if not os.path.exists(api_keys_path):
            # Create template API keys file
            self._create_api_keys_template(api_keys_path)
            logger.warning(f"Created API keys template at {api_keys_path}. Please fill in your credentials.")
            return {}
        
        try:
            with open(api_keys_path, 'r') as api_keys_file:
                self.api_keys = yaml.safe_load(api_keys_file)
                logger.info(f"Loaded API keys from {api_keys_path}")
                
                # Basic validation
                if not isinstance(self.api_keys, dict):
                    raise ConfigError("API keys file must contain a dictionary")
                
                return self.api_keys
        except yaml.YAMLError as e:
            logger.error(f"Error parsing {api_keys_path}: {str(e)}")
            raise ConfigError(f"Invalid YAML in API keys file: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading {api_keys_path}: {str(e)}")
            raise ConfigError(f"Failed to load API keys: {str(e)}")
    
    def get_config_value(self, key_path: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value using dot notation for nested keys.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., "video.resolution")
            default: Default value to return if the key doesn't exist
            
        Returns:
            The configuration value or the default if not found
        """
        if not self.config_data:
            logger.warning("Attempted to get config value before loading configuration")
            return default
        
        # Split the key path
        keys = key_path.split('.')
        value = self.config_data
        
        # Traverse the nested dictionary
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.debug(f"Config key '{key_path}' not found, using default: {default}")
                return default
        
        return value
    
    def get_api_key(self, service: str, key_name: str = "api_key") -> Optional[str]:
        """
        Get an API key for a specific service.
        
        Args:
            service: The service name (e.g., "youtube", "image_generation")
            key_name: The key name within the service configuration
            
        Returns:
            The API key or None if not found
        """
        if not self.api_keys:
            logger.warning("Attempted to get API key before loading API keys configuration")
            return None
        
        # Check if the service exists in the API keys
        if service in self.api_keys and isinstance(self.api_keys[service], dict):
            # Check if the key name exists in the service configuration
            if key_name in self.api_keys[service]:
                return self.api_keys[service][key_name]
        
        logger.warning(f"API key for {service}.{key_name} not found")
        return None
    
    def save_config(self, config_data: Dict[str, Any], filename: str = "config.yaml") -> bool:
        """
        Save configuration data to a file.
        
        Args:
            config_data: Dictionary containing configuration values
            filename: Name of the configuration file
            
        Returns:
            True if successful, False otherwise
        """
        config_path = os.path.join(self.config_dir, filename)
        
        try:
            with open(config_path, 'w') as config_file:
                yaml.dump(config_data, config_file, default_flow_style=False)
                logger.info(f"Saved configuration to {config_path}")
                
                # Update the internal config data
                self.config_data = config_data
                
                return True
        except Exception as e:
            logger.error(f"Error saving configuration to {config_path}: {str(e)}")
            return False
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate the configuration data.
        
        Args:
            config: Dictionary containing configuration values
            
        Raises:
            ConfigError: If the configuration is invalid
        """
        # Check for required top-level sections
        required_sections = ["workflow", "content", "video", "image", "audio"]
        for section in required_sections:
            if section not in config:
                raise ConfigError(f"Required configuration section '{section}' is missing")
        
        # Validate workflow settings
        if "default_interval_minutes" not in config["workflow"]:
            raise ConfigError("Workflow configuration must include 'default_interval_minutes'")
        
        # Validate video settings
        if "resolution" not in config["video"]:
            raise ConfigError("Video configuration must include 'resolution'")
        if "duration_seconds" not in config["video"]:
            raise ConfigError("Video configuration must include 'duration_seconds'")
        
        logger.debug("Configuration validation successful")
    
    def _create_default_config(self, config_path: str) -> None:
        """
        Create a default configuration file.
        
        Args:
            config_path: Path where the configuration file will be created
        """
        default_config = {
            "workflow": {
                "default_interval_minutes": 60,
                "max_videos_per_day": 10
            },
            "content": {
                "spreadsheet_id": "",
                "default_themes": ["travel", "tech", "cooking", "fitness"]
            },
            "video": {
                "resolution": "1080x1920",  # Vertical for shorts
                "duration_seconds": 60,
                "fps": 30
            },
            "image": {
                "count_per_video": 5,
                "style": "photorealistic"
            },
            "audio": {
                "duration_seconds": 60,
                "fade_in_seconds": 1,
                "fade_out_seconds": 2
            }
        }
        
        try:
            with open(config_path, 'w') as config_file:
                yaml.dump(default_config, config_file, default_flow_style=False)
                logger.info(f"Created default configuration at {config_path}")
        except Exception as e:
            logger.error(f"Error creating default configuration: {str(e)}")
    
    def _create_api_keys_template(self, api_keys_path: str) -> None:
        """
        Create a template API keys file.
        
        Args:
            api_keys_path: Path where the API keys file will be created
        """
        template = {
            "youtube": {
                "client_id": "YOUR_CLIENT_ID",
                "client_secret": "YOUR_CLIENT_SECRET",
                "refresh_token": "YOUR_REFRESH_TOKEN"
            },
            "image_generation": {
                "provider": "stable_diffusion",  # or "dalle"
                "api_key": "YOUR_API_KEY"
            },
            "audio": {
                "provider": "YOUR_AUDIO_PROVIDER",
                "api_key": "YOUR_API_KEY"
            }
        }
        
        try:
            with open(api_keys_path, 'w') as api_keys_file:
                yaml.dump(template, api_keys_file, default_flow_style=False)
                logger.info(f"Created API keys template at {api_keys_path}")
        except Exception as e:
            logger.error(f"Error creating API keys template: {str(e)}")