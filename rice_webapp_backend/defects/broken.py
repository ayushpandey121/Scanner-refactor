# defects/broken.py
"""
Broken grain detection based on length threshold
A grain is considered broken if its length is below the minimum threshold
"""

import logging
from config.constants import DEFAULT_MIN_LENGTH

logger = logging.getLogger(__name__)


def is_broken_grain(length, min_length=DEFAULT_MIN_LENGTH):
    """
    Determine if grain is broken based on length threshold
    
    Args:
        length: Grain length in millimeters
        min_length: Minimum length threshold (default from config)
    
    Returns:
        bool: True if broken, False otherwise
    
    Logic:
        - If length < min_length → broken
        - Otherwise → whole grain
    
    Example:
        >>> is_broken_grain(4.5, min_length=5.0)
        True
        
        >>> is_broken_grain(6.2, min_length=5.0)
        False
    """
    if length <= 0:
        logger.warning(f"Invalid grain length: {length}")
        return False
    
    is_broken = length < min_length
    
    if is_broken:
        logger.debug(
            f"Broken grain detected: length={length:.2f}mm < "
            f"threshold={min_length:.2f}mm"
        )
    
    return is_broken


def count_broken_grains(grains, min_length=DEFAULT_MIN_LENGTH):
    """
    Count number of broken grains in a list
    
    Args:
        grains: List of grain dictionaries with 'length' key
        min_length: Minimum length threshold
    
    Returns:
        int: Number of broken grains
    
    Example:
        >>> grains = [
        ...     {'length': 4.5, 'width': 2.1},
        ...     {'length': 6.2, 'width': 2.3},
        ...     {'length': 3.8, 'width': 2.0}
        ... ]
        >>> count_broken_grains(grains, min_length=5.0)
        2
    """
    broken_count = 0
    
    for grain in grains:
        length = grain.get('length', 0)
        if is_broken_grain(length, min_length):
            broken_count += 1
    
    return broken_count


def get_broken_indices(grains, min_length=DEFAULT_MIN_LENGTH):
    """
    Get indices of broken grains
    
    Args:
        grains: List of grain dictionaries with 'length' key
        min_length: Minimum length threshold
    
    Returns:
        list: Indices of broken grains
    
    Example:
        >>> grains = [
        ...     {'length': 4.5},  # index 0 - broken
        ...     {'length': 6.2},  # index 1 - whole
        ...     {'length': 3.8}   # index 2 - broken
        ... ]
        >>> get_broken_indices(grains, min_length=5.0)
        [0, 2]
    """
    broken_indices = []
    
    for idx, grain in enumerate(grains):
        length = grain.get('length', 0)
        if is_broken_grain(length, min_length):
            broken_indices.append(idx)
    
    return broken_indices


def calculate_broken_percentage(grains, min_length=DEFAULT_MIN_LENGTH):
    """
    Calculate percentage of broken grains
    
    Args:
        grains: List of grain dictionaries
        min_length: Minimum length threshold
    
    Returns:
        float: Percentage of broken grains (0-100)
    """
    if not grains:
        return 0.0
    
    broken_count = count_broken_grains(grains, min_length)
    total_count = len(grains)
    
    percentage = (broken_count / total_count) * 100
    
    logger.info(
        f"Broken grains: {broken_count}/{total_count} ({percentage:.2f}%)"
    )

    return percentage


class BrokenDetector:
    """Class-based interface for broken grain detection"""

    @staticmethod
    def is_broken(length, minlen):
        """
        Determine if grain is broken based on length threshold

        Args:
            length: Grain length in millimeters
            minlen: Minimum length threshold

        Returns:
            bool: True if broken, False otherwise
        """
        return is_broken_grain(length, minlen)
