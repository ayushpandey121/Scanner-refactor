# quality/classifier.py
"""
Sample type classification based on RGB values
Classifies rice samples as White, Yellow, Brown, or Mixed
"""

import logging
from enum import Enum
from config.constants import SAMPLE_TYPE_THRESHOLDS

logger = logging.getLogger(__name__)


class SampleType(Enum):
    """Enum for rice sample types"""
    WHITE = "White"
    YELLOW = "Yellow"
    BROWN = "Brown"
    MIXED = "Mixed"


def determine_sample_type(avg_r, avg_b):
    """
    Determine sample type based on average RGB values
    Priority: Brown > Mixed > Yellow > White > Default
    
    Args:
        avg_r: Average R value across all grains
        avg_b: Average B value across all grains
    
    Returns:
        str: Sample type ('White', 'Yellow', 'Brown', or 'Mixed')
    
    Logic:
        1. Brown: High R (>162), Low B (<145)
        2. Mixed: High R (>145), High B (>130), Large R-B gap (>13)
        3. Yellow: Low R (<143), Low B (<125)
        4. White: High R (>140), High B (>126) OR Small R-B gap (<12)
        5. Default: White (if no match)
    
    Example:
        >>> determine_sample_type(avg_r=165, avg_b=140)
        'Brown'
        
        >>> determine_sample_type(avg_r=155, avg_b=145)
        'White'
    """
    avg_rb_gap = avg_r - avg_b
    
    # Get thresholds from config
    brown_th = SAMPLE_TYPE_THRESHOLDS["Brown"]
    mixed_th = SAMPLE_TYPE_THRESHOLDS["Mixed"]
    yellow_th = SAMPLE_TYPE_THRESHOLDS["Yellow"]
    white_th = SAMPLE_TYPE_THRESHOLDS["White"]

    # Check Brown first (most specific: high R, low B)
    if avg_r > brown_th["min_r"] and avg_b < brown_th["max_b"]:
        sample_type = SampleType.BROWN.value
        logger.info(
            f"Sample type: {sample_type} "
            f"(R={avg_r:.2f} > {brown_th['min_r']}, "
            f"B={avg_b:.2f} < {brown_th['max_b']})"
        )
        return sample_type
    
    # Check Mixed (high R and B with significant gap)
    elif (avg_r > mixed_th["min_r"] and 
          avg_b > mixed_th["min_b"] and 
          avg_rb_gap > mixed_th["min_rb_gap"]):
        sample_type = SampleType.MIXED.value
        logger.info(
            f"Sample type: {sample_type} "
            f"(R={avg_r:.2f} > {mixed_th['min_r']}, "
            f"B={avg_b:.2f} > {mixed_th['min_b']}, "
            f"R-B gap={avg_rb_gap:.2f} > {mixed_th['min_rb_gap']})"
        )
        return sample_type

    # Check Yellow (low R, low B)
    elif avg_r < yellow_th["max_r"] and avg_b < yellow_th["max_b"]:
        sample_type = SampleType.YELLOW.value
        logger.info(
            f"Sample type: {sample_type} "
            f"(R={avg_r:.2f} < {yellow_th['max_r']}, "
            f"B={avg_b:.2f} < {yellow_th['max_b']})"
        )
        return sample_type
    
    # Check White (high R, high B with small gap)
    elif ((avg_r > white_th["min_r"] and avg_b > white_th["min_b"]) or 
          (avg_rb_gap < white_th["max_rb_gap"])):
        sample_type = SampleType.WHITE.value
        logger.info(
            f"Sample type: {sample_type} "
            f"(R={avg_r:.2f}, B={avg_b:.2f}, R-B gap={avg_rb_gap:.2f})"
        )
        return sample_type
    
    # Default to White if none match (safest threshold)
    else:
        sample_type = SampleType.WHITE.value
        logger.info(
            f"Sample type: {sample_type} (default) "
            f"(R={avg_r:.2f}, B={avg_b:.2f})"
        )
        return sample_type


def get_sample_type_thresholds():
    """
    Get sample type classification thresholds
    
    Returns:
        dict: Threshold values for each sample type
    """
    return SAMPLE_TYPE_THRESHOLDS


def classify_multiple_samples(samples):
    """
    Classify multiple samples
    
    Args:
        samples: List of dicts with 'avg_r' and 'avg_b' keys
    
    Returns:
        list: Sample types for each sample
    
    Example:
        >>> samples = [
        ...     {'avg_r': 165, 'avg_b': 140},
        ...     {'avg_r': 155, 'avg_b': 145}
        ... ]
        >>> classify_multiple_samples(samples)
        ['Brown', 'White']
    """
    results = []
    
    for sample in samples:
        avg_r = sample.get('avg_r', 0)
        avg_b = sample.get('avg_b', 0)
        sample_type = determine_sample_type(avg_r, avg_b)
        results.append(sample_type)
    
    return results