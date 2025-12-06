# storage/local_storage.py
"""
Local file storage operations
Handles saving/loading files to local directories
"""

import os
import json
import shutil
import logging
import cv2
from config.settings import Config

logger = logging.getLogger(__name__)


def ensure_directories():
    """
    Create all necessary storage directories
    
    Creates:
        - BASE_DIR
        - STATIC_ROOT
        - UPLOAD_FOLDER
        - RESULT_FOLDER
        - GRAIN_FOLDER
        - LOG_FOLDER
        - EXCEL_FOLDER
        - CROPPED_FOLDER
        - models/
    """
    try:
        # Create base directories
        os.makedirs(Config.BASE_DIR, exist_ok=True)
        os.makedirs(Config.STATIC_ROOT, exist_ok=True)
        
        # Create all storage folders
        for folder in Config.get_all_folders():
            os.makedirs(folder, exist_ok=True)
        
        # Create models directory
        models_folder = os.path.join(Config.BASE_DIR, 'models')
        os.makedirs(models_folder, exist_ok=True)
        
        logger.info("All storage directories created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating directories: {e}")
        return False


def save_image(image, filepath):
    """
    Save image (numpy array or path) to specified location
    
    Args:
        image: Image array (numpy) or source file path
        filepath: Destination file path
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        >>> import cv2
        >>> img = cv2.imread('input.jpg')
        >>> save_image(img, '/path/to/output.jpg')
        True
    """
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if isinstance(image, str):
            # If image is a file path, copy it
            shutil.copy(image, filepath)
        else:
            # If image is numpy array, write it
            cv2.imwrite(filepath, image)
        
        logger.debug(f"Image saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving image to {filepath}: {e}")
        return False


def save_json(data, filepath):
    """
    Save dictionary as JSON file
    
    Args:
        data: Dictionary to save
        filepath: Destination file path
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"JSON saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {filepath}: {e}")
        return False


def load_json(filepath):
    """
    Load JSON file
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        dict: Loaded data or None if error
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"JSON loaded: {filepath}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON from {filepath}: {e}")
        return None


