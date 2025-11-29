import boto3
import json
import logging
import os
import re
from botocore.exceptions import ClientError
from config import Config

logger = logging.getLogger(__name__)

def get_s3_client():
    """Get S3 client with configured credentials"""
    return boto3.client(
        's3',
        region_name=Config.AWS_REGION
    )

def download_json_from_s3(bucket_name, key):
    """
    Download JSON file from S3

    Args:
        bucket_name: S3 bucket name
        key: S3 object key

    Returns:
        dict: Parsed JSON data
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        json_data = response['Body'].read().decode('utf-8')
        return json.loads(json_data)
    except ClientError as e:
        logger.error(f"Error downloading {key} from S3: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from {key}: {e}")
        raise

def upload_json_to_s3(bucket_name, key, data):
    """
    Upload JSON data to S3

    Args:
        bucket_name: S3 bucket name
        key: S3 object key
        data: dict to upload
    """
    try:
        s3_client = get_s3_client()
        json_data = json.dumps(data, indent=2)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json_data,
            ContentType='application/json'
        )
        logger.info(f"Successfully uploaded {key} to S3")
    except ClientError as e:
        logger.error(f"Error uploading {key} to S3: {e}")
        raise

def download_csv_from_s3(bucket_name, key, local_path):
    """
    Download CSV file from S3 to local path

    Args:
        bucket_name: S3 bucket name
        key: S3 object key
        local_path: Local file path to save
    """
    try:
        s3_client = get_s3_client()
        s3_client.download_file(bucket_name, key, local_path)
        logger.info(f"Successfully downloaded {key} to {local_path}")
    except ClientError as e:
        logger.error(f"Error downloading {key} from S3: {e}")
        raise

def get_s3_object(bucket_name, key):
    """
    Get S3 object (for streaming)
    
    Args:
        bucket_name: S3 bucket name
        key: S3 object key
    
    Returns:
        S3 response object with Body stream
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response
    except ClientError as e:
        logger.error(f"Error getting object {key} from S3: {e}")
        raise

def extract_model_number_from_device_id(device_id):
    """
    Extract model number from device ID
    Example: AGS-2001 -> 2001, AGS-2002 -> 2002

    Args:
        device_id: Device ID string (e.g., "AGS-2001")

    Returns:
        str: Model number (e.g., "2001")
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

def download_model_files_by_device_id(device_id):
    """
    Download model files from S3 based on device ID
    
    Args:
        device_id: Device ID (e.g., "AGS-2001", "AGS-2002")
    
    Returns:
        tuple: (sella_path, non_sella_path) - paths to downloaded files
    
    Raises:
        ValueError: If device ID format is invalid
        ClientError: If files don't exist on S3
    """
    try:
        # Extract model number from device ID
        model_number = extract_model_number_from_device_id(device_id)
        logger.info(f"Extracted model number {model_number} from device ID {device_id}")
        
        # Create models directory
        models_folder = os.path.join(Config.BASE_DIR, 'models')
        os.makedirs(models_folder, exist_ok=True)
        
        # Define S3 keys and local paths for sella and non-sella models
        sella_s3_key = f'models_sella/{model_number}_1.csv'
        non_sella_s3_key = f'models_nonsella/{model_number}_2.csv'
        
        sella_local_path = os.path.join(models_folder, f'{model_number}_1.csv')
        non_sella_local_path = os.path.join(models_folder, f'{model_number}_2.csv')
        
        # Download sella model
        logger.info(f"Downloading Sella model from {sella_s3_key}")
        download_csv_from_s3(Config.S3_BUCKET_NAME, sella_s3_key, sella_local_path)
        
        # Download non-sella model
        logger.info(f"Downloading Non-Sella model from {non_sella_s3_key}")
        download_csv_from_s3(Config.S3_BUCKET_NAME, non_sella_s3_key, non_sella_local_path)
        
        logger.info(f"Successfully downloaded model files for device {device_id}")
        logger.info(f"  Sella: {sella_local_path}")
        logger.info(f"  Non-Sella: {non_sella_local_path}")
        
        return sella_local_path, non_sella_local_path
        
    except ValueError as e:
        logger.error(f"Invalid device ID format: {e}")
        raise
    except ClientError as e:
        logger.error(f"Model files not found on S3 for device {device_id}: {e}")
        raise Exception(f"Model files for device {device_id} not found on S3")
    except Exception as e:
        logger.error(f"Error downloading model files for device {device_id}: {e}")
        raise

def verify_license_key(license_key):
    """
    Verify if the license key is valid by checking against product_keys.json on S3

    Args:
        license_key: The license key to verify

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        bucket_name = Config.S3_BUCKET_NAME
        key = 'product_keys/product_keys.json'
        keys_data = download_json_from_s3(bucket_name, key)
        # Check if the key exists in activations
        activations = keys_data.get('activations', {})
        return license_key in activations
    except Exception as e:
        logger.error(f"Error verifying license key: {e}")
        return False

def get_device_id_from_license_key(license_key):
    """
    Get device ID associated with a license key
    
    Args:
        license_key: The license key to lookup
    
    Returns:
        str: Device ID or None if not found
    """
    try:
        bucket_name = Config.S3_BUCKET_NAME
        key = 'product_keys/product_keys.json'
        keys_data = download_json_from_s3(bucket_name, key)
        activations = keys_data.get('activations', {})
        
        if license_key in activations:
            return activations[license_key].get('deviceId')
        
        return None
    except Exception as e:
        logger.error(f"Error getting device ID from license key: {e}")
        return None