# defects/discolor.py
"""
Discoloration detection using RGB-based (B-R) threshold analysis
Uses statistical approach: compares grain's (B-R) value against dataset average
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_br_statistics(grains_with_rgb):
    """
    Calculate average and standard deviation of (B-R) values from all grains
    
    Args:
        grains_with_rgb: List of dictionaries containing 'B' and 'R' values
                        Example: [{'R': 150, 'G': 140, 'B': 130}, ...]
    
    Returns:
        tuple: (avg_br: float, std_br: float)
    
    Example:
        >>> grains = [{'R': 150, 'B': 135}, {'R': 148, 'B': 132}]
        >>> avg_br, std_br = calculate_br_statistics(grains)
        >>> print(f"Avg(B-R): {avg_br:.2f}, Std: {std_br:.2f}")
    """
    br_values = []
    
    for grain in grains_with_rgb:
        if 'B' in grain and 'R' in grain and grain['B'] > 0 and grain['R'] > 0:
            br_values.append(grain['B'] - grain['R'])
    
    if not br_values:
        logger.warning("No valid B-R values found for calculating statistics")
        return 0.0, 0.0
    
    avg_br = float(np.mean(br_values))
    std_br = float(np.std(br_values))
    threshold = avg_br - 11  # Fixed threshold offset
    
    logger.info(
        f"(B-R) statistics: Avg={avg_br:.2f}, Std={std_br:.2f}, "
        f"Threshold={threshold:.2f}"
    )
    
    return avg_br, std_br


def classify_discoloration(b_value, r_value, avg_br, threshold_offset=11):
    """
    Classify grain discoloration based on (B-R) value compared to average(B-R) - offset
    
    Args:
        b_value: Blue channel value of the grain
        r_value: Red channel value of the grain
        avg_br: Average (B-R) value across all grains in the sample
        threshold_offset: Offset from average (default 11)
    
    Returns:
        str: "YES" if discolored, "NO" otherwise
    
    Logic:
        - Calculate grain's (B-R) value
        - Compare against threshold = avg(B-R) - 11
        - If grain's (B-R) < threshold → discolored (YES)
        - Otherwise → normal (NO)
    
    Example:
        >>> # Sample with avg(B-R) = -15
        >>> classify_discoloration(130, 145, -15)
        'NO'  # grain (B-R) = -15, threshold = -26, -15 > -26
        
        >>> classify_discoloration(120, 145, -15)
        'YES'  # grain (B-R) = -25, threshold = -26, -25 > -26 (but close)
    """
    br_value = b_value - r_value
    threshold = avg_br - threshold_offset
    
    if br_value < threshold:
        logger.debug(
            f"Discolored grain: (B-R)={br_value:.2f} < threshold={threshold:.2f} "
            f"(B={b_value:.2f}, R={r_value:.2f})"
        )
        return "YES"
    else:
        logger.debug(
            f"Normal grain: (B-R)={br_value:.2f} >= threshold={threshold:.2f} "
            f"(B={b_value:.2f}, R={r_value:.2f})"
        )
        return "NO"


def is_discolored(b_value, r_value, avg_br, threshold_offset=11):
    """
    Boolean version of classify_discoloration
    
    Args:
        b_value: Blue channel value
        r_value: Red channel value
        avg_br: Average (B-R) value
        threshold_offset: Offset from average (default 11)
    
    Returns:
        bool: True if discolored, False otherwise
    """
    result = classify_discoloration(b_value, r_value, avg_br, threshold_offset)
    return result == "YES"


def get_discoloration_threshold(avg_br, threshold_offset=11):
    """
    Get the discoloration threshold value

    Args:
        avg_br: Average (B-R) value
        threshold_offset: Offset from average (default 11)

    Returns:
        float: Threshold value
    """
    return avg_br - threshold_offset


class DiscolorDetector:
    """Class-based interface for discoloration detection"""

    @staticmethod
    def detect(grain_image, avg_br=None):
        """
        Detect discoloration in grain image

        Args:
            grain_image: BGR image (not used in current implementation)
            avg_br: Average (B-R) value across all grains (required)

        Returns:
            dict: {'discolor_class': str}

        Note: Currently returns 'NO' as discoloration detection requires
        grain RGB values and avg_br from all grains, which should be
        calculated at batch level.
        """
        # TODO: Implement proper discoloration detection
        # This requires grain's B, R values and avg_br from all grains
        # For now, return default 'NO'
        return {'discolor_class': 'NO'}
