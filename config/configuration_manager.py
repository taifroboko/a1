"""
Configuration Manager - A1 Agentic System

Centralized configuration management for API keys, system settings,
and environment-specific parameters.

Based on the A1 research paper specifications.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import configparser
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API configuration settings"""
    grok_api_key: str
    grok_base_url: str
    etherscan_api_key: str
    bscscan_api_key: str
    alchemy_eth_url: str
    alchemy_bnb_url: str

@dataclass
class SystemConfig:
    """System configuration settings"""
    max_iterations: int
    max_concurrent_contracts: int
    max_route_hops: int
    min_liquidity_usd: float
    min_profit_percentage: float
    max_price_impact: float
    enable_compression: bool
    storage_db_path: str
    storage_data_dir: str
    max_db_size_mb: int
    log_level: str
    enable_metrics: bool

@dataclass
class NetworkConfig:
    """Network-specific configuration"""
    name: str
    rpc_url: str
    scanner_api_key: str
    scanner_base_url: str
    chain_id: int
    native_token: str
    block_time: float

class ConfigurationManager:
    """
    Centralized configuration management system.
    
    Handles loading, validation, and management of all system configuration
    including API keys, network settings, and operational parameters.
    """
    
    def __init__(self, config_file: str = '.env'):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = Path(config_file)
        self.config_data: Dict[str, Any] = {}
        
        self.default_config = self._get_default_config()
        
        self._load_configuration()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'GROK_API_KEY': '',
            'GROK_BASE_URL': 'https://api.x.ai/v1',
            'ETHERSCAN_API_KEY': '',
            'BSCSCAN_API_KEY': '',
            'ALCHEMY_ETH_URL': '',
            'ALCHEMY_BNB_URL': '',
            
            'MAX_ITERATIONS': 5,
            'MAX_CONCURRENT_CONTRACTS': 3,
            'MAX_ROUTE_HOPS': 3,
            'MIN_LIQUIDITY_USD': 10000,
            'MIN_PROFIT_PERCENTAGE': 0.5,
            'MAX_PRICE_IMPACT': 5.0,
            'ENABLE_COMPRESSION': True,
            'STORAGE_DB_PATH': 'a1_results.db',
            'STORAGE_DATA_DIR': 'data',
            'MAX_DB_SIZE_MB': 1000,
            'LOG_LEVEL': 'INFO',
            'ENABLE_METRICS': True,
            
            'ETHEREUM_RPC_URL': '',
            'BSC_RPC_URL': '',
            'ETHEREUM_CHAIN_ID': 1,
            'BSC_CHAIN_ID': 56,
            
            'FORGE_ENABLED': True,
            'FORGE_TIMEOUT': 300,
            'CONCRETE_EXECUTION_TIMEOUT': 120,
            'SOURCE_CODE_CACHE_SIZE': 1000,
            'STATE_READER_BATCH_SIZE': 100,

            'ENABLE_RATE_LIMITING': True,
            'MAX_REQUESTS_PER_MINUTE': 60,
            'ENABLE_REQUEST_LOGGING': True,
            'MAX_REQUESTS_PER_SECOND': 5,
            'MAX_BATCH_SIZE': 5,
            'SANITIZE_OUTPUTS': True,
            
            'ENABLE_CACHING': True,
            'CACHE_TTL_SECONDS': 3600,
            'MAX_MEMORY_USAGE_MB': 2048,
            'ENABLE_PARALLEL_EXECUTION': True,
            
            'ENABLE_MONITORING': True,
            'METRICS_COLLECTION_INTERVAL': 60,
            'ENABLE_PERFORMANCE_TRACKING': True,
            'ENABLE_ERROR_REPORTING': True
        }
    
    def _load_configuration(self):
        """Load configuration from various sources."""
        self.config_data = self.default_config.copy()
        
        if self.config_file.exists():
            load_dotenv(self.config_file)
            logger.info(f"Loaded configuration from {self.config_file}")
        else:
            logger.warning(f"Configuration file {self.config_file} not found, using defaults")
        
        for key in self.default_config.keys():
            env_value = os.getenv(key)
            if env_value is not None:
                self.config_data[key] = self._convert_value(env_value, key)
        
        self._validate_configuration()
        
        logger.info("Configuration loaded and validated successfully")
    
    def _convert_value(self, value: str, key: str) -> Union[str, int, float, bool]:
        """Convert string value to appropriate type based on key."""
        if key in ['ENABLE_COMPRESSION', 'ENABLE_METRICS', 'FORGE_ENABLED', 
                   'ENABLE_RATE_LIMITING', 'ENABLE_REQUEST_LOGGING', 'SANITIZE_OUTPUTS',
                   'ENABLE_CACHING', 'ENABLE_PARALLEL_EXECUTION', 'ENABLE_MONITORING',
                   'ENABLE_PERFORMANCE_TRACKING', 'ENABLE_ERROR_REPORTING']:
            return value.lower() in ('true', '1', 'yes', 'on')
        
        if key in ['MAX_ITERATIONS', 'MAX_CONCURRENT_CONTRACTS', 'MAX_ROUTE_HOPS',
                   'MAX_DB_SIZE_MB', 'ETHEREUM_CHAIN_ID', 'BSC_CHAIN_ID',
                   'FORGE_TIMEOUT', 'CONCRETE_EXECUTION_TIMEOUT', 'SOURCE_CODE_CACHE_SIZE',
                   'STATE_READER_BATCH_SIZE', 'MAX_REQUESTS_PER_MINUTE', 'CACHE_TTL_SECONDS',
                   'MAX_MEMORY_USAGE_MB', 'METRICS_COLLECTION_INTERVAL',
                   'MAX_REQUESTS_PER_SECOND', 'MAX_BATCH_SIZE']:
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Invalid integer value for {key}: {value}")
                return self.default_config[key]
        
        if key in ['MIN_LIQUIDITY_USD', 'MIN_PROFIT_PERCENTAGE', 'MAX_PRICE_IMPACT']:
            try:
                return float(value)
            except ValueError:
                logger.warning(f"Invalid float value for {key}: {value}")
                return self.default_config[key]
        
        return value
    
    def _validate_configuration(self):
        """Validate configuration values."""
        errors = []
        
        required_keys = ['GROK_API_KEY', 'ETHERSCAN_API_KEY', 'BSCSCAN_API_KEY', 
                        'ALCHEMY_ETH_URL', 'ALCHEMY_BNB_URL']
        
        for key in required_keys:
            if not self.config_data.get(key):
                errors.append(f"Missing required configuration: {key}")
        
        if self.config_data['MAX_ITERATIONS'] < 1 or self.config_data['MAX_ITERATIONS'] > 10:
            errors.append("MAX_ITERATIONS must be between 1 and 10")
        
        if self.config_data['MAX_CONCURRENT_CONTRACTS'] < 1 or self.config_data['MAX_CONCURRENT_CONTRACTS'] > 20:
            errors.append("MAX_CONCURRENT_CONTRACTS must be between 1 and 20")
        
        if self.config_data['MIN_PROFIT_PERCENTAGE'] < 0 or self.config_data['MIN_PROFIT_PERCENTAGE'] > 100:
            errors.append("MIN_PROFIT_PERCENTAGE must be between 0 and 100")

        if self.config_data['MAX_REQUESTS_PER_SECOND'] < 1:
            errors.append("MAX_REQUESTS_PER_SECOND must be at least 1")

        if self.config_data['MAX_BATCH_SIZE'] < 1:
            errors.append("MAX_BATCH_SIZE must be at least 1")
        
        url_keys = ['GROK_BASE_URL', 'ALCHEMY_ETH_URL', 'ALCHEMY_BNB_URL']
        for key in url_keys:
            url = self.config_data.get(key, '')
            if url and not (url.startswith('http://') or url.startswith('https://')):
                errors.append(f"Invalid URL format for {key}: {url}")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_config(self) -> Dict[str, Any]:
        """Get complete configuration dictionary."""
        return self.config_data.copy()
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration."""
        return APIConfig(
            grok_api_key=self.config_data['GROK_API_KEY'],
            grok_base_url=self.config_data['GROK_BASE_URL'],
            etherscan_api_key=self.config_data['ETHERSCAN_API_KEY'],
            bscscan_api_key=self.config_data['BSCSCAN_API_KEY'],
            alchemy_eth_url=self.config_data['ALCHEMY_ETH_URL'],
            alchemy_bnb_url=self.config_data['ALCHEMY_BNB_URL']
        )
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration."""
        return SystemConfig(
            max_iterations=self.config_data['MAX_ITERATIONS'],
            max_concurrent_contracts=self.config_data['MAX_CONCURRENT_CONTRACTS'],
            max_route_hops=self.config_data['MAX_ROUTE_HOPS'],
            min_liquidity_usd=self.config_data['MIN_LIQUIDITY_USD'],
            min_profit_percentage=self.config_data['MIN_PROFIT_PERCENTAGE'],
            max_price_impact=self.config_data['MAX_PRICE_IMPACT'],
            enable_compression=self.config_data['ENABLE_COMPRESSION'],
            storage_db_path=self.config_data['STORAGE_DB_PATH'],
            storage_data_dir=self.config_data['STORAGE_DATA_DIR'],
            max_db_size_mb=self.config_data['MAX_DB_SIZE_MB'],
            log_level=self.config_data['LOG_LEVEL'],
            enable_metrics=self.config_data['ENABLE_METRICS']
        )
    
    def get_network_config(self, network: str) -> Optional[NetworkConfig]:
        """Get network-specific configuration."""
        network_configs = {
            'ethereum': NetworkConfig(
                name='ethereum',
                rpc_url=self.config_data['ALCHEMY_ETH_URL'],
                scanner_api_key=self.config_data['ETHERSCAN_API_KEY'],
                scanner_base_url='https://api.etherscan.io/api',
                chain_id=self.config_data['ETHEREUM_CHAIN_ID'],
                native_token='ETH',
                block_time=12.0
            ),
            'bsc': NetworkConfig(
                name='bsc',
                rpc_url=self.config_data['ALCHEMY_BNB_URL'],
                scanner_api_key=self.config_data['BSCSCAN_API_KEY'],
                scanner_base_url='https://api.bscscan.com/api',
                chain_id=self.config_data['BSC_CHAIN_ID'],
                native_token='BNB',
                block_time=3.0
            )
        }
        
        return network_configs.get(network.lower())
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self.config_data.get(key, default)
    
    def set_value(self, key: str, value: Any):
        """Set configuration value."""
        self.config_data[key] = value
        logger.debug(f"Configuration updated: {key} = {value}")
    
    def update_config(self, updates: Dict[str, Any]):
        """Update multiple configuration values."""
        self.config_data.update(updates)
        logger.info(f"Configuration updated with {len(updates)} values")
    
    def save_config(self, output_file: Optional[str] = None):
        """Save current configuration to file."""
        output_path = Path(output_file) if output_file else self.config_file
        
        try:
            with open(output_path, 'w') as f:
                f.write("# A1 Agentic System Configuration\n")
                f.write(f"# Generated on {os.path.basename(__file__)}\n\n")
                
                groups = {
                    'API Configuration': ['GROK_API_KEY', 'GROK_BASE_URL', 'ETHERSCAN_API_KEY', 
                                         'BSCSCAN_API_KEY', 'ALCHEMY_ETH_URL', 'ALCHEMY_BNB_URL'],
                    'System Configuration': ['MAX_ITERATIONS', 'MAX_CONCURRENT_CONTRACTS', 'MAX_ROUTE_HOPS',
                                           'MIN_LIQUIDITY_USD', 'MIN_PROFIT_PERCENTAGE', 'MAX_PRICE_IMPACT'],
                    'Storage Configuration': ['ENABLE_COMPRESSION', 'STORAGE_DB_PATH', 'STORAGE_DATA_DIR',
                                            'MAX_DB_SIZE_MB'],
                    'Performance Configuration': ['ENABLE_CACHING', 'CACHE_TTL_SECONDS', 'MAX_MEMORY_USAGE_MB',
                                                'ENABLE_PARALLEL_EXECUTION']
                }
                
                for group_name, keys in groups.items():
                    f.write(f"# {group_name}\n")
                    for key in keys:
                        if key in self.config_data:
                            value = self.config_data[key]
                            f.write(f"{key}={value}\n")
                    f.write("\n")
                
                written_keys = set()
                for keys in groups.values():
                    written_keys.update(keys)
                
                remaining_keys = set(self.config_data.keys()) - written_keys
                if remaining_keys:
                    f.write("# Other Configuration\n")
                    for key in sorted(remaining_keys):
                        value = self.config_data[key]
                        f.write(f"{key}={value}\n")
            
            logger.info(f"Configuration saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def export_config(self, format: str = 'json') -> str:
        """Export configuration in specified format."""
        if format.lower() == 'json':
            return json.dumps(self.config_data, indent=2)
        elif format.lower() == 'yaml':
            try:
                import yaml
                return yaml.dump(self.config_data, default_flow_style=False)
            except ImportError:
                logger.error("PyYAML not installed, cannot export as YAML")
                return json.dumps(self.config_data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate API key formats and accessibility."""
        validation_results = {}
        
        grok_key = self.config_data.get('GROK_API_KEY', '')
        validation_results['grok_api_key'] = bool(grok_key and grok_key.startswith('xai-'))
        
        etherscan_key = self.config_data.get('ETHERSCAN_API_KEY', '')
        validation_results['etherscan_api_key'] = bool(etherscan_key and len(etherscan_key) == 34)
        
        bscscan_key = self.config_data.get('BSCSCAN_API_KEY', '')
        validation_results['bscscan_api_key'] = bool(bscscan_key and len(bscscan_key) == 34)
        
        eth_url = self.config_data.get('ALCHEMY_ETH_URL', '')
        validation_results['alchemy_eth_url'] = bool(eth_url and 'alchemy.com' in eth_url)
        
        bnb_url = self.config_data.get('ALCHEMY_BNB_URL', '')
        validation_results['alchemy_bnb_url'] = bool(bnb_url and 'alchemy.com' in bnb_url)
        
        return validation_results
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        return {
            'config_file': str(self.config_file),
            'config_exists': self.config_file.exists(),
            'python_version': os.sys.version,
            'working_directory': os.getcwd(),
            'environment_variables': {
                key: '***' if 'key' in key.lower() or 'secret' in key.lower() else value
                for key, value in os.environ.items()
                if key.startswith(('XAI_', 'ETHERSCAN_', 'BSCSCAN_', 'ALCHEMY_'))
            }
        }
    
    def reload_config(self):
        """Reload configuration from file."""
        logger.info("Reloading configuration...")
        self._load_configuration()
        logger.info("Configuration reloaded successfully")
    
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        logger.warning("Resetting configuration to defaults")
        self.config_data = self.default_config.copy()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging/debugging."""
        api_validation = self.validate_api_keys()
        
        return {
            'total_config_keys': len(self.config_data),
            'api_keys_valid': all(api_validation.values()),
            'api_validation_details': api_validation,
            'max_iterations': self.config_data['MAX_ITERATIONS'],
            'max_concurrent': self.config_data['MAX_CONCURRENT_CONTRACTS'],
            'storage_enabled': bool(self.config_data['STORAGE_DB_PATH']),
            'metrics_enabled': self.config_data['ENABLE_METRICS'],
            'caching_enabled': self.config_data['ENABLE_CACHING'],
            'log_level': self.config_data['LOG_LEVEL']
        }
