# utils/__init__.py
"""
Utility functions module
Hardware detection, validation, and helper functions
"""

from .hardware import get_hardware_id, get_hardware_info
from .helpers import (
    validate_rgb,
    validate_length,
    format_percentage,
    format_float,
    safe_divide,
    calculate_average
)

__all__ = [
    # Hardware
    'get_hardware_id',
    'get_hardware_info',
    # Helpers
    'validate_rgb',
    'validate_length',
    'format_percentage',
    'format_float',
    'safe_divide',
    'calculate_average'
]