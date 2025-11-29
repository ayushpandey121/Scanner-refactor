# storage/s3_client.py
"""
S3 client wrapper for AWS operations
Provides basic S3 operations (upload, download, list)
"""

import boto3
import logging
from botocore.exceptions import ClientError
from config.settings import Config

logger = logging.getLogger(__name__)

# Singleton S3 client
_s3_client = None


def get_s3_client():
    """
    Get or create S3 client singleton
    
    Returns:
        boto3.client: S3 client instance
    """
    global _s3_client
    
    if _s3_client is None:
        _s3_client = boto3.client(
            's3',
            region_name=Config.AWS_REGION
        )
        logger.info(f"Initialized S3 client for region: {Config.AWS_REGION}")
    
    return _s3_client


def download_file(bucket_name, s3_key, local_path):
    """
    Download file from S3 to local path
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key (path in bucket)
        local_path: Local file path to save
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        >>> success = download_file(
        ...     'my-bucket',
        ...     'models/2001_1.csv',
        ...     '/local/models/2001_1.csv'
        ... )
    """
    try:
        s3_client = get_s3_client()
        s3_client.download_file(bucket_name, s3_key, local_path)
        logger.info(f"Downloaded {s3_key} from {bucket_name} to {local_path}")
        return True
    except ClientError as e:
        logger.error(f"Error downloading {s3_key} from S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {s3_key}: {e}")
        return False


def upload_file(local_path, bucket_name, s3_key, content_type=None):
    """
    Upload file from local path to S3
    
    Args:
        local_path: Local file path
        bucket_name: S3 bucket name
        s3_key: S3 object key (destination path in bucket)
        content_type: Optional content type (e.g., 'application/json')
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        >>> success = upload_file(
        ...     '/local/data.json',
        ...     'my-bucket',
        ...     'data/data.json',
        ...     content_type='application/json'
        ... )
    """
    try:
        s3_client = get_s3_client()
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        s3_client.upload_file(local_path, bucket_name, s3_key, ExtraArgs=extra_args)
        logger.info(f"Uploaded {local_path} to {bucket_name}/{s3_key}")
        return True
    except ClientError as e:
        logger.error(f"Error uploading {local_path} to S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading {local_path}: {e}")
        return False


def download_bytes(bucket_name, s3_key):
    """
    Download file from S3 as bytes
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key
    
    Returns:
        bytes: File content or None if error
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        content = response['Body'].read()
        logger.info(f"Downloaded {s3_key} from {bucket_name} as bytes")
        return content
    except ClientError as e:
        logger.error(f"Error downloading {s3_key} from S3: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading {s3_key}: {e}")
        return None


def upload_bytes(data, bucket_name, s3_key, content_type=None):
    """
    Upload bytes to S3
    
    Args:
        data: Bytes to upload
        bucket_name: S3 bucket name
        s3_key: S3 object key
        content_type: Optional content type
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        s3_client = get_s3_client()
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=data,
            **extra_args
        )
        logger.info(f"Uploaded bytes to {bucket_name}/{s3_key}")
        return True
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {e}")
        return False


def list_objects(bucket_name, prefix=''):
    """
    List objects in S3 bucket with optional prefix
    
    Args:
        bucket_name: S3 bucket name
        prefix: Optional key prefix to filter objects
    
    Returns:
        list: List of object keys, empty list if error
    
    Example:
        >>> files = list_objects('my-bucket', prefix='models/')
        >>> print(files)
        ['models/2001_1.csv', 'models/2001_2.csv']
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            logger.info(f"No objects found in {bucket_name} with prefix '{prefix}'")
            return []
        
        keys = [obj['Key'] for obj in response['Contents']]
        logger.info(f"Found {len(keys)} objects in {bucket_name} with prefix '{prefix}'")
        return keys
    except ClientError as e:
        logger.error(f"Error listing objects in S3: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error listing objects: {e}")
        return []


def object_exists(bucket_name, s3_key):
    """
    Check if object exists in S3
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key
    
    Returns:
        bool: True if exists, False otherwise
    """
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        logger.error(f"Error checking if {s3_key} exists: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking object existence: {e}")
        return False


def get_object_metadata(bucket_name, s3_key):
    """
    Get object metadata from S3
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key
    
    Returns:
        dict: Metadata dictionary or None if error
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return {
            'size': response.get('ContentLength'),
            'last_modified': response.get('LastModified'),
            'content_type': response.get('ContentType'),
            'etag': response.get('ETag')
        }
    except ClientError as e:
        logger.error(f"Error getting metadata for {s3_key}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting metadata: {e}")
        return None