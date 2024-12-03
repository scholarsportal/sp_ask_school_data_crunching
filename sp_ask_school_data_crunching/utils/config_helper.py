import os
import configparser
from pathlib import Path
from typing import Optional, Tuple

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

def check_lh3_config() -> Tuple[bool, str]:
    """Check if lh3api configuration exists and is valid"""
    home = str(Path.home())
    config_dir = os.path.join(home, '.lh3')
    config_file = os.path.join(config_dir, 'config')
    credentials_file = os.path.join(config_dir, 'credentials')
    
    # Check if directory exists
    if not os.path.exists(config_dir):
        return False, f"Configuration directory not found at {config_dir}"
    
    # Check if files exist
    if not os.path.exists(config_file):
        return False, f"Config file not found at {config_file}"
    if not os.path.exists(credentials_file):
        return False, f"Credentials file not found at {credentials_file}"
    
    # Check file contents
    try:
        config = configparser.ConfigParser()
        config.read([config_file, credentials_file])
        
        if not config.has_section('default'):
            return False, "Missing 'default' section in configuration files"
        
        required_config = ['scheme', 'server', 'timezone', 'version']
        required_creds = ['username', 'password']
        
        for item in required_config:
            if not config.has_option('default', item):
                return False, f"Missing required config item: {item}"
                
        for item in required_creds:
            if not config.has_option('default', item):
                return False, f"Missing required credential: {item}"
        
        return True, "Configuration is valid"
        
    except Exception as e:
        return False, f"Error reading configuration: {str(e)}"

def setup_lh3_config(username: str, password: str) -> bool:
    """Set up lh3api configuration files"""
    try:
        home = str(Path.home())
        config_dir = os.path.join(home, '.lh3')
        
        # Create directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Create config file
        config_content = """[default]
scheme = https
server = libraryh3lp.com
timezone = UTC
version = v2
"""
        with open(os.path.join(config_dir, 'config'), 'w') as f:
            f.write(config_content)
        
        # Create credentials file
        creds_content = f"""[default]
username = {username}
password = {password}
"""
        with open(os.path.join(config_dir, 'credentials'), 'w') as f:
            f.write(creds_content)
        
        return True
    except Exception as e:
        print(f"Error setting up configuration: {str(e)}")
        return False