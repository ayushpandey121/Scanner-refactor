# utils/helpers.py
"""
General helper functions
Validation, formatting, and common utility functions
"""

import logging
from typing import List, Union, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_rgb(r, g, b):
    """
    Validate RGB values are in valid range (0-255)
    
    Args:
        r: Red value
        g: Green value
        b: Blue value
    
    Returns:
        bool: True if all values are valid
    
    Example:
        >>> validate_rgb(150, 140, 135)
        True
        >>> validate_rgb(300, 140, 135)
        False
    """
    try:
        r, g, b = float(r), float(g), float(b)
        return 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255
    except (ValueError, TypeError):
        return False


def validate_length(length, min_value=0.0, max_value=100.0):
    """
    Validate grain length is in reasonable range
    
    Args:
        length: Length value in mm
        min_value: Minimum acceptable length
        max_value: Maximum acceptable length
    
    Returns:
        bool: True if valid
    """
    try:
        length = float(length)
        return min_value <= length <= max_value
    except (ValueError, TypeError):
        return False


def validate_percentage(value):
    """
    Validate percentage value (0-100)
    
    Args:
        value: Percentage value
    
    Returns:
        bool: True if valid
    """
    try:
        value = float(value)
        return 0 <= value <= 100
    except (ValueError, TypeError):
        return False


def validate_positive_number(value):
    """
    Validate value is a positive number
    
    Args:
        value: Numeric value
    
    Returns:
        bool: True if positive
    """
    try:
        value = float(value)
        return value > 0
    except (ValueError, TypeError):
        return False


# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_percentage(value, decimals=2):
    """
    Format value as percentage string
    
    Args:
        value: Numeric value (0-100)
        decimals: Number of decimal places
    
    Returns:
        str: Formatted percentage (e.g., "45.67%")
    
    Example:
        >>> format_percentage(45.6789)
        '45.68%'
    """
    try:
        return f"{float(value):.{decimals}f}%"
    except (ValueError, TypeError):
        return "0.00%"


def format_float(value, decimals=2):
    """
    Format float with specified decimal places
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
    
    Returns:
        str: Formatted number
    
    Example:
        >>> format_float(3.14159, 3)
        '3.142'
    """
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return "0.00"


def format_dimension(value, unit='mm', decimals=2):
    """
    Format dimension with unit
    
    Args:
        value: Numeric value
        unit: Unit string (e.g., 'mm', 'cm')
        decimals: Number of decimal places
    
    Returns:
        str: Formatted dimension (e.g., "6.25mm")
    """
    try:
        return f"{float(value):.{decimals}f}{unit}"
    except (ValueError, TypeError):
        return f"0.00{unit}"


# ============================================================================
# CALCULATION HELPERS
# ============================================================================

