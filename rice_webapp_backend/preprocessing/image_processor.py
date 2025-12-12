# rice_webapp_backend/preprocessing/image_processor.py
"""
Complete image preprocessing: cropping, grain extraction, watershed segmentation
Excludes grains touching image edges
"""
import cv2
import numpy as np
import logging
from scipy.spatial import distance as dist
from imutils import perspective
from config.constants import (
    LOWER_BG_BGR, UPPER_BG_BGR, HARDCODED_PPM,
    MIN_CONTOUR_AREA, BG_COLOR_BGR, BOUNDARY_MARGIN
)

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles all image preprocessing operations"""
    
    @staticmethod
    def load_image(image_path):
        """Load image from path"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot load image from {image_path}")
        return img
    
    @staticmethod
    def create_background_mask(image):
        """
        Create binary mask where background pixels are white (255)
        Updated to detect blue background instead of cyan
        """
        return cv2.inRange(image, LOWER_BG_BGR, UPPER_BG_BGR)

    
    @staticmethod
    def decode_and_crop_image(image_path):
        """
        Decode image without cropping - returns full image
        (Kept for backward compatibility)
        """
        try:
            img = ImageProcessor.load_image(image_path)
            return img
        except Exception as e:
            logger.error(f"Error in decode_and_crop_image: {str(e)}")
            return None
    
    @staticmethod
    def get_pixels_per_metric():
        """Returns hardcoded PPM value"""
        return HARDCODED_PPM
    
    @staticmethod
    def pad_image_to_dims(image, target_dims=(500, 500)):
        """
        Pad image to target dimensions with BLUE background
        """
        h, w = image.shape[:2]
        target_h, target_w = target_dims
        
        pad_h = max(target_h - h, 0)
        pad_w = max(target_w - w, 0)
        
        top = pad_h // 2
        bottom = pad_h - top
        left = pad_w // 2
        right = pad_w - left
        
        # Use blue color from constants
        return cv2.copyMakeBorder(
            image, top, bottom, left, right, 
            cv2.BORDER_CONSTANT, value=BG_COLOR_BGR
        )
    
    @staticmethod
    def separate_touching_grains(image, min_grain_area=1000):
        """
        Separate touching grains using watershed segmentation
        
        Returns:
            labels: Label image where each grain has a unique integer
            num_grains: Number of grains detected
        """
        from scipy import ndimage as ndi
        from skimage.segmentation import watershed
        
        # Create mask: grains are not blue
        blue_mask = ImageProcessor.create_background_mask(image)
        thresh = cv2.bitwise_not(blue_mask)
        
        # Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        # Distance transform
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(
            dist_transform, 
            0.3 * dist_transform.max(), 
            255, 0
        )
        sure_fg = np.uint8(sure_fg)
        
        # Unknown region
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        # Marker labelling
        _, markers = cv2.connectedComponents(sure_fg)
        markers = markers + 1
        markers[unknown == 255] = 0
        
        # Watershed
        markers = watershed(-dist_transform, markers, mask=thresh)
        
        # Filter small regions
        unique_labels = np.unique(markers)
        filtered_markers = np.zeros_like(markers)
        label_count = 0
        
        for label in unique_labels:
            if label in [0, 1]:  # Skip background
                continue
            
            mask = (markers == label).astype(np.uint8) * 255
            area = cv2.countNonZero(mask)
            
            if area >= min_grain_area:
                label_count += 1
                filtered_markers[markers == label] = label_count
        
        return filtered_markers, label_count
    
    @staticmethod
    def extract_grains_from_labels(image, labels, num_grains):
        """
        Extract individual grains from watershed labels
        """
        grains = []
        
        for label_id in range(1, num_grains + 1):
            mask = (labels == label_id).astype(np.uint8) * 255
            contours_list, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours_list:
                continue
            
            contour = contours_list[0]
            x, y, w, h = cv2.boundingRect(contour)
            
            # Extract grain
            grain_masked = cv2.bitwise_and(image, image, mask=mask)
            grain_crop = grain_masked[y:y+h, x:x+w]
            mask_crop = mask[y:y+h, x:x+w]
            
            # Set background to BLUE using constant
            grain_rgb = grain_crop.copy()
            grain_rgb[mask_crop == 0] = BG_COLOR_BGR
            
            grains.append((grain_rgb, (x, y, w, h), contour))
        
        return grains
    
    @staticmethod
    def align_grain_vertically(image, contour):
        """
        Align grain image vertically using PCA
        Updated to use blue background for border
        """
        if not contour is not None and len(contour) > 0:
            logger.warning("No contours provided for alignment")
            return image
        
        try:
            contour_points = contour.reshape(-1, 2)
            
            # PCA for orientation
            _, eigenvectors = cv2.PCACompute(
                contour_points.astype(np.float32), mean=None
            )
            angle = np.arctan2(eigenvectors[0, 1], eigenvectors[0, 0]) * 180.0 / np.pi
            angle = (angle + 90) % 180 if angle < -45 else angle
            
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Use blue color for border
            rotated_image = cv2.warpAffine(
                image, rotation_matrix, (w, h), 
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=BG_COLOR_BGR
            )
            
            # Ensure tip is upwards (additional orientation correction)
            bg_mask = ImageProcessor.create_background_mask(rotated_image)
            binary_rotated = cv2.bitwise_not(bg_mask)
            contours_rotated, _ = cv2.findContours(
                binary_rotated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            
            if contours_rotated:
                main_contour = max(contours_rotated, key=cv2.contourArea)
                moments = cv2.moments(main_contour)
                
                if moments["m00"] != 0:
                    cx = int(moments["m10"] / moments["m00"])
                    cy = int(moments["m01"] / moments["m00"])
                else:
                    cx, cy = w // 2, h // 2
                
                farthest_point = max(
                    main_contour[:, 0, :], 
                    key=lambda pt: np.linalg.norm(pt - np.array([cx, cy]))
                )
                
                if farthest_point[1] > cy:
                    rotated_image = cv2.rotate(rotated_image, cv2.ROTATE_180)
            
            return rotated_image
        
        except Exception as e:
            logger.error(f"Error in align_grain_vertically: {str(e)}")
            return image
    
    @staticmethod
    def is_bbox_touching_boundary(bbox, image_shape, margin=BOUNDARY_MARGIN):
        """
        Check if bounding box touches image boundary
        
        Args:
            bbox: Tuple of (x, y, w, h)
            image_shape: Shape of image (height, width, channels)
            margin: Boundary margin in pixels
        
        Returns:
            bool: True if touches boundary
        """
        if len(image_shape) == 3:
            height, width, _ = image_shape
        else:
            height, width = image_shape
        
        x, y, w, h = bbox
        
        touches_left = x <= margin
        touches_top = y <= margin
        touches_right = (x + w) >= (width - margin)
        touches_bottom = (y + h) >= (height - margin)
        
        touching = touches_left or touches_top or touches_right or touches_bottom
        
        if touching:
            boundaries = []
            if touches_left: boundaries.append("left")
            if touches_top: boundaries.append("top")
            if touches_right: boundaries.append("right")
            if touches_bottom: boundaries.append("bottom")
            logger.debug(f"Grain touches: {', '.join(boundaries)}")
        
        return touching
    
    @staticmethod
    def extract_all_grains(image, image_name, pixels_per_metric):
        """
        Grain extraction pipeline with boundary detection
        
        Returns:
            List of tuples: (padded_image, filename, bbox, exclude_grain)
        """
        logger.info(f"Extracting grains from: {image_name}")
        
        # Watershed segmentation
        labels, num_grains = ImageProcessor.separate_touching_grains(
            image, min_grain_area=1000
        )
        
        if num_grains == 0:
            logger.warning("No grains detected")
            return []
        
        logger.info(f"Detected {num_grains} grains using watershed")
        
        # Extract individual grains
        grains = ImageProcessor.extract_grains_from_labels(image, labels, num_grains)
        
        # Calculate exclusion threshold (area-based)
        contour_areas = [cv2.contourArea(contour) for _, _, contour in grains]
        avg_area = sum(contour_areas) / len(contour_areas) if contour_areas else 0
        threshold_area = avg_area + 1000
        
        logger.info(f"Average contour area: {avg_area:.2f}")
        logger.info(f"Area exclusion threshold: {threshold_area:.2f}")
        
        # Process each grain
        result = []
        boundary_excluded = 0
        area_excluded = 0
        
        for idx, (grain_rgb, bbox, contour) in enumerate(grains):
            grain_area = contour_areas[idx]
            
            # Check area exclusion (existing logic)
            exclude_by_area = grain_area > threshold_area
            
            #Check boundary exclusion
            exclude_by_boundary = ImageProcessor.is_bbox_touching_boundary(
                bbox, image.shape, BOUNDARY_MARGIN
            )
            
            # Combine exclusion flags
            exclude_grain = exclude_by_area or exclude_by_boundary
            
            # Logging
            if exclude_by_area:
                area_excluded += 1
                logger.info(
                    f"Excluding grain {idx+1}: large area "
                    f"({grain_area:.2f} > {threshold_area:.2f})"
                )
            
            if exclude_by_boundary:
                boundary_excluded += 1
                logger.info(
                    f"Excluding grain {idx+1}: touches boundary "
                    f"(margin={BOUNDARY_MARGIN}px)"
                )
            
            # Pad and align
            padded_grain = ImageProcessor.pad_image_to_dims(grain_rgb, (500, 500))
            aligned_grain = ImageProcessor.align_grain_vertically(padded_grain, contour)
            
            filename = f"{image_name}_{idx+1:03d}.jpg"
            result.append((aligned_grain, filename, bbox, exclude_grain))
        
        # Summary statistics
        total_excluded = sum(1 for _, _, _, exclude in result if exclude)
        logger.info("="*60)
        logger.info("GRAIN EXTRACTION SUMMARY:")
        logger.info(f"  Total detected: {len(result)}")
        logger.info(f"  Excluded by area: {area_excluded}")
        logger.info(f"  Excluded by boundary: {boundary_excluded}")
        logger.info(f"  Total excluded: {total_excluded}")
        logger.info(f"  Included for analysis: {len(result) - total_excluded}")
        logger.info("="*60)
        
        return result