# grain/processor.py
"""
Orchestrates complete grain-level processing workflow
"""
import os
import cv2
import logging
from grain.measurements import GrainMeasurements
from defects.chalky import ChalkyDetector
from defects.discolor import DiscolorDetector
from defects.broken import BrokenDetector

logger = logging.getLogger(__name__)


class GrainProcessor:
    """Orchestrates all grain-level processing"""
    
    @staticmethod
    def process_single_grain(
        grain_path, 
        pixels_per_metric, 
        grain_coordinates=None,
        minlen=5.0, 
        chalky_percentage=30.0, 
        exclude_grain=False
    ):
        """
        Complete grain analysis pipeline
        
        Returns:
            dict: Complete grain data with measurements and defects
        """
        if exclude_grain:
            logger.info(f"Skipping excluded grain: {grain_path}")
            return None
        
        try:
            # Stage 1: Measurements
            measurements = GrainMeasurements.calculate_length_breadth(
                grain_path, pixels_per_metric, exclude_grain
            )
            
            if not measurements:
                return None
            
            # Load image for defect detection
            grain_image = cv2.imread(grain_path)
            
            # Stage 2: Defect Detection
            chalky_result = ChalkyDetector.detect(grain_image, chalky_percentage)
            discolor_result = DiscolorDetector.detect(grain_image)
            is_broken = BrokenDetector.is_broken(measurements['length'], minlen)
            
            # Combine results
            grain_data = {
                "id": os.path.splitext(os.path.basename(grain_path))[0],
                "length": measurements['length'],
                "width": measurements['breadth'],
                "R": measurements['R'],
                "G": measurements['G'],
                "B": measurements['B'],
                "grain_coordinates": grain_coordinates or [],
                "grain_url": None,  # Will be set later
                "chalky": chalky_result['chalky'],
                "chalky_count": chalky_result['chalky_count'],
                "discolor": discolor_result['discolor_class'],
                "broken": is_broken
            }
            
            return grain_data
        
        except Exception as e:
            logger.error(f"Error processing grain {grain_path}: {str(e)}")
            return None
    
    @staticmethod
    def process_batch(
        grain_paths, 
        pixels_per_metric,
        minlen=5.0,
        chalky_percentage=30.0,
        exclude_flags=None
    ):
        """
        Process multiple grains in batch
        
        Returns:
            list: List of grain data dictionaries
        """
        if exclude_flags is None:
            exclude_flags = [False] * len(grain_paths)
        
        results = []
        for grain_path, exclude_flag in zip(grain_paths, exclude_flags):
            result = GrainProcessor.process_single_grain(
                grain_path,
                pixels_per_metric,
                minlen=minlen,
                chalky_percentage=chalky_percentage,
                exclude_grain=exclude_flag
            )
            
            if result:
                results.append(result)
        
        logger.info(f"Processed {len(results)} grains successfully")
        return results