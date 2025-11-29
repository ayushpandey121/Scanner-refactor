# services/storage_service.py
import os
import json
import logging
import shutil
from config import Config

logger = logging.getLogger(__name__)


class StorageService:
    """Handle all file storage operations"""
    
    @staticmethod
    def save_uploaded_file(file, filename):
        """
        Save uploaded file to storage
        
        Args:
            file: File object or path
            filename: Name for the saved file
        
        Returns:
            str: Path to saved file
        """
        try:
            save_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            if hasattr(file, 'save'):
                # File from Flask request
                file.save(save_path)
            else:
                # File path
                shutil.copy(file, save_path)
            
            logger.info(f"Uploaded file saved: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            raise
    
    @staticmethod
    def save_cropped_image(image, filename):
        """
        Save cropped image
        
        Args:
            image: Image array
            filename: Name for the saved file
        
        Returns:
            str: Path to saved file
        """
        import cv2
        try:
            save_path = os.path.join(Config.CROPPED_FOLDER, filename)
            cv2.imwrite(save_path, image)
            logger.info(f"Cropped image saved: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Error saving cropped image: {str(e)}")
            raise
    
    @staticmethod
    def save_result_image(image, filename):
        """
        Save result image
        
        Args:
            image: Image array
            filename: Name for the saved file
        
        Returns:
            str: Path to saved file
        """
        import cv2
        try:
            save_path = os.path.join(Config.RESULT_FOLDER, filename)
            cv2.imwrite(save_path, image)
            logger.info(f"Result image saved: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Error saving result image: {str(e)}")
            raise
    
    @staticmethod
    def save_grain_image(image_path, base_name, filename):
        """
        Save grain image to organized folder
        
        Args:
            image_path: Source image path
            base_name: Base name for folder organization
            filename: Name for the saved file
        
        Returns:
            str: Relative path for URL
        """
        try:
            grain_folder = os.path.join(Config.GRAIN_FOLDER, base_name)
            os.makedirs(grain_folder, exist_ok=True)
            
            save_path = os.path.join(grain_folder, filename)
            shutil.copy(image_path, save_path)
            
            logger.info(f"Grain image saved: {save_path}")
            return f"{base_name}/{filename}"
        except Exception as e:
            logger.error(f"Error saving grain image: {str(e)}")
            raise
    
    @staticmethod
    def save_excel(dataframe, filename):
        """
        Save DataFrame to Excel file
        
        Args:
            dataframe: Pandas DataFrame
            filename: Name for the saved file
        
        Returns:
            str: Relative path for URL
        """
        try:
            save_path = os.path.join(Config.EXCEL_FOLDER, filename)
            dataframe.to_excel(save_path, index=False)
            logger.info(f"Excel file saved: {save_path}")
            return filename
        except Exception as e:
            logger.error(f"Error saving Excel file: {str(e)}")
            raise
    
    @staticmethod
    def save_log(log_data, filename):
        """
        Save log data as JSON
        
        Args:
            log_data: Dictionary to save
            filename: Name for the saved file
        
        Returns:
            str: Path to saved file
        """
        try:
            save_path = os.path.join(Config.LOG_FOLDER, filename)
            with open(save_path, 'w') as f:
                json.dump(log_data, f, indent=2)
            logger.info(f"Log file saved: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Error saving log file: {str(e)}")
            raise
    
    @staticmethod
    def get_url(folder, filename):
        """
        Generate URL for stored file
        
        Args:
            folder: Folder type ('upload', 'result', 'grain', 'excel', 'cropped')
            filename: File name
        
        Returns:
            str: URL path
        """
        folder_map = {
            'upload': '/upload',
            'result': '/result-image',
            'grain': '/grain-image',
            'excel': '/excel',
            'cropped': '/cropped-image'
        }
        
        base_path = folder_map.get(folder, '')
        return f"{base_path}/{filename}"