def safe_divide(numerator, denominator, default=0.0):
    """
    Safely divide two numbers, returning default if division by zero
    
    Args:
        numerator: Top number
        denominator: Bottom number
        default: Value to return if denominator is zero
    
    Returns:
        float: Result or default
    
    Example:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        0.0
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def calculate_average(values: List[Union[int, float]], ignore_zero=False) -> float:
    """
    Calculate average of a list of numbers
    
    Args:
        values: List of numeric values
        ignore_zero: If True, exclude zero values from calculation
    
    Returns:
        float: Average value or 0.0 if empty
    
    Example:
        >>> calculate_average([1, 2, 3, 4, 5])
        3.0
        >>> calculate_average([1, 0, 2, 0, 3], ignore_zero=True)
        2.0
    """
    try:
        if ignore_zero:
            values = [v for v in values if v != 0]
        
        if not values:
            return 0.0
        
        return sum(values) / len(values)
    except (ValueError, TypeError):
        return 0.0


def calculate_ratio(a, b, decimals=2):
    """
    Calculate ratio of two numbers
    
    Args:
        a: First number
        b: Second number
        decimals: Decimal places to round
    
    Returns:
        float: Ratio (a/b) or 0.0 if b is zero
    
    Example:
        >>> calculate_ratio(6.5, 2.5)
        2.6
    """
    result = safe_divide(a, b, default=0.0)
    return round(result, decimals)


def clamp(value, min_value, max_value):
    """
    Clamp value between min and max
    
    Args:
        value: Value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value
    
    Returns:
        Clamped value
    
    Example:
        >>> clamp(15, 0, 10)
        10
        >>> clamp(-5, 0, 10)
        0
    """
    return max(min_value, min(value, max_value))


# ============================================================================
# DATA STRUCTURE HELPERS
# ============================================================================

def extract_values(dict_list: List[dict], key: str, default=None) -> List:
    """
    Extract specific key values from list of dictionaries
    
    Args:
        dict_list: List of dictionaries
        key: Key to extract
        default: Default value if key not found
    
    Returns:
        List of extracted values
    
    Example:
        >>> grains = [{'length': 6.5}, {'length': 5.2}, {'length': 7.1}]
        >>> extract_values(grains, 'length')
        [6.5, 5.2, 7.1]
    """
    return [d.get(key, default) for d in dict_list]


def filter_by_key(dict_list: List[dict], key: str, value) -> List[dict]:
    """
    Filter list of dictionaries by key-value pair
    
    Args:
        dict_list: List of dictionaries
        key: Key to filter by
        value: Value to match
    
    Returns:
        Filtered list
    
    Example:
        >>> grains = [
        ...     {'broken': True, 'length': 4.5},
        ...     {'broken': False, 'length': 6.5}
        ... ]
        >>> filter_by_key(grains, 'broken', False)
        [{'broken': False, 'length': 6.5}]
    """
    return [d for d in dict_list if d.get(key) == value]


def group_by_key(dict_list: List[dict], key: str) -> dict:
    """
    Group list of dictionaries by key value
    
    Args:
        dict_list: List of dictionaries
        key: Key to group by
    
    Returns:
        Dictionary with grouped items
    
    Example:
        >>> grains = [
        ...     {'type': 'chalky', 'length': 6.5},
        ...     {'type': 'normal', 'length': 6.2},
        ...     {'type': 'chalky', 'length': 5.8}
        ... ]
        >>> group_by_key(grains, 'type')
        {
            'chalky': [{'type': 'chalky', 'length': 6.5}, ...],
            'normal': [{'type': 'normal', 'length': 6.2}]
        }
    """
    groups = {}
    for item in dict_list:
        group_key = item.get(key)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(item)
    return groups


# ============================================================================
# FILE HELPERS
# ============================================================================

def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename
    
    Args:
        filename: Filename or path
    
    Returns:
        str: Extension (lowercase, with dot)
    
    Example:
        >>> get_file_extension('image.JPG')
        '.jpg'
    """
    import os
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_image_file(filename: str) -> bool:
    """
    Check if filename is an image file
    
    Args:
        filename: Filename or path
    
    Returns:
        bool: True if image file
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    return get_file_extension(filename) in image_extensions


def is_excel_file(filename: str) -> bool:
    """
    Check if filename is an Excel file
    
    Args:
        filename: Filename or path
    
    Returns:
        bool: True if Excel file
    """
    excel_extensions = {'.xlsx', '.xls'}
    return get_file_extension(filename) in excel_extensions


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters
    
    Args:
        filename: Original filename
    
    Returns:
        str: Sanitized filename
    
    Example:
        >>> sanitize_filename('my file?.jpg')
        'my_file.jpg'
    """
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    return filename


# ============================================================================
# LOGGING HELPERS
# ============================================================================

def log_grain_summary(grains: List[dict]):
    """
    Log summary statistics for grains
    
    Args:
        grains: List of grain dictionaries
    """
    if not grains:
        logger.info("No grains to summarize")
        return
    
    total = len(grains)
    chalky = sum(1 for g in grains if g.get('chalky') == 'Yes')
    discolored = sum(1 for g in grains if g.get('discolor') == 'YES')
    broken = sum(1 for g in grains if g.get('broken', False))
    
    lengths = [g.get('length', 0) for g in grains if g.get('length', 0) > 0]
    avg_length = calculate_average(lengths)
    
    logger.info("="*60)
    logger.info("GRAIN SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Grains: {total}")
    logger.info(f"Average Length: {avg_length:.2f}mm")
    logger.info(f"Chalky: {chalky} ({safe_divide(chalky, total) * 100:.1f}%)")
    logger.info(f"Discolored: {discolored} ({safe_divide(discolored, total) * 100:.1f}%)")
    logger.info(f"Broken: {broken} ({safe_divide(broken, total) * 100:.1f}%)")
    logger.info("="*60)