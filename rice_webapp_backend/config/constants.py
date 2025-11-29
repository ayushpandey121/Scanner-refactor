# config/constants.py
"""
Application constants for rice grain analysis
Includes thresholds, color values, and detection parameters
"""

import numpy as np

# ============================================================================
# IMAGE PROCESSING CONSTANTS
# ============================================================================

# Pixels per metric (hardcoded value)
HARDCODED_PPM = 15.53

# Border crop coordinates (if needed)
BORDER_CROP_COORDINATES = (650, 50, 3950, 3350)

# Strip/reference measurements
STRIP_WIDTH = 9.98
MINIMUM_PPM = 15.5
MAXIMUM_PPM = 25.5

# Contour detection
MIN_CONTOUR_AREA = 500
MINIMUM_CNT_RICE = 1000
MAXIMUM_CNT_STRIP = 50000
MIN_CNT_AREA_WA = 1000
MIN_CNT_GRAIN_AREA = 1000

# Image padding
PADDED_IMAGE_KERNEL = 3
CHALKY_MARGIN = 10
CHALKY_PADDING = 20

# ============================================================================
# COLOR DETECTION - RGB/BGR RANGES (OpenCV uses BGR format)
# ============================================================================

# Cyan background detection (BGR format)
LOWER_CYAN_BGR = np.array([60, 50, 0])      # Lower bound for cyan (B, G, R)
UPPER_CYAN_BGR = np.array([255, 255, 93])   # Upper bound for cyan (B, G, R)

# ============================================================================
# CHALKINESS DETECTION CONSTANTS
# ============================================================================

# Brightness thresholds
TH1_MIN_CHALKY = 0      # Minimum dark pixel threshold
TH1_MAX_CHALKY = 50     # Maximum dark pixel threshold
TH2_MIN_CHALKY = 178    # Minimum bright pixel threshold (not used in current implementation)

# Fixed bright threshold for chalky detection
FIXED_BRIGHT_THRESHOLD = 178

# Chalkiness percentage threshold (default)
CHALKY_PERCENTAGE_THRESHOLD = 30.0
DEFAULT_CHALKY_PERCENTAGE = 30.0

# Variance-based filtering thresholds
MIN_BRIGHT_PIXEL_COUNT = 50         # Minimum bright pixels to consider chalky
BRIGHTNESS_VARIANCE_THRESHOLD = 90   # Variance threshold (chalky = high variance)

# ============================================================================
# SAMPLE TYPE CLASSIFICATION THRESHOLDS
# ============================================================================

SAMPLE_TYPE_THRESHOLDS = {
    "Brown": {
        "min_r": 162,
        "max_b": 145
    },
    "Mixed": {
        "min_r": 145,
        "min_b": 130,
        "min_rb_gap": 13
    },
    "Yellow": {
        "max_r": 143,
        "max_b": 125
    },
    "White": {
        "min_r": 140,
        "min_b": 126,
        "max_rb_gap": 12
    }
}

# ============================================================================
# DISCOLORATION DETECTION CONSTANTS
# ============================================================================

# RGB-based discoloration threshold offset
# Threshold = avg(B-R) - DISCOLORATION_THRESHOLD_OFFSET
DISCOLORATION_THRESHOLD_OFFSET = 11

# Legacy discoloration thresholds by sample type (not currently used)
DISCOLORATION_THRESHOLDS = {
    "White": 15,
    "Mixed": 21,
    "Brown": 26.5,
    "Yellow": 28,
}

# ============================================================================
# BROKEN GRAIN DETECTION CONSTANTS
# ============================================================================

# Default minimum length threshold (mm)
DEFAULT_MIN_LENGTH = 5.0

# ============================================================================
# KETT WHITENESS PREDICTION CONSTANTS
# ============================================================================

# Interpolation method: B-channel linear interpolation with R-channel refinement
KETT_INTERPOLATION_METHOD = "b_channel_linear"

# Monotonic interpolation tolerance
KETT_MONOTONIC_TOLERANCE = 0.01

# ============================================================================
# HSV COLOR RANGES (Legacy - not currently used)
# ============================================================================

# Yellow detection in HSV
LOWER_YELLOW_HSV = np.array([20, 55, 90])
UPPER_YELLOW_HSV = np.array([35, 255, 255])

# Brown detection in HSV
LOWER_BROWN_HSV = np.array([10, 100, 20])
UPPER_BROWN_HSV = np.array([20, 255, 200])

# Red detection in HSV (two ranges due to hue wraparound)
LOWER_RED1_HSV = np.array([0, 100, 50])
UPPER_RED1_HSV = np.array([10, 255, 255])
LOWER_RED2_HSV = np.array([160, 100, 50])
UPPER_RED2_HSV = np.array([180, 255, 255])

# ============================================================================
# INTERPOLATION CONSTANTS (Legacy - not currently used)
# ============================================================================

INTERPOLATION_MAX = 256
RED_INPUT = [0, 255, 255, 255, 255]
RED_OUTPUT = [0, 150, 150, 150, 255]
GREEN_INPUT = [0, 255, 255, 255, 255]
GREEN_OUTPUT = [0, 150, 150, 150, 255]
BLUE_INPUT = [0, 10, 10, 10, 255]
BLUE_OUTPUT = [0, 0, 0, 0, 0]

# ============================================================================
# MISC CONSTANTS
# ============================================================================

MAX_PIXEL_VALUE = 255
WHITENESS_INDEX_OFFSET = 0
MAXIMUM_STRIP_LENGTH = 216

# Error messages
MULTIPLE_OBJECTS_DETECTED = "Multiple objects detected"
BOWL_NOT_FOUND = "Bowl not found"