def save_excel(dataframe, filepath):
    """
    Save pandas DataFrame as Excel file
    
    Args:
        dataframe: Pandas DataFrame
        filepath: Destination file path
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        dataframe.to_excel(filepath, index=False)
        logger.debug(f"Excel saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving Excel to {filepath}: {e}")
        return False


class LocalStorage:
    """
    Helper class for organized local file storage operations
    """
    
    @staticmethod
    def save_upload(file_or_path, filename):
        """
        Save uploaded file
        
        Args:
            file_or_path: File object (Flask) or source path
            filename: Filename to save as
        
        Returns:
            str: Full path to saved file or None if error
        """
        try:
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            if hasattr(file_or_path, 'save'):
                # Flask file object
                file_or_path.save(filepath)
            else:
                # File path
                shutil.copy(file_or_path, filepath)
            
            # logger.info(f"Upload saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving upload: {e}")
            return None
    
    @staticmethod
    def save_cropped(image, filename):
        """Save cropped image"""
        filepath = os.path.join(Config.CROPPED_FOLDER, filename)
        if save_image(image, filepath):
            # logger.info(f"Cropped image saved: {filepath}")
            return filepath
        return None
    
    @staticmethod
    def save_result(image, filename):
        """Save result image"""
        filepath = os.path.join(Config.RESULT_FOLDER, filename)
        if save_image(image, filepath):
            logger.info(f"Result image saved: {filepath}")
            return filepath
        return None
    
    @staticmethod
    def save_grain(image_or_path, base_name, filename):
        """
        Save grain image to organized folder
        
        Args:
            image_or_path: Image array or source path
            base_name: Base name for folder organization
            filename: Grain filename
        
        Returns:
            str: Relative path for URL (base_name/filename) or None if error
        """
        try:
            grain_folder = os.path.join(Config.GRAIN_FOLDER, base_name)
            os.makedirs(grain_folder, exist_ok=True)
            
            filepath = os.path.join(grain_folder, filename)
            
            if save_image(image_or_path, filepath):
                # logger.info(f"Grain image saved: {filepath}")
                return f"{base_name}/{filename}"
            return None
        except Exception as e:
            logger.error(f"Error saving grain image: {e}")
            return None
    
    @staticmethod
    def save_log(data, filename):
        """Save analysis log"""
        filepath = os.path.join(Config.LOG_FOLDER, filename)
        if save_json(data, filepath):
            logger.info(f"Log saved: {filepath}")
            return filepath
        return None
    
    @staticmethod
    def save_excel_file(dataframe, filename):
        """Save Excel file"""
        filepath = os.path.join(Config.EXCEL_FOLDER, filename)
        if save_excel(dataframe, filepath):
            logger.info(f"Excel saved: {filepath}")
            return filepath
        return None
    
    @staticmethod
    def get_url(folder_type, filename):
        """
        Generate URL path for stored file
        
        Args:
            folder_type: 'upload', 'result', 'grain', 'excel', 'cropped', 'log'
            filename: Filename or relative path
        
        Returns:
            str: URL path
        
        Example:
            >>> LocalStorage.get_url('grain', 'sample_001/grain_001.jpg')
            '/grain-image/sample_001/grain_001.jpg'
        """
        folder_map = {
            'upload': '/upload',
            'result': '/result-image',
            'grain': '/grain-image',
            'excel': '/excel',
            'cropped': '/cropped-image',
            'log': '/logs'
        }
        
        base_path = folder_map.get(folder_type, '')
        return f"{base_path}/{filename}"
    
    @staticmethod
    def list_files(folder_type, extension=None):
        """
        List files in a storage folder
        
        Args:
            folder_type: 'upload', 'result', 'grain', 'excel', 'cropped', 'log'
            extension: Optional file extension filter (e.g., '.jpg', '.json')
        
        Returns:
            list: List of filenames
        """
        folder_map = {
            'upload': Config.UPLOAD_FOLDER,
            'result': Config.RESULT_FOLDER,
            'grain': Config.GRAIN_FOLDER,
            'excel': Config.EXCEL_FOLDER,
            'cropped': Config.CROPPED_FOLDER,
            'log': Config.LOG_FOLDER
        }
        
        folder = folder_map.get(folder_type)
        if not folder or not os.path.exists(folder):
            return []
        
        files = os.listdir(folder)
        
        if extension:
            files = [f for f in files if f.endswith(extension)]
        
        return sorted(files)
    
    @staticmethod
    def delete_file(folder_type, filename):
        """
        Delete file from storage
        
        Args:
            folder_type: Storage folder type
            filename: File to delete
        
        Returns:
            bool: True if successful, False otherwise
        """
        folder_map = {
            'upload': Config.UPLOAD_FOLDER,
            'result': Config.RESULT_FOLDER,
            'grain': Config.GRAIN_FOLDER,
            'excel': Config.EXCEL_FOLDER,
            'cropped': Config.CROPPED_FOLDER,
            'log': Config.LOG_FOLDER
        }
        
        folder = folder_map.get(folder_type)
        if not folder:
            return False
        
        filepath = os.path.join(folder, filename)
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted file: {filepath}")
                return True
            else:
                logger.warning(f"File not found: {filepath}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {filepath}: {e}")
            return False
    
    @staticmethod
    def clear_folder(folder_type):
        """
        Clear all files from a storage folder
        
        Args:
            folder_type: Storage folder type
        
        Returns:
            int: Number of files deleted
        """
        folder_map = {
            'upload': Config.UPLOAD_FOLDER,
            'result': Config.RESULT_FOLDER,
            'grain': Config.GRAIN_FOLDER,
            'excel': Config.EXCEL_FOLDER,
            'cropped': Config.CROPPED_FOLDER,
            'log': Config.LOG_FOLDER
        }
        
        folder = folder_map.get(folder_type)
        if not folder or not os.path.exists(folder):
            return 0
        
        deleted = 0
        try:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    deleted += 1
            
            logger.info(f"Cleared {deleted} files from {folder_type}")
            return deleted
        except Exception as e:
            logger.error(f"Error clearing folder {folder_type}: {e}")
            return deleted


# Convenience functions
def save_uploaded_file(file_or_path, filename):
    """Convenience function for saving uploaded files"""
    return LocalStorage.save_upload(file_or_path, filename)


def save_result_image(image, filename):
    """Convenience function for saving result images"""
    return LocalStorage.save_result(image, filename)


def save_grain_image(image_or_path, base_name, filename):
    """Convenience function for saving grain images"""
    return LocalStorage.save_grain(image_or_path, base_name, filename)