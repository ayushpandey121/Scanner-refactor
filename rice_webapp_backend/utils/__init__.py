# utils/__init__.py
"""
Utility functions module
Hardware detection, validation, and helper functions
"""

from .helpers import (
    validate_rgb,
    validate_length,
    format_percentage,
    format_float,
    safe_divide,
    calculate_average
)

__all__ = [
    # Helpers
    'validate_rgb',
    'validate_length',
    'format_percentage',
    'format_float',
    'safe_divide',
    'calculate_average'
]