# defects/chalky.py
"""
Chalkiness detection using variance-based filtering
Chalky grains have HIGH variance (bright spots + darker areas)
Non-chalky grains have LOW variance (uniform color)
"""

import cv2
import numpy as np
import logging
from config.constants import (
    FIXED_BRIGHT_THRESHOLD,
    CHALKY_PERCENTAGE_THRESHOLD,
    MIN_BRIGHT_PIXEL_COUNT,
    BRIGHTNESS_VARIANCE_THRESHOLD,
    TH1_MIN_CHALKY,
    TH1_MAX_CHALKY,
    LOWER_CYAN_BGR,
    UPPER_CYAN_BGR
)

logger = logging.getLogger(__name__)


def create_cyan_mask(image):
    """
    Create binary mask where cyan pixels are white (255)
    
    Args:
        image: BGR image with cyan background
    
    Returns:
        Binary mask (uint8)
    """
    cyan_mask = cv2.inRange(image, LOWER_CYAN_BGR, UPPER_CYAN_BGR)
    return cyan_mask


def calculate_chalkiness_percentage(image, use_adaptive=True):
    """
    Calculate chalkiness percentage using variance-based filtering
    
    Args:
        image: Input BGR image with cyan background
        use_adaptive: If True, use variance filtering to reduce false positives
    
    Returns:
        float: Chalkiness percentage (0-100)
    
    Logic:
        1. Uses fixed brightness threshold (178) like original
        2. Adds variance check: chalky grains have HIGH variance (bright AND dark spots)
        3. Non-chalky grains have LOW variance (uniform color)
        4. This simple approach works better than complex adaptive methods
    """
    try:
        # Create mask to exclude cyan background
        cyan_mask = create_cyan_mask(image)
        grain_mask = cv2.bitwise_not(cyan_mask)  # Grains are NOT cyan
        
        # Convert to grayscale
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Get only grain pixels
        grain_pixels = gray_image[grain_mask > 0]
        
        # Total grain pixels (excluding cyan background)
        total_grain_pixels = len(grain_pixels)
        
        if total_grain_pixels == 0:
            logger.warning("No grain pixels found in image")
            return 0
        
        # Count black/dark pixels (0-50) within grain area
        bpx = np.sum(
            (gray_image >= TH1_MIN_CHALKY) & 
            (gray_image <= TH1_MAX_CHALKY) & 
            (grain_mask > 0)
        )
        
        # Grain pixels excluding the black/dark regions
        gpx = total_grain_pixels - bpx

        if gpx <= 0:
            logger.warning("No valid grain pixels after excluding dark regions")
            return 0
        
        # Calculate grain statistics
        mean_brightness = np.mean(grain_pixels)
        variance = np.var(grain_pixels)
        std_brightness = np.std(grain_pixels)
        
        # Count bright pixels using FIXED threshold (original method)
        wpx = np.sum(
            (gray_image >= FIXED_BRIGHT_THRESHOLD) & 
            (grain_mask > 0)
        )
        
        # Calculate raw percentage
        wpx_percentage = (wpx / gpx * 100) if gpx > 0 else 0
        
        # VARIANCE-BASED FILTERING (if adaptive mode enabled)
        if use_adaptive:
            # Chalky grains have HIGH variance (bright spots + darker areas)
            # Non-chalky grains have LOW variance (uniform color)
            # If variance is too low, the grain is probably uniform (non-chalky)
            
            if variance < BRIGHTNESS_VARIANCE_THRESHOLD:
                # Low variance = uniform color = likely NOT chalky
                # Reduce the percentage significantly
                wpx_percentage = wpx_percentage * 0.3  # Reduce by 70%
                logger.debug(
                    f"Low variance grain ({variance:.1f} < {BRIGHTNESS_VARIANCE_THRESHOLD}): "
                    f"Reducing chalkiness to {wpx_percentage:.2f}%"
                )
            
            # Additional filter: Very low bright pixel count
            if wpx < MIN_BRIGHT_PIXEL_COUNT:
                wpx_percentage = wpx_percentage * 0.5
                logger.debug(
                    f"Few bright pixels ({wpx} < {MIN_BRIGHT_PIXEL_COUNT}): "
                    f"Reducing to {wpx_percentage:.2f}%"
                )
        
        # Debug logging
        logger.debug(
            f"Grain analysis: mean={mean_brightness:.1f}, std={std_brightness:.1f}, "
            f"var={variance:.1f}, wpx={wpx}, gpx={gpx}, "
            f"raw_pct={(wpx/gpx*100):.2f}%, final_pct={wpx_percentage:.2f}%"
        )
        
        return wpx_percentage
        
    except Exception as e:
        logger.error(f"Error in calculate_chalkiness_percentage: {str(e)}")
        return 0


def detect_chalkiness(image, threshold_percentage=CHALKY_PERCENTAGE_THRESHOLD, use_adaptive=True):
    """
    Detect if grain is chalky based on threshold
    
    Args:
        image: Input BGR image with cyan background
        threshold_percentage: Threshold for chalkiness (default 30%)
        use_adaptive: Use variance-based filtering (recommended: True)
    
    Returns:
        tuple: (is_chalky: bool, chalkiness_percentage: float)
    """
    try:
        chalkiness_pct = calculate_chalkiness_percentage(image, use_adaptive=use_adaptive)
        
        # Use default threshold if provided is too low
        effective_threshold = max(threshold_percentage, CHALKY_PERCENTAGE_THRESHOLD)
        
        is_chalky = chalkiness_pct >= effective_threshold
        
        if is_chalky:
            logger.debug(
                f"Grain marked as CHALKY ({chalkiness_pct:.2f}% >= {effective_threshold}%)"
            )
        
        return is_chalky, chalkiness_pct

    except Exception as e:
        logger.error(f"Error in detect_chalkiness: {str(e)}")
        return False, 0.0


class ChalkyDetector:
    """Class-based interface for chalkiness detection"""

    @staticmethod
    def detect(image, threshold_percentage):
        """
        Detect chalkiness in grain image

        Args:
            image: BGR image
            threshold_percentage: Threshold for chalkiness

        Returns:
            dict: {'chalky': bool, 'chalky_count': int}
        """
        is_chalky, chalkiness_pct = detect_chalkiness(image, threshold_percentage=threshold_percentage)
        return {
            'chalky': is_chalky,
            'chalky_count': 1 if is_chalky else 0
        }
