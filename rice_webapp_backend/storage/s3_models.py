# storage/s3_models.py
"""
S3 model file operations
Handles downloading and managing Kett prediction model files
"""

import os
import re
import logging
from config.settings import Config
from .s3_client import download_file, object_exists

logger = logging.getLogger(__name__)


def extract_model_number_from_device_id(device_id):
    """
    Extract model number from device ID
    
    Args:
        device_id: Device ID (e.g., "AGS-2001", "AGS-2002")
    
    Returns:
        str: Model number (e.g., "2001", "2002")
    
    Raises:
        ValueError: If device ID format is invalid
    
    Example:
        >>> extract_model_number_from_device_id("AGS-2001")
        '2001'
        
        >>> extract_model_number_from_device_id("AGS-2002")
        '2002'
    """
    # Extract numeric part after the last dash
    match = re.search(r'-(\d+)$', device_id)
    if match:
        return match.group(1)
    
    # Fallback: extract any 4-digit number
    match = re.search(r'(\d{4})', device_id)
    if match:
        return match.group(1)
    
    raise ValueError(f"Could not extract model number from device ID: {device_id}")


def get_model_s3_keys(device_id):
    """
    Get S3 keys for model files based on device ID
    
    Args:
        device_id: Device ID (e.g., "AGS-2001")
    
    Returns:
        tuple: (sella_s3_key, non_sella_s3_key)
    
    Example:
        >>> sella_key, non_sella_key = get_model_s3_keys("AGS-2001")
        >>> print(sella_key)
        'models_sella/2001_1.csv'
    """
    model_number = extract_model_number_from_device_id(device_id)
    
    sella_key = f'{Config.MODELS_SELLA_FOLDER}/{model_number}_1.csv'
    non_sella_key = f'{Config.MODELS_NONSELLA_FOLDER}/{model_number}_2.csv'
    
    return sella_key, non_sella_key


def get_local_model_paths(device_id, models_base_dir=None):
    """
    Get local file paths for model files
    
    Args:
        device_id: Device ID (e.g., "AGS-2001")
        models_base_dir: Base directory for models (defaults to Config.BASE_DIR/models)
    
    Returns:
        tuple: (sella_path, non_sella_path)
    
    Example:
        >>> sella_path, non_sella_path = get_local_model_paths("AGS-2001")
        >>> print(sella_path)
        '/path/to/models/2001_1.csv'
    """
    model_number = extract_model_number_from_device_id(device_id)
    
    if models_base_dir is None:
        models_base_dir = os.path.join(Config.BASE_DIR, 'models')
    
    sella_path = os.path.join(models_base_dir, f'{model_number}_1.csv')
    non_sella_path = os.path.join(models_base_dir, f'{model_number}_2.csv')
    
    return sella_path, non_sella_path


def verify_model_exists(device_id, check_s3=True):
    """
    Verify if model files exist (locally or on S3)
    
    Args:
        device_id: Device ID
        check_s3: If True, check S3; if False, only check local
    
    Returns:
        dict: Status for each model file
            {
                'sella_local': bool,
                'non_sella_local': bool,
                'sella_s3': bool (if check_s3=True),
                'non_sella_s3': bool (if check_s3=True)
            }
    """
    result = {}
    
    # Check local files
    sella_path, non_sella_path = get_local_model_paths(device_id)
    result['sella_local'] = os.path.exists(sella_path)
    result['non_sella_local'] = os.path.exists(non_sella_path)
    
    logger.info(f"Local model check for {device_id}:")
    logger.info(f"  Sella: {sella_path} - {'EXISTS' if result['sella_local'] else 'NOT FOUND'}")
    logger.info(f"  Non-Sella: {non_sella_path} - {'EXISTS' if result['non_sella_local'] else 'NOT FOUND'}")
    
    # Check S3 if requested
    if check_s3:
        sella_s3_key, non_sella_s3_key = get_model_s3_keys(device_id)
        result['sella_s3'] = object_exists(Config.S3_BUCKET_NAME, sella_s3_key)
        result['non_sella_s3'] = object_exists(Config.S3_BUCKET_NAME, non_sella_s3_key)
        
        logger.info(f"S3 model check for {device_id}:")
        logger.info(f"  Sella: {sella_s3_key} - {'EXISTS' if result['sella_s3'] else 'NOT FOUND'}")
        logger.info(f"  Non-Sella: {non_sella_s3_key} - {'EXISTS' if result['non_sella_s3'] else 'NOT FOUND'}")
    
    return result


