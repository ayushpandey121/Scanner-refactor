# utils/image_utils.py
import cv2
import numpy as np
import logging
from config import Config

logger = logging.getLogger(__name__)


def decode_and_crop_image(image_path, crop_coords=None):
    """
    Decode image without cropping - returns full image
    
    Args:
        image_path: Path to the image file
        crop_coords: Ignored parameter (kept for backward compatibility)
    
    Returns:
        Full image or None if failed
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error("Failed to decode image")
            return None

        height, width = img.shape[:2]
        logger.info(f"Image dimensions: {width}x{height}")
        logger.info(f"Using full image without cropping")
        
        return img

    except Exception as e:
        logger.error(f"Error in decode_and_crop_image: {str(e)}")
        return None


def calculate_pixels_per_metric(cropped_img):
    """
    Returns hardcoded PPM value only
    
    Args:
        cropped_img: Image array (not used, kept for backward compatibility)
    
    Returns:
        Tuple of (pixels_per_metric, strip_contour)
    """
    logger.info(f"Using hardcoded PPM: {Config.HARDCODED_PPM}")
    return Config.HARDCODED_PPM, None


def save_image(image, path):
    """
    Save image to specified path
    
    Args:
        image: Image array to save
        path: Destination path
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cv2.imwrite(path, image)
        logger.info(f"Image saved successfully: {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving image to {path}: {str(e)}")
        return False