"""
Helper utilities for reading activation data from S3
"""
import os
import json
import logging
from datetime import datetime
from config import Config
from utils.s3_utils import download_json_from_s3
import pytz

logger = logging.getLogger(__name__)


def is_key_expired(expiration_date_str):
    """
    Check if activation key has expired
    
    Args:
        expiration_date_str: expiration date string in 'YYYY-MM-DD HH:MM:SS' format
    
    Returns:
        bool: True if expired, False otherwise
    """
    try:
        expiration_date = pytz.timezone("Asia/Kolkata").localize(datetime.strptime(expiration_date_str, '%Y-%m-%d %H:%M:%S'))
        current_date = datetime.now(pytz.timezone("Asia/Kolkata"))
        return current_date > expiration_date
    except Exception as e:
        logger.error(f"Error parsing expiration date: {e}")
        return True  # Treat invalid dates as expired for security


def get_activation_by_hardware_id(hardware_id):
    """
    Get activation data from S3 for a specific hardware ID
    
    Args:
        hardware_id: Hardware ID to lookup
    
    Returns:
        dict: Activation data with key and entry, or None if not found
    """
    try:
        # Download product keys from S3
        keys_data = download_json_from_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY)
        activations = keys_data.get('activations', {})
        
        # Find the activation entry for this hardware ID
        for key, entry in activations.items():
            if (entry.get('status') == 'activated' and 
                entry.get('hardwareId') == hardware_id):
                return {
                    'key': key,
                    'entry': entry
                }
        
        logger.warning(f"No activation found for hardware ID: {hardware_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error reading activation from S3: {e}")
        return None


def get_device_id(hardware_id=None):
    """
    Get device ID from S3 activation data
    
    Args:
        hardware_id: Hardware ID to lookup (optional - will use first activated device if not provided)
    
    Returns:
        str: Device ID (e.g., "AGS-2001") or None if not activated
    """
    try:
        if hardware_id:
            activation = get_activation_by_hardware_id(hardware_id)
            if activation:
                device_id = activation['entry'].get('deviceId')
                logger.info(f"Device ID loaded from S3: {device_id}")
                return device_id
        else:
            # If no hardware_id provided, try to get any activated device
            keys_data = download_json_from_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY)
            activations = keys_data.get('activations', {})
            
            for key, entry in activations.items():
                if entry.get('status') == 'activated':
                    device_id = entry.get('deviceId')
                    logger.info(f"Device ID loaded from S3: {device_id}")
                    return device_id
        
        logger.warning("No device ID found in S3")
        return None
            
    except Exception as e:
        logger.error(f"Error reading device ID from S3: {e}")
        return None


def is_activated(hardware_id):
    """
    Check if the system is activated for a specific hardware ID
    Also checks if the activation key has expired
    
    Args:
        hardware_id: Hardware ID to check
    
    Returns:
        bool: True if activated and not expired, False otherwise
    """
    activation = get_activation_by_hardware_id(hardware_id)
    if not activation:
        return False
    
    # Check expiration date
    expiration_date = activation['entry'].get('expirationDate')
    if expiration_date and is_key_expired(expiration_date):
        logger.warning(f"Activation key has expired: {expiration_date}")
        return False
    
    return True


def is_logged_in(hardware_id):
    """
    Check if the user is logged in (activated AND loggedIn=true in S3)
    Also checks if the activation key has expired
    
    Args:
        hardware_id: Hardware ID to check
    
    Returns:
        bool: True if logged in and not expired, False otherwise
    """
    activation = get_activation_by_hardware_id(hardware_id)
    if not activation:
        return False
    
    # Check expiration date
    expiration_date = activation['entry'].get('expirationDate')
    if expiration_date and is_key_expired(expiration_date):
        logger.warning(f"Activation key has expired: {expiration_date}")
        return False
    
    return activation['entry'].get('loggedIn') == True


def get_model_paths(hardware_id):
    """
    Get local model file paths based on activated device ID from S3
    Also checks if the activation key has expired
    
    Args:
        hardware_id: Hardware ID to lookup
    
    Returns:
        tuple: (sella_path, non_sella_path) or (None, None) if not activated or expired
    """
    try:
        # Check if activation is valid and not expired
        if not is_activated(hardware_id):
            logger.warning("Cannot get model paths: Activation invalid or expired")
            return None, None
        
        device_id = get_device_id(hardware_id)
        if not device_id:
            logger.warning("Cannot get model paths: No device ID")
            return None, None
        
        from utils.kett_predictor import get_model_paths_from_device_id
        sella_path, non_sella_path = get_model_paths_from_device_id(device_id)
        
        # Verify files exist
        if not os.path.exists(sella_path):
            logger.error(f"Sella model not found: {sella_path}")
            return None, None
        
        if not os.path.exists(non_sella_path):
            logger.error(f"Non-Sella model not found: {non_sella_path}")
            return None, None
        
        logger.info(f"Model paths loaded for device {device_id}")
        return sella_path, non_sella_path
        
    except Exception as e:
        logger.error(f"Error getting model paths: {e}")
        return None, None


def get_expiration_info(hardware_id):
    """
    Get expiration information for an activation
    
    Args:
        hardware_id: Hardware ID to lookup
    
    Returns:
        dict: Contains activatedAt, expirationDate, and isExpired, or None if not found
    """
    try:
        activation = get_activation_by_hardware_id(hardware_id)
        if not activation:
            return None
        
        entry = activation['entry']
        activated_at = entry.get('activatedAt')
        expiration_date = entry.get('expirationDate')
        
        return {
            'activatedAt': activated_at,
            'expirationDate': expiration_date,
            'isExpired': is_key_expired(expiration_date) if expiration_date else False
        }
    except Exception as e:
        logger.error(f"Error getting expiration info: {e}")
        return None