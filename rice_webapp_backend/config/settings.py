# config/settings.py
"""
Application settings and configuration
Environment-specific settings, paths, and AWS configuration
"""

import os
import sys

class Config:
    """Application configuration"""
    
    # ========================================================================
    # SERVER CONFIGURATION
    # ========================================================================
    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG = True
    
    # ========================================================================
    # STORAGE CONFIGURATION
    # ========================================================================
    # For packaged apps, use a writable user data directory
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        if sys.platform == 'win32':
            DEFAULT_BASE_DIR = os.path.join(
                os.environ.get('APPDATA', os.path.expanduser('~')), 
                'AgSure'
            )
        elif sys.platform == 'darwin':
            DEFAULT_BASE_DIR = os.path.join(
                os.path.expanduser('~'), 
                'Library', 
                'Application Support', 
                'AgSure'
            )
        else:
            DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), '.agsure')
    else:
        # Running in development
        DEFAULT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    BASE_DIR = os.environ.get("AGSURE_DATA_DIR", DEFAULT_BASE_DIR)
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')
    
    # Storage folders
    UPLOAD_FOLDER = os.path.join(STATIC_ROOT, 'uploads')
    RESULT_FOLDER = os.path.join(STATIC_ROOT, 'results')
    GRAIN_FOLDER = os.path.join(STATIC_ROOT, 'grains')
    LOG_FOLDER = os.path.join(STATIC_ROOT, 'logs')
    EXCEL_FOLDER = os.path.join(STATIC_ROOT, 'excels')
    CROPPED_FOLDER = os.path.join(STATIC_ROOT, 'cropped')
    
    # Configuration files
    VARIETIES_FILE = os.path.join(STATIC_ROOT, 'varieties.json')
    
    # ========================================================================
    # CORS CONFIGURATION
    # ========================================================================
    CORS_ORIGINS = ["*"]
    
    # ========================================================================
    # AWS S3 CONFIGURATION
    # ========================================================================
    AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "agsurescanner")
    PRODUCT_KEYS_KEY = "product_keys/product_keys.json"
    
    # S3 model folders
    MODELS_SELLA_FOLDER = "models_sella"
    MODELS_NONSELLA_FOLDER = "models_nonsella"
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @classmethod
    def get_all_folders(cls):
        """
        Get list of all storage folders
        
        Returns:
            list: List of folder paths
        """
        return [
            cls.UPLOAD_FOLDER,
            cls.RESULT_FOLDER,
            cls.GRAIN_FOLDER,
            cls.LOG_FOLDER,
            cls.EXCEL_FOLDER,
            cls.CROPPED_FOLDER
        ]
    
    @classmethod
    def create_directories(cls):
        """
        Create all necessary directories
        Also initializes varieties.json if it doesn't exist
        """
        # Ensure base directory exists
        os.makedirs(cls.BASE_DIR, exist_ok=True)
        os.makedirs(cls.STATIC_ROOT, exist_ok=True)
        
        # Create storage folders
        for folder in cls.get_all_folders():
            os.makedirs(folder, exist_ok=True)
        
        # Create models directory
        models_folder = os.path.join(cls.BASE_DIR, 'models')
        os.makedirs(models_folder, exist_ok=True)
        
        # Initialize varieties.json if it doesn't exist
        cls.initialize_varieties_file()
    
    @classmethod
    def initialize_varieties_file(cls):
        """Create varieties.json if it doesn't exist"""
        if not os.path.exists(cls.VARIETIES_FILE):
            try:
                import json
                with open(cls.VARIETIES_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"varieties": []}, f, indent=2, ensure_ascii=False)
                print(f"Initialized varieties file at: {cls.VARIETIES_FILE}")
            except Exception as e:
                print(f"Error initializing varieties file: {e}")