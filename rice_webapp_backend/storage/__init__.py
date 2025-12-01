# rice_webapp_backend/storage/__init__.py
"""
Storage module for file operations (S3 and local)
Handles model files, activation data, and local file storage
"""

from .s3_client import get_s3_client, download_file, upload_file
from .s3_models import (
    download_model_files,
    verify_model_exists,
    get_model_s3_keys
)
from .s3_activation import (
    get_activation_data,
    update_activation_data,
    get_device_id_from_s3,
    is_key_expired,
    # Add these missing imports:
    get_activation_by_key,
    get_activation_by_hardware_id,
    update_login_status
)
from .local_storage import (
    LocalStorage,
    save_image,
    save_json,
    save_excel,
    ensure_directories
)

__all__ = [
    # S3 Client
    'get_s3_client',
    'download_file',
    'upload_file',
    # S3 Models
    'download_model_files',
    'verify_model_exists',
    'get_model_s3_keys',
    # S3 Activation
    'get_activation_data',
    'update_activation_data',
    'get_device_id_from_s3',
    'is_key_expired',
    # Add these to __all__:
    'get_activation_by_key',
    'get_activation_by_hardware_id',
    'update_login_status',
    # Local Storage
    'LocalStorage',
    'save_image',
    'save_json',
    'save_excel',
    'ensure_directories'
]