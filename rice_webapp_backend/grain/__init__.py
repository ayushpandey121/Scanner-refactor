# rice_webapp_backend/grain/__init__.py
from .measurements import GrainMeasurements
from .processor import GrainProcessor
# Import ImageProcessor to expose extraction logic if needed by analysis.py
from preprocessing.image_processor import ImageProcessor 

def extract_grains(image, base_name, pixels_per_metric):
    """Wrapper for ImageProcessor.extract_all_grains (used by analysis.py)"""
    return ImageProcessor.extract_all_grains(image, base_name, pixels_per_metric)

def calculate_grain_measurements(grain_path, pixels_per_metric):
    """Wrapper for GrainMeasurements.calculate_length_breadth"""
    return GrainMeasurements.calculate_length_breadth(grain_path, pixels_per_metric)

__all__ = [
    'GrainMeasurements',
    'GrainProcessor',
    'extract_grains',
    'calculate_grain_measurements'
]