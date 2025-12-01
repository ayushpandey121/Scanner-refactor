# rice_webapp_backend/preprocessing/__init__.py
from .image_processor import ImageProcessor

def decode_and_crop_image(image_path):
    """Wrapper for ImageProcessor.decode_and_crop_image"""
    return ImageProcessor.decode_and_crop_image(image_path)

def calculate_pixels_per_metric(image=None):
    """
    Wrapper for ImageProcessor.get_pixels_per_metric
    Returns (ppm, None) tuple as expected by analysis routes
    """
    return ImageProcessor.get_pixels_per_metric(), None

__all__ = [
    'ImageProcessor',
    'decode_and_crop_image',
    'calculate_pixels_per_metric'
]