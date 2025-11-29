# storage/s3_activation.py
"""
S3 activation data operations
Handles reading/writing activation keys and device data
"""

import json
import logging
from datetime import datetime
import pytz
from config.settings import Config
from .s3_client import download_bytes, upload_bytes

logger = logging.getLogger(__name__)


def is_key_expired(expiration_date_str):
    """
    Check if activation key has expired
    
    Args:
        expiration_date_str: Expiration date string in 'YYYY-MM-DD HH:MM:SS' format
    
    Returns:
        bool: True if expired, False otherwise
    
    Example:
        >>> is_key_expired("2024-12-31 23:59:59")
        False  # (assuming current date is before this)
    """
    try:
        expiration_date = pytz.timezone("Asia/Kolkata").localize(
            datetime.strptime(expiration_date_str, '%Y-%m-%d %H:%M:%S')
        )
        current_date = datetime.now(pytz.timezone("Asia/Kolkata"))
        is_expired = current_date > expiration_date
        
        if is_expired:
            logger.warning(f"Key expired: {expiration_date_str}")
        
        return is_expired
    except Exception as e:
        logger.error(f"Error parsing expiration date: {e}")
        return True  # Treat invalid dates as expired for security


def get_activation_data():
    """
    Download and parse activation data from S3
    
    Returns:
        dict: Activation data or None if error
            {
                'activations': {...},
                'totalActivations': int,
                'lastUpdated': str
            }
    
    Example:
        >>> data = get_activation_data()
        >>> print(data['totalActivations'])
        42
    """
    try:
        content = download_bytes(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY)
        if content is None:
            logger.error("Failed to download activation data from S3")
            return None
        
        data = json.loads(content.decode('utf-8'))
        logger.info(f"Loaded activation data: {data.get('totalActivations', 0)} activations")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing activation JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting activation data: {e}")
        return None


def update_activation_data(data):
    """
    Upload updated activation data to S3
    
    Args:
        data: Activation data dictionary
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        >>> data = get_activation_data()
        >>> data['activations']['KEY123']['status'] = 'activated'
        >>> update_activation_data(data)
        True
    """
    try:
        json_data = json.dumps(data, indent=2)
        success = upload_bytes(
            json_data.encode('utf-8'),
            Config.S3_BUCKET_NAME,
            Config.PRODUCT_KEYS_KEY,
            content_type='application/json'
        )
        
        if success:
            logger.info("Successfully updated activation data on S3")
        else:
            logger.error("Failed to update activation data on S3")
        
        return success
    except Exception as e:
        logger.error(f"Error updating activation data: {e}")
        return False


def get_activation_by_key(activation_key):
    """
    Get activation entry for a specific key
    
    Args:
        activation_key: Activation key to lookup
    
    Returns:
        dict: Activation entry or None if not found
            {
                'status': 'activated',
                'username': 'user@example.com',
                'hardwareId': '...',
                'deviceId': 'AGS-2001',
                'activatedAt': '...',
                'expirationDate': '...',
                'loggedIn': bool
            }
    """
    data = get_activation_data()
    if data is None:
        return None
    
    activations = data.get('activations', {})
    entry = activations.get(activation_key)
    
    if entry:
        logger.info(f"Found activation entry for key: {activation_key[:8]}...")
    else:
        logger.warning(f"No activation entry found for key: {activation_key[:8]}...")
    
    return entry


def get_activation_by_hardware_id(hardware_id):
    """
    Get activation entry for a specific hardware ID
    
    Args:
        hardware_id: Hardware ID to lookup
    
    Returns:
        tuple: (activation_key, activation_entry) or (None, None) if not found
    """
    data = get_activation_data()
    if data is None:
        return None, None
    
    activations = data.get('activations', {})
    
    for key, entry in activations.items():
        if (entry.get('status') == 'activated' and 
            entry.get('hardwareId') == hardware_id):
            logger.info(f"Found activation for hardware ID: {hardware_id[:8]}...")
            return key, entry
    
    logger.warning(f"No activation found for hardware ID: {hardware_id[:8]}...")
    return None, None


