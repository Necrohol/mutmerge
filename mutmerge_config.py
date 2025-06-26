#!/usr/bin/env python3
"""
Configuration management module for MutMerge
Handles loading and parsing of configuration files
"""

import os
import configparser
from typing import Dict


class ConfigManager:
    """Manage configuration from packages.toml or config.in"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or self.find_config_file()
        self.config = self.load_config()
    
    def find_config_file(self) -> str:
        """Find configuration file (packages.toml or config.in)"""
        candidates = ["packages.toml", "config.in", "mutmerge.toml"]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        raise FileNotFoundError("No configuration file found (packages.toml, config.in, mutmerge.toml)")
    
    def load_config(self) -> Dict:
        """Load configuration based on file type"""
        if self.config_path.endswith('.toml'):
            return self.load_toml_config()
        else:
            return self.load_ini_config()
    
    def load_toml_config(self) -> Dict:
        """Load TOML configuration"""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ImportError("tomllib/tomli required for TOML support")
        
        with open(self.config_path, 'rb') as f:
            return tomllib.load(f)
    
    def load_ini_config(self) -> Dict:
        """Load INI-style configuration"""
        config = configparser.ConfigParser()
        config.read(self.config_path)
        
        result = {}
        for section in config.sections():
            result[section] = dict(config[section])
        
        return result
    
    def get_packages(self) -> Dict[str, Dict]:
        """Get package configurations"""
        if 'packages' in self.config:
            return self.config['packages']
        
        # Fallback for config.in format
        packages = {}
        for section, values in self.config.items():
            if section.startswith('package.'):
                pkg_name = section.replace('package.', '')
                packages[pkg_name] = values
        
        return packages
    
    def get_global_settings(self) -> Dict:
        """Get global settings from configuration"""
        return self.config.get('settings', {})
    
    def get_package_config(self, package_name: str) -> Dict:
        """Get configuration for a specific package"""
        packages = self.get_packages()
        return packages.get(package_name, {})
