# services/grain_service.py
import os
import cv2
import logging
import numpy as np
from preprocessing import (
    process_image_stage1,
    process_image_stage2,
    correct_and_save_orientation
)
from rice_quality_utils import RiceQualityAnalysis
from utils.metrics import classify_discoloration, calculate_br_statistics
from config import Config

logger = logging.getLogger(__name__)


class GrainService:
    """Handle grain extraction and analysis"""
    
    @staticmethod
    def extract_grains(cropped_image, image_name, pixels_per_metric, strip_contour=None):
        """
        Extract individual grains from image (no strip filtering)
        
        Args:
            cropped_image: Image array
            image_name: Name of the image
            pixels_per_metric: Pixels per metric value (always hardcoded 15.62)
            strip_contour: Ignored parameter (kept for backward compatibility)
        
        Returns:
            Tuple of (masked_padded_images, grain_info_list, result_image)
        """
        try:
            logger.info(f"Extracting grains from: {image_name} with PPM: {pixels_per_metric}")

            masked_padded_images = process_image_stage1(cropped_image, image_name, pixels_per_metric)

            # No strip filtering - use all extracted grains
            grain_info_list = []
            result_image = cropped_image.copy()

            # Handle the new 4-element tuple: (padded_image, filename, bbox, exclude_grain)
            for item in masked_padded_images:
                if len(item) == 4:
                    padded_image, filename, bbox, exclude_grain = item
                else:
                    # Backward compatibility
                    padded_image, filename, bbox = item
                    exclude_grain = False

                grain_info_list.append({
                    'filename': filename,
                    'bbox': bbox,
                    'exclude_grain': exclude_grain
                })

                x, y, w, h = bbox
                # Use different colors for visualization
                color = (0, 0, 255) if exclude_grain else (0, 255, 0)  # Red for excluded, green for included
                cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)

            included_count = sum(1 for g in grain_info_list if not g['exclude_grain'])
            excluded_count = len(grain_info_list) - included_count
            logger.info(f"Found {len(masked_padded_images)} grains ({included_count} included, {excluded_count} excluded)")
            
            return masked_padded_images, grain_info_list, result_image

        except Exception as e:
            logger.error(f"Error in grain extraction: {str(e)}")
            return [], [], cropped_image
    
    @staticmethod
    def analyze_grain(grain_path, pixels_per_metric, grain_coordinates=None, 
                     minlen=None, chalky_percentage=None, exclude_grain=False):
        """
        Analyze single grain for quality parameters
        NOTE: This method does NOT perform discoloration classification.
        Use process_grain_with_classification() for complete analysis.
        
        Args:
            grain_path: Path to grain image
            pixels_per_metric: Pixels per metric value (always hardcoded 15.62)
            grain_coordinates: Coordinates of grain in original image
            minlen: Minimum length threshold for broken detection
            chalky_percentage: Chalky percentage threshold
            exclude_grain: If True, skip this grain
        
        Returns:
            Tuple of (grain_data, oriented_path, feature_dict)
        """
        # Skip excluded grains
        if exclude_grain:
            logger.info(f"Skipping excluded grain: {os.path.basename(grain_path)}")
            return None, None, None
        
        if minlen is None:
            minlen = Config.DEFAULT_MIN_LENGTH
        if chalky_percentage is None:
            chalky_percentage = Config.DEFAULT_CHALKY_PERCENTAGE
        if grain_coordinates is None:
            grain_coordinates = []
        
        try:
            # Run Stage2 processing for accurate features (with exclude_grain flag)
            feature_dict = process_image_stage2(grain_path, pixels_per_metric, exclude_grain)
            if not feature_dict:
                return None, None, None

            # Create oriented image
            oriented_path = os.path.join(
                os.path.dirname(grain_path),
                "oriented",
                os.path.basename(grain_path)
            )
            os.makedirs(os.path.dirname(oriented_path), exist_ok=True)
            correct_and_save_orientation(grain_path, oriented_path)

            # Quality analysis on the padded grain image
            grain_image = cv2.imread(grain_path)

            # Keep old discolor detection for backward compatibility
            # but it will be overridden by RGB-based classification
            discolor_result = RiceQualityAnalysis.find_discolor(grain_image)
            
            # Use custom chalky_percentage parameter
            chalky_count, chalky_indices = RiceQualityAnalysis.find_chalkiness(
                grain_image, percent=chalky_percentage
            )
            chalky_result = "Yes" if chalky_indices else "No"

            # Use Stage 2 length and breadth (more accurate)
            length = feature_dict.get('length', 0.0)
            width = feature_dict.get('breadth', 0.0)
            is_broken = length < minlen if length > 0 else False

            grain_data = {
                "id": os.path.splitext(os.path.basename(grain_path))[0],
                "width": width,
                "length": length,
                "grain_coordinates": grain_coordinates,
                "grain_url": None,
                "discolor": discolor_result,  # Will be overridden by RGB classification
                "chalky": chalky_result,
                "chalky_count": chalky_count,
                "broken": is_broken
            }

            return grain_data, oriented_path, feature_dict

        except Exception as e:
            logger.error(f"Error analyzing grain {grain_path}: {str(e)}")
            return None, None, None
    
    @staticmethod
    def collect_rgb_values(grain_paths, pixels_per_metric, exclude_flags=None):
        """
        Collect RGB values from all grains for (B-R) value statistics
        
        Args:
            grain_paths: List of grain image paths
            pixels_per_metric: Pixels per metric value (always hardcoded 15.62)
            exclude_flags: List of boolean flags indicating which grains to exclude
        
        Returns:
            Tuple of (rgb_values, grain_features)
        """
        if exclude_flags is None:
            exclude_flags = [False] * len(grain_paths)
        
        rgb_values = []
        grain_features = {}
        
        for grain_path, exclude_grain in zip(grain_paths, exclude_flags):
            # Skip excluded grains
            if exclude_grain:
                continue
                
            feature_dict = process_image_stage2(grain_path, pixels_per_metric, exclude_grain)
            
            if feature_dict:
                R = feature_dict.get('R', 0.0)
                G = feature_dict.get('G', 0.0)
                B = feature_dict.get('B', 0.0)
                rgb_values.append((R, G, B))
                grain_features[os.path.basename(grain_path)] = feature_dict
        
        logger.info(f"Collected RGB values from {len(rgb_values)} included grains")
        return rgb_values, grain_features
    
    @staticmethod
    def process_grain_with_classification(grain_path, grain_filename, feature_dict, 
                                         avg_br, pixels_per_metric, 
                                         minlen, chalky_percentage, exclude_grain=False):
        """
        Process grain with statistical (B-R)-value based discoloration classification
        
        Args:
            grain_path: Path to grain image
            grain_filename: Filename of grain
            feature_dict: Pre-computed features
            avg_br: Average (B-R) value across all grains
            pixels_per_metric: Pixels per metric value (always hardcoded 15.62)
            minlen: Minimum length threshold
            chalky_percentage: Chalky percentage threshold
            exclude_grain: If True, skip this grain
        
        Returns:
            dict: Processed grain data with statistical discoloration classification or None if excluded
        """
        # Skip excluded grains
        if exclude_grain:
            logger.info(f"Skipping excluded grain in classification: {grain_filename}")
            return None
        
        grain_image = cv2.imread(grain_path)

        # Keep old discolor detection for reference (optional)
        discolor_result = RiceQualityAnalysis.find_discolor(grain_image)
        
        # Chalky detection
        chalky_count, chalky_indices_grain = RiceQualityAnalysis.find_chalkiness(
            grain_image, percent=chalky_percentage
        )

        # Extract RGB values
        R = feature_dict.get('R', 0.0)
        G = feature_dict.get('G', 0.0)
        B = feature_dict.get('B', 0.0)
        length = feature_dict.get('length', 0.0)
        breadth = feature_dict.get('breadth', 0.0)
        
        # Use statistical (B-R)-value based discoloration classification
        discoloration_class = classify_discoloration(B, R, avg_br)
        is_broken = length < minlen if length > 0 else False

        return {
            'filename': grain_filename,
            'length': length,
            'breadth': breadth,
            'R': R,
            'G': G,
            'B': B,
            'discoloration_class': discoloration_class,  # Statistical (B-R)-value based classification
            'discolor_result': discolor_result,  # Old method (for reference)
            'chalky_count': chalky_count,
            'chalky': "Yes" if chalky_count > 0 else "No",
            'is_broken': is_broken
        }