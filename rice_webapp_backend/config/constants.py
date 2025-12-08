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
HARDCODED_PPM = 15.91

# Border crop coordinates (if needed)
BORDER_CROP_COORDINATES = (650, 50, 3950, 3350)

# Contour detection
MIN_CONTOUR_AREA = 500
MINIMUM_CNT_RICE = 1000
MIN_CNT_GRAIN_AREA = 1000

# Image padding
PADDED_IMAGE_KERNEL = 3
CHALKY_MARGIN = 10
CHALKY_PADDING = 20

BOUNDARY_MARGIN = 5

# ============================================================================
# COLOR DETECTION CONSTANTS
# ============================================================================

# Blue background detection (BGR format)
LOWER_BG_BGR = np.array([0, 0, 0])     # Lower bound: [B, G, R]
UPPER_BG_BGR = np.array([230, 150, 43])   # Upper bound: [B, G, R]

# Use middle values for padding: B=175, G=100, R=30
BG_COLOR_BGR = [175, 100, 30]  # Blue background in BGR for padding/borders

# ============================================================================
# CHALKINESS DETECTION CONSTANTS
# ============================================================================

# Brightness thresholds
TH1_MIN_CHALKY = 0      # Minimum dark pixel threshold
TH1_MAX_CHALKY = 50     # Maximum dark pixel threshold
TH2_MIN_CHALKY = 178    # Minimum bright pixel threshold (not used in current implementation)

# Fixed bright threshold for chalky detection
FIXED_BRIGHT_THRESHOLD = 187

# Chalkiness percentage threshold (default)
CHALKY_PERCENTAGE_THRESHOLD = 30.0
DEFAULT_CHALKY_PERCENTAGE = 30.0

# Variance-based filtering thresholds
MIN_BRIGHT_PIXEL_COUNT = 50         # Minimum bright pixels to consider chalky
BRIGHTNESS_VARIANCE_THRESHOLD = 90   # Variance threshold (chalky = high variance)

# RGB-based discoloration threshold offset
# Threshold = avg(B-R) - DISCOLORATION_THRESHOLD_OFFSET
DISCOLORATION_THRESHOLD_OFFSET = 12

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