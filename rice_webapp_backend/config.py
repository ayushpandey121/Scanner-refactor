# config.py
import os
import json
import sys

class Config:
    """Application configuration"""
    
    # Server Configuration
    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG = True
    
    # Storage Configuration
    # For packaged apps, use a writable user data directory
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        if sys.platform == 'win32':
            DEFAULT_BASE_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AgSure')
        elif sys.platform == 'darwin':
            DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'AgSure')
        else:
            DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), '.agsure')
    else:
        # Running in development
        DEFAULT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    BASE_DIR = os.environ.get("AGSURE_DATA_DIR", DEFAULT_BASE_DIR)
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')
    UPLOAD_FOLDER = os.path.join(STATIC_ROOT, 'uploads')
    RESULT_FOLDER = os.path.join(STATIC_ROOT, 'results')
    GRAIN_FOLDER = os.path.join(STATIC_ROOT, 'grains')
    LOG_FOLDER = os.path.join(STATIC_ROOT, 'logs')
    EXCEL_FOLDER = os.path.join(STATIC_ROOT, 'excels')
    CROPPED_FOLDER = os.path.join(STATIC_ROOT, 'cropped')
    VARIETIES_FILE = os.path.join(STATIC_ROOT, 'varieties.json')
    
    # Image Processing Constants
    BORDER_CROP_COORDINATES = (650, 50, 3950, 3350)
    STRIP_WIDTH = 9.98
    MINIMUM_PPM = 15.5
    MAXIMUM_PPM = 25.5
    MIN_CONTOUR_AREA = 500
    HARDCODED_PPM = 15.53
    DEFAULT_CHALKY_PERCENTAGE = 30.0
    DEFAULT_MIN_LENGTH = 5.0
    
    # CORS Configuration
    CORS_ORIGINS = ["*"]

    # AWS S3 Configuration
    AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "agsurescanner")
    PRODUCT_KEYS_KEY = "product_keys/product_keys.json"
    
    MODELS_SELLA_FOLDER = "models_sella"
    MODELS_NONSELLA_FOLDER = "models_nonsella"
    
    # Sample Type Thresholds
    SAMPLE_TYPE_THRESHOLDS = {
        "Brown": {"min_r": 162, "max_b": 145},
        "Mixed": {"min_r": 145, "min_b": 130, "min_rb_gap": 13},
        "Yellow": {"max_r": 143, "max_b": 125},
        "White": {"min_r": 140, "min_b": 126, "max_rb_gap": 12}
    }
    
    # Discoloration Thresholds by Sample Type
    DISCOLORATION_THRESHOLDS = {
        "White": 15,
        "Mixed": 21,
        "Brown": 26.5,
        "Yellow": 28,
    }
    
    @classmethod
    def get_all_folders(cls):
        """Get list of all storage folders"""
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
        """Create all necessary directories"""
        # Ensure base directory exists
        os.makedirs(cls.BASE_DIR, exist_ok=True)
        os.makedirs(cls.STATIC_ROOT, exist_ok=True)
        
        for folder in cls.get_all_folders():
            os.makedirs(folder, exist_ok=True)
        
        # Also create models directory
        models_folder = os.path.join(cls.BASE_DIR, 'models')
        os.makedirs(models_folder, exist_ok=True)
        
        # Initialize varieties.json if it doesn't exist
        cls.initialize_varieties_file()
    
    @classmethod
    def initialize_varieties_file(cls):
        """Create varieties.json if it doesn't exist"""
        if not os.path.exists(cls.VARIETIES_FILE):
            try:
                with open(cls.VARIETIES_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"varieties": []}, f, indent=2, ensure_ascii=False)
                print(f"Initialized varieties file at: {cls.VARIETIES_FILE}")
            except Exception as e:
                print(f"Error initializing varieties file: {e}")