def get_device_id_from_s3(hardware_id=None):
    """
    Get device ID from S3 activation data
    
    Args:
        hardware_id: Hardware ID to lookup (optional - uses first activated device if not provided)
    
    Returns:
        str: Device ID (e.g., "AGS-2001") or None if not found
    
    Example:
        >>> device_id = get_device_id_from_s3("ABC123...")
        >>> print(device_id)
        'AGS-2001'
    """
    try:
        data = get_activation_data()
        if data is None:
            return None
        
        activations = data.get('activations', {})
        
        if hardware_id:
            # Find specific hardware ID
            for key, entry in activations.items():
                if (entry.get('status') == 'activated' and 
                    entry.get('hardwareId') == hardware_id):
                    device_id = entry.get('deviceId')
                    logger.info(f"Device ID for hardware {hardware_id[:8]}...: {device_id}")
                    return device_id
        else:
            # Return first activated device
            for key, entry in activations.items():
                if entry.get('status') == 'activated':
                    device_id = entry.get('deviceId')
                    logger.info(f"Found device ID: {device_id}")
                    return device_id
        
        logger.warning("No device ID found in S3")
        return None
    except Exception as e:
        logger.error(f"Error getting device ID from S3: {e}")
        return None


def is_activated(hardware_id):
    """
    Check if the hardware is activated (and not expired)
    
    Args:
        hardware_id: Hardware ID to check
    
    Returns:
        bool: True if activated and not expired, False otherwise
    """
    key, entry = get_activation_by_hardware_id(hardware_id)
    if not entry:
        return False
    
    # Check expiration
    expiration_date = entry.get('expirationDate')
    if expiration_date and is_key_expired(expiration_date):
        logger.warning(f"Activation for {hardware_id[:8]}... has expired")
        return False
    
    return True


def is_logged_in(hardware_id):
    """
    Check if user is logged in (activated AND loggedIn=true)
    
    Args:
        hardware_id: Hardware ID to check
    
    Returns:
        bool: True if logged in and not expired, False otherwise
    """
    if not is_activated(hardware_id):
        return False
    
    key, entry = get_activation_by_hardware_id(hardware_id)
    logged_in = entry.get('loggedIn') == True
    
    if logged_in:
        logger.info(f"User is logged in: {hardware_id[:8]}...")
    else:
        logger.info(f"User is not logged in: {hardware_id[:8]}...")
    
    return logged_in


def update_login_status(hardware_id, logged_in):
    """
    Update login status for a hardware ID
    
    Args:
        hardware_id: Hardware ID
        logged_in: True to log in, False to log out
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = get_activation_data()
        if data is None:
            return False
        
        activations = data.get('activations', {})
        
        # Find and update the entry
        updated = False
        for key, entry in activations.items():
            if (entry.get('status') == 'activated' and 
                entry.get('hardwareId') == hardware_id):
                entry['loggedIn'] = logged_in
                
                current_time = datetime.now(pytz.timezone("Asia/Kolkata")).strftime(
                    '%Y-%m-%d %H:%M:%S'
                )
                
                if logged_in:
                    entry['lastLoginAt'] = current_time
                    logger.info(f"Set loggedIn=True for {hardware_id[:8]}...")
                else:
                    entry['lastLogoutAt'] = current_time
                    logger.info(f"Set loggedIn=False for {hardware_id[:8]}...")
                
                updated = True
                break
        
        if not updated:
            logger.warning(f"No activation found to update for {hardware_id[:8]}...")
            return False
        
        # Upload updated data
        return update_activation_data(data)
    except Exception as e:
        logger.error(f"Error updating login status: {e}")
        return False


def get_expiration_info(hardware_id):
    """
    Get expiration information for hardware ID
    
    Args:
        hardware_id: Hardware ID to lookup
    
    Returns:
        dict: Contains activatedAt, expirationDate, and isExpired, or None if not found
    
    Example:
        >>> info = get_expiration_info("ABC123...")
        >>> print(info['expirationDate'])
        '2025-12-31 23:59:59'
    """
    try:
        key, entry = get_activation_by_hardware_id(hardware_id)
        if not entry:
            return None
        
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