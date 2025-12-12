# utils/rgb.py
"""
RGB extraction utility for rice grain analysis
Extracts average RGB values from a central square region of the image
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def extract_rgb_from_square(image, square_size_ratio=0.6):
    """
    Extract RGB values from a square area in the center of the image.
    
    Parameters:
    - image: Input image (numpy array in BGR format)
    - square_size_ratio: Size of the square as a ratio of the smaller dimension (default 0.6 = 60%)
    
    Returns:
    - dict: {
        'avg_rgb': [R, G, B] average values,
        'square_coords': (x1, y1, x2, y2) coordinates of the square,
        'square_size': size of the square in pixels,
        'contour_image': image with square drawn on it (optional)
      }
    """
    if image is None:
        logger.error("Error: Invalid image input")
        return None
    
    h, w = image.shape[:2]
    
    # Calculate square dimensions (based on smaller dimension)
    square_size = int(min(h, w) * square_size_ratio)
    
    # Calculate center position
    center_x = w // 2
    center_y = h // 2
    
    # Calculate square coordinates
    half_size = square_size // 2
    x1 = center_x - half_size
    y1 = center_y - half_size
    x2 = center_x + half_size
    y2 = center_y + half_size
    
    # Ensure coordinates are within image bounds
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)
    
    # Extract the square region
    square_region = image[y1:y2, x1:x2]
    
    # Calculate average RGB values (OpenCV uses BGR, so we reverse it)
    avg_bgr = np.mean(square_region, axis=(0, 1))
    avg_rgb = avg_bgr[::-1]  # Convert BGR to RGB
    
    # Create contour image (BGR for OpenCV)
    contour_image = image.copy()
    cv2.rectangle(contour_image, (x1, y1), (x2, y2), (0, 255, 0), 8)  # Green rectangle
    
    logger.info(f"RGB Extraction:")
    logger.info(f"  Square dimensions: {square_size}x{square_size} pixels")
    logger.info(f"  Square covers {square_size_ratio*100:.0f}% of the image")
    logger.info(f"  Average RGB: R={avg_rgb[0]:.2f}, G={avg_rgb[1]:.2f}, B={avg_rgb[2]:.2f}")
    
    return {
        'avg_rgb': avg_rgb.tolist(),
        'R': round(avg_rgb[0], 2),
        'G': round(avg_rgb[1], 2),
        'B': round(avg_rgb[2], 2),
        'square_coords': (x1, y1, x2, y2),
        'square_size': square_size,
        'contour_image': contour_image
    }


def extract_rgb_from_image_path(image_path, square_size_ratio=0.6):
    """
    Extract RGB values from an image file.
    
    Parameters:
    - image_path: Path to the input image
    - square_size_ratio: Size of the square as a ratio of the smaller dimension
    
    Returns:
    - Same as extract_rgb_from_square()
    """
    image = cv2.imread(image_path)
    
    if image is None:
        logger.error(f"Error: Could not read image from {image_path}")
        return None
    
    return extract_rgb_from_square(image, square_size_ratio)