def download_model_files(device_id, force_download=False):
    """
    Download model files from S3 for a specific device
    
    Args:
        device_id: Device ID (e.g., "AGS-2001")
        force_download: If True, download even if files exist locally
    
    Returns:
        tuple: (sella_path, non_sella_path) or (None, None) if error
    
    Raises:
        ValueError: If device ID format is invalid
        Exception: If model files don't exist on S3 or download fails
    
    Example:
        >>> sella_path, non_sella_path = download_model_files("AGS-2001")
        >>> print(f"Downloaded to: {sella_path}")
    """
    try:
        logger.info(f"Downloading model files for device: {device_id}")
        
        # Extract model number
        model_number = extract_model_number_from_device_id(device_id)
        logger.info(f"Extracted model number: {model_number}")
        
        # Get S3 keys and local paths
        sella_s3_key, non_sella_s3_key = get_model_s3_keys(device_id)
        sella_local_path, non_sella_local_path = get_local_model_paths(device_id)
        
        # Create models directory
        models_dir = os.path.dirname(sella_local_path)
        os.makedirs(models_dir, exist_ok=True)
        
        # Download Sella model
        if force_download or not os.path.exists(sella_local_path):
            logger.info(f"Downloading Sella model: {sella_s3_key}")
            if not object_exists(Config.S3_BUCKET_NAME, sella_s3_key):
                raise Exception(f"Sella model not found on S3: {sella_s3_key}")
            
            if not download_file(Config.S3_BUCKET_NAME, sella_s3_key, sella_local_path):
                raise Exception(f"Failed to download Sella model: {sella_s3_key}")
            
            logger.info(f"✅ Sella model downloaded: {sella_local_path}")
        else:
            logger.info(f"✅ Sella model already exists: {sella_local_path}")
        
        # Download Non-Sella model
        if force_download or not os.path.exists(non_sella_local_path):
            logger.info(f"Downloading Non-Sella model: {non_sella_s3_key}")
            if not object_exists(Config.S3_BUCKET_NAME, non_sella_s3_key):
                raise Exception(f"Non-Sella model not found on S3: {non_sella_s3_key}")
            
            if not download_file(Config.S3_BUCKET_NAME, non_sella_s3_key, non_sella_local_path):
                raise Exception(f"Failed to download Non-Sella model: {non_sella_s3_key}")
            
            logger.info(f"✅ Non-Sella model downloaded: {non_sella_local_path}")
        else:
            logger.info(f"✅ Non-Sella model already exists: {non_sella_local_path}")
        
        logger.info(f"✅ All model files ready for device {device_id}")
        return sella_local_path, non_sella_local_path
        
    except ValueError as e:
        logger.error(f"Invalid device ID format: {e}")
        raise
    except Exception as e:
        logger.error(f"Error downloading model files for {device_id}: {e}")
        raise


def get_available_models(check_s3=True):
    """
    Get list of available model numbers
    
    Args:
        check_s3: If True, check S3; if False, only check local
    
    Returns:
        dict: Available models
            {
                'local': ['2001', '2002', ...],
                's3': ['2001', '2002', ...] (if check_s3=True)
            }
    """
    result = {'local': []}
    
    # Check local models
    models_dir = os.path.join(Config.BASE_DIR, 'models')
    if os.path.exists(models_dir):
        files = os.listdir(models_dir)
        model_numbers = set()
        for file in files:
            match = re.match(r'(\d{4})_[12]\.csv', file)
            if match:
                model_numbers.add(match.group(1))
        result['local'] = sorted(list(model_numbers))
    
    logger.info(f"Found {len(result['local'])} model(s) locally: {result['local']}")
    
    # Check S3 if requested
    if check_s3:
        from .s3_client import list_objects
        
        result['s3'] = []
        model_numbers_s3 = set()
        
        # Check Sella folder
        sella_keys = list_objects(Config.S3_BUCKET_NAME, prefix=Config.MODELS_SELLA_FOLDER)
        for key in sella_keys:
            match = re.search(r'(\d{4})_1\.csv', key)
            if match:
                model_numbers_s3.add(match.group(1))
        
        # Check Non-Sella folder
        non_sella_keys = list_objects(Config.S3_BUCKET_NAME, prefix=Config.MODELS_NONSELLA_FOLDER)
        for key in non_sella_keys:
            match = re.search(r'(\d{4})_2\.csv', key)
            if match:
                model_numbers_s3.add(match.group(1))
        
        result['s3'] = sorted(list(model_numbers_s3))
        logger.info(f"Found {len(result['s3'])} model(s) on S3: {result['s3']}")
    
    return result