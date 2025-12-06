# grain/measurements.py
"""
Grain measurement calculations: length, breadth, RGB values, area
"""
import cv2
import numpy as np
import logging
from scipy.spatial import distance as dist
from imutils.perspective import order_points
from preprocessing.image_processor import ImageProcessor

logger = logging.getLogger(__name__)


class GrainMeasurements:
    """Handles all grain measurement operations"""
    
    @staticmethod
    def midpoint(ptA, ptB):
        """Calculate midpoint between two points"""
        return ((ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5)
    
    @staticmethod
    def calculate_length_breadth(image_path, pixels_per_metric, exclude_grain=False):
        """
        Calculate grain length and breadth using minAreaRect
        
        Returns:
            dict with keys: Image Name, length, breadth, R, G, B
        """
        if exclude_grain:
            logger.info(f"Skipping excluded grain: {image_path}")
            return None
        
        try:
            # Load and preprocess
            img = ImageProcessor.load_image(image_path)
            bg_mask = ImageProcessor.create_background_mask(img)  # Updated method
            thresh = cv2.bitwise_not(bg_mask)
            
            # Find largest contour
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours:
                logger.error(f"No contour found in {image_path}")
                return None
            
            contour = max(contours, key=cv2.contourArea)
            
            # Calculate dimensions
            box = cv2.minAreaRect(contour)
            box = cv2.boxPoints(box)
            box = np.array(box, dtype="int")
            box = order_points(box)
            
            (tl, tr, br, bl) = box
            (tltrX, tltrY) = GrainMeasurements.midpoint(tl, tr)
            (blbrX, blbrY) = GrainMeasurements.midpoint(bl, br)
            (tlblX, tlblY) = GrainMeasurements.midpoint(tl, bl)
            (trbrX, trbrY) = GrainMeasurements.midpoint(tr, br)
            
            dA = dist.euclidean((tltrX, tltrY), (blbrX, blbrY))
            dB = dist.euclidean((tlblX, tlblY), (trbrX, trbrY))
            
            # Convert to mm
            dimA = dA / pixels_per_metric
            dimB = dB / pixels_per_metric
            
            length = max(dimA, dimB)
            breadth = min(dimA, dimB)
            
            # Calculate RGB
            avg_r, avg_g, avg_b = GrainMeasurements.calculate_rgb(img, bg_mask)
            
            return {
                "Image Name": image_path,
                "length": length,
                "breadth": breadth,
                "R": avg_r,
                "G": avg_g,
                "B": avg_b
            }
        
        except Exception as e:
            logger.error(f"Error measuring grain {image_path}: {str(e)}")
            return None
    
    @staticmethod
    def calculate_rgb(image, bg_mask=None):
        """
        Calculate average RGB values (excluding blue background)
        """
        try:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Create grain mask
            if bg_mask is None:
                bg_mask = ImageProcessor.create_background_mask(image)
            grain_mask = cv2.bitwise_not(bg_mask)
            
            # Extract grain pixels
            grain_mask_bool = grain_mask > 0
            grain_pixels = img_rgb[grain_mask_bool]
            
            if len(grain_pixels) == 0:
                logger.warning("No grain pixels found")
                return 0, 0, 0
            
            avg_r = np.mean(grain_pixels[:, 0])
            avg_g = np.mean(grain_pixels[:, 1])
            avg_b = np.mean(grain_pixels[:, 2])
            
            return round(avg_r, 2), round(avg_g, 2), round(avg_b, 2)
        
        except Exception as e:
            logger.error(f"Error calculating RGB: {str(e)}")
            return 0, 0, 0
    
    @staticmethod
    def calculate_area(length, breadth):
        """Calculate grain area (mm²)"""
        return round(length * breadth, 2)
    
    @staticmethod
    def calculate_lb_ratio(length, breadth):
        """Calculate length/breadth ratio"""
        if breadth == 0:
            return 0
        return round(length / breadth, 2)