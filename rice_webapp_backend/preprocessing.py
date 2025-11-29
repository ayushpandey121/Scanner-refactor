import os
import cv2
import numpy as np
import imutils
from imutils import contours, perspective
from scipy.spatial import distance as dist
from scipy import ndimage as ndi
from skimage.feature import peak_local_max
from skimage.segmentation import watershed
import logging
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RGB-based cyan detection (BGR format in OpenCV)
LOWER_CYAN_BGR = np.array([60, 50, 0])   # Lower bound for cyan in BGR (B, G, R)
UPPER_CYAN_BGR = np.array([255, 255, 93])  # Upper bound for cyan in BGR (B, G, R)

# =====================================================================
# COMMON UTILITIES
# =====================================================================

def midpoint(ptA, ptB):
    """Calculate midpoint between two points"""
    return (ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5

def is_cyan_pixel(pixel_bgr):
    """Check if a BGR pixel is cyan"""
    return (LOWER_CYAN_BGR[0] <= pixel_bgr[0] <= UPPER_CYAN_BGR[0] and
            LOWER_CYAN_BGR[1] <= pixel_bgr[1] <= UPPER_CYAN_BGR[1] and
            LOWER_CYAN_BGR[2] <= pixel_bgr[2] <= UPPER_CYAN_BGR[2])

def create_cyan_mask(image):
    """Create a binary mask where cyan pixels are white (255)"""
    # Create mask using inRange for efficiency
    cyan_mask = cv2.inRange(image, LOWER_CYAN_BGR, UPPER_CYAN_BGR)
    return cyan_mask

def pad_image_to_dims(image, target_dims=(500, 500)):
    """Pad image to target dimensions with CYAN background"""
    h, w = image.shape[:2]
    target_h, target_w = target_dims
    
    pad_h = max(target_h - h, 0)
    pad_w = max(target_w - w, 0)
    
    top = pad_h // 2
    bottom = pad_h - top
    left = pad_w // 2
    right = pad_w - left
    
    # Use cyan color for padding (BGR format)
    cyan_color = [255, 255, 0]
    return cv2.copyMakeBorder(image, top, bottom, left, right, 
                             cv2.BORDER_CONSTANT, value=cyan_color)

def pad_masked_grain(grain_masked, output_size=500):
    """Pad masked grain to output size with CYAN background"""
    h, w = grain_masked.shape[:2]
    
    if h > output_size or w > output_size:
        scale = min(output_size / h, output_size / w)
        grain_masked = cv2.resize(grain_masked, (int(w * scale), int(h * scale)))
        h, w = grain_masked.shape[:2]
    
    # Create cyan background
    background = np.full((output_size, output_size, 3), [255, 255, 0], dtype=np.uint8)
    
    # Create mask for the grain region (non-cyan and non-black pixels)
    cyan_mask = create_cyan_mask(grain_masked)
    
    # Mask for non-black pixels
    gray = cv2.cvtColor(grain_masked, cv2.COLOR_BGR2GRAY)
    _, black_mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
    
    # Combine: grain pixels are neither cyan nor black
    grain_mask = cv2.bitwise_and(cv2.bitwise_not(cyan_mask), black_mask)
    
    # Place grain in center
    y_offset = (output_size - h) // 2
    x_offset = (output_size - w) // 2
    
    # Copy only the grain pixels (not black, not cyan background)
    for i in range(h):
        for j in range(w):
            if grain_mask[i, j] > 0:  # If it's a grain pixel
                background[y_offset + i, x_offset + j] = grain_masked[i, j]
    
    return background

# =====================================================================
# WATERSHED SEGMENTATION FOR GRAIN SEPARATION
# =====================================================================

def separate_touching_grains_watershed(image, min_grain_area=1000):
    """
    Separate touching grains using watershed segmentation - RGB-based cyan detection
    
    Args:
        image: Input BGR image with CYAN background
        min_grain_area: Minimum area to consider as a grain
        
    Returns:
        labels: Label image where each grain has a unique integer
        num_grains: Number of grains detected
    """
    # Create mask: grains are NOT cyan (using RGB/BGR)
    cyan_mask = create_cyan_mask(image)
    thresh = cv2.bitwise_not(cyan_mask)  # Invert to get grains as white
    
    # Noise removal with morphological opening
    kernel = np.ones((3, 3), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
    
    # Sure background area - dilation
    sure_bg = cv2.dilate(opening, kernel, iterations=3)
    
    # Finding sure foreground area - distance transform + threshold
    dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
    
    # Use adaptive threshold based on image characteristics
    _, sure_fg = cv2.threshold(dist_transform, 
                                0.3 * dist_transform.max(), 
                                255, 0)
    
    sure_fg = np.uint8(sure_fg)
    
    # Unknown region
    unknown = cv2.subtract(sure_bg, sure_fg)
    
    # Marker labelling
    _, markers = cv2.connectedComponents(sure_fg)
    
    # Add 1 to all labels so background is not 0, but 1
    markers = markers + 1
    
    # Mark unknown region as 0
    markers[unknown == 255] = 0
    
    # Apply watershed
    markers = watershed(-dist_transform, markers, mask=thresh)
    
    # Filter out small regions
    unique_labels = np.unique(markers)
    filtered_markers = np.zeros_like(markers)
    label_count = 0
    
    for label in unique_labels:
        if label == 0 or label == 1:  # Skip background
            continue
        
        mask = (markers == label).astype(np.uint8) * 255
        area = cv2.countNonZero(mask)
        
        if area >= min_grain_area:
            label_count += 1
            filtered_markers[markers == label] = label_count
    
    return filtered_markers, label_count

def extract_individual_grains_from_labels(image, labels, num_grains):
    """
    Extract individual grains from watershed labels
    
    Args:
        image: Original BGR image
        labels: Label image from watershed
        num_grains: Number of grains detected
        
    Returns:
        List of tuples: (grain_image, bounding_box, contour)
    """
    grains = []
    
    for label_id in range(1, num_grains + 1):
        # Create mask for this grain
        mask = (labels == label_id).astype(np.uint8) * 255
        
        # Find contours
        contours_list, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, 
                                             cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours_list:
            continue
        
        contour = contours_list[0]
        x, y, w, h = cv2.boundingRect(contour)
        
        # Extract grain
        grain_masked = cv2.bitwise_and(image, image, mask=mask)
        grain_crop = grain_masked[y:y+h, x:x+w]
        mask_crop = mask[y:y+h, x:x+w]
        
        # Set background to black
        grain_rgb = grain_crop.copy()
        grain_rgb[mask_crop == 0] = (0, 0, 0)
        
        grains.append((grain_rgb, (x, y, w, h), contour))
    
    return grains

# =====================================================================
# STAGE 1: GRAIN EXTRACTION
# =====================================================================

def align_image_vertically(image, contours_list):
    """Align image vertically using PCA - RGB-based cyan background"""
    if not contours_list:
        logger.warning("No contours found for alignment.")
        return image

    try:
        main_contour = max(contours_list, key=cv2.contourArea)
        contour_points = main_contour.reshape(-1, 2)
        
        # PCA for orientation
        _, eigenvectors = cv2.PCACompute(contour_points.astype(np.float32), mean=None)
        angle = np.arctan2(eigenvectors[0, 1], eigenvectors[0, 0]) * 180.0 / np.pi
        
        angle = (angle + 90) % 180 if angle < -45 else angle
        
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Get cyan color for border padding (BGR format)
        cyan_color = [255, 255, 0]
        rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h), 
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=cyan_color)
        
        # Find contours again after rotation using RGB/BGR
        cyan_mask = create_cyan_mask(rotated_image)
        binary_rotated = cv2.bitwise_not(cyan_mask)
        
        contours_rotated, _ = cv2.findContours(binary_rotated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours_rotated:
            main_contour_rotated = max(contours_rotated, key=cv2.contourArea)
            x, y, width, height = cv2.boundingRect(main_contour_rotated)
            
            if width > height:
                rotation_matrix_90 = cv2.getRotationMatrix2D(center, 90, 1.0)
                rotated_image = cv2.warpAffine(rotated_image, rotation_matrix_90, (w, h), 
                                               flags=cv2.INTER_LINEAR,
                                               borderMode=cv2.BORDER_CONSTANT,
                                               borderValue=cyan_color)
        
        # Ensure tip is upwards
        cyan_mask = create_cyan_mask(rotated_image)
        binary_rotated = cv2.bitwise_not(cyan_mask)
        contours_rotated, _ = cv2.findContours(binary_rotated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours_rotated:
            main_contour_rotated = max(contours_rotated, key=cv2.contourArea)
            moments = cv2.moments(main_contour_rotated)
            
            if moments["m00"] != 0:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
            else:
                cx, cy = w // 2, h // 2
            
            farthest_point = max(main_contour_rotated[:, 0, :], 
                               key=lambda pt: np.linalg.norm(pt - np.array([cx, cy])))
            
            if farthest_point[1] > cy:
                rotated_image = cv2.rotate(rotated_image, cv2.ROTATE_180)
        
        return rotated_image
    
    except Exception as e:
        logger.error(f"Error in align_image_vertically: {str(e)}")
        return image

def process_image_stage1(image, image_name, pixelspermetric=None):
    """Process image for Stage 1 - grain extraction using watershed segmentation"""
    logger.info(f"Processing image: {image_name}")

    # Always use hardcoded PPM
    if pixelspermetric is None:
        pixelspermetric = Config.HARDCODED_PPM
    
    logger.info(f"Using hardcoded PPM: {pixelspermetric}")

    # Apply watershed segmentation to separate touching grains
    labels, num_grains = separate_touching_grains_watershed(image, min_grain_area=1000)
    
    if num_grains == 0:
        logger.warning("No grains detected.")
        return []
    
    logger.info(f"Detected {num_grains} grains using watershed segmentation")
    
    # Extract individual grains
    grains = extract_individual_grains_from_labels(image, labels, num_grains)
    
    # Collect and print contour areas
    contour_areas = []
    for idx, (grain_rgb, bbox, contour) in enumerate(grains):
        contour_area = cv2.contourArea(contour)
        contour_areas.append(contour_area)
        logger.info(f"Grain {idx + 1}: Contour area = {contour_area:.2f} pixels²")

    # Print average contour area
    if contour_areas:
        avg_contour_area = sum(contour_areas) / len(contour_areas)
        logger.info(f"Average contour area: {avg_contour_area:.2f} pixels² (from {len(contour_areas)} grains)")
    
    masked_padded_images = []
    orig = image.copy()
    
    # Calculate threshold based on average contour area
    avg_contour_area = sum(contour_areas) / len(contour_areas) if contour_areas else 0
    threshold_area = avg_contour_area + 1000
    
    logger.info(f"Average contour area: {avg_contour_area:.2f} pixels²")
    logger.info(f"Threshold area (avg + 1000): {threshold_area:.2f} pixels²")
    
    # Second pass: process grains and mark those to exclude
    excluded_count = 0
    for idx, (grain_rgb, bbox, contour) in enumerate(grains):
        x, y, w, h = bbox
        
        # Get contour area for this grain
        grain_contour_area = contour_areas[idx]
        
        # Check if grain should be excluded
        exclude_grain = grain_contour_area > threshold_area
        
        if exclude_grain:
            excluded_count += 1
            logger.info(f"Excluding grain {idx + 1}: Contour area {grain_contour_area:.2f} pixels² > threshold {threshold_area:.2f} pixels²")
        
        # Pad and align grain
        padded_grain = pad_masked_grain(grain_rgb)
        padded_grain = pad_image_to_dims(padded_grain)
        aligned_grain = align_image_vertically(padded_grain, [contour])
        
        filename = f"{image_name}_{idx + 1:03d}.jpg"
        # Add exclude flag to the tuple
        masked_padded_images.append((aligned_grain, filename, bbox, exclude_grain))
        
        # Draw contours on original for visualization
        box = cv2.minAreaRect(contour)
        box = cv2.boxPoints(box)
        box = np.array(box, dtype="int")
        box = perspective.order_points(box)

        (tl, tr, br, bl) = box
        (tltrX, tltrY) = midpoint(tl, tr)
        (blbrX, blbrY) = midpoint(bl, br)
        (tlblX, tlblY) = midpoint(tl, bl)
        (trbrX, trbrY) = midpoint(tr, br)
        
        # Use different color for excluded grains (red) vs included grains (green)
        contour_color = (0, 0, 255) if exclude_grain else (0, 255, 0)
        
        cv2.drawContours(orig, [box.astype("int")], -1, contour_color, 2)
        cv2.circle(orig, (int(tltrX), int(tltrY)), 5, (255, 0, 0), -1)
        cv2.circle(orig, (int(blbrX), int(blbrY)), 5, (255, 0, 0), -1)
        cv2.circle(orig, (int(tlblX), int(tlblY)), 5, (255, 0, 0), -1)
        cv2.circle(orig, (int(trbrX), int(trbrY)), 5, (255, 0, 0), -1)
        cv2.line(orig, (int(tltrX), int(tltrY)), (int(blbrX), int(blbrY)), (255, 0, 255), 2)
        cv2.line(orig, (int(tlblX), int(tlblY)), (int(trbrX), int(trbrY)), (255, 0, 255), 2)

    logger.info(f"Stage 1 complete: Extracted {len(masked_padded_images)} grains ({excluded_count} excluded from measurements)")
    return masked_padded_images

# =====================================================================
# STAGE 2: LENGTH & BREADTH CALCULATION
# =====================================================================

def order_points(pts):
    """Sort points in top-left, top-right, bottom-right, bottom-left order"""
    xSorted = pts[np.argsort(pts[:, 0]), :]
    leftMost = xSorted[:2, :]
    rightMost = xSorted[2:, :]
    
    leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
    (tl, bl) = leftMost
    
    rightMost = rightMost[np.argsort(rightMost[:, 1]), :]
    (tr, br) = rightMost
    
    return np.array([tl, tr, br, bl], dtype="int")

def load_and_preprocess(image_path):
    """Load and preprocess image with CYAN background - RGB-based"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot load image from {image_path}")
    
    # Create mask: grains are NOT cyan (using RGB/BGR)
    cyan_mask = create_cyan_mask(img)
    thresh = cv2.bitwise_not(cyan_mask)  # Invert to get grains as white
    


    
    return img, thresh

def get_largest_contour(thresh):
    """Get largest contour from threshold image"""
    contours_list, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours_list:
        return None
    
    largest = max(contours_list, key=cv2.contourArea)
    return largest

def find_endpoints(contour):
    """Find endpoints of the grain"""
    [vx, vy, x, y] = cv2.fitLine(contour, cv2.DIST_L2, 0, 0.01, 0.01)
    
    contour_pts = contour.reshape(-1, 2)
    t = (contour_pts[:, 0] - x) * vx + (contour_pts[:, 1] - y) * vy
    t = t.reshape(-1, 1)
    
    min_idx = np.argmin(t)
    max_idx = np.argmax(t)
    
    return contour_pts[min_idx], contour_pts[max_idx]

def correct_and_save_orientation(input_path, output_path):
    """Correct grain orientation and save"""
    try:
        img = cv2.imread(input_path)
        if img is None:
            logger.error(f"Cannot load image from {input_path}")
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        if np.mean(thresh) > 127:
            thresh = cv2.bitwise_not(thresh)
        
        contours_list, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours_list:
            cv2.imwrite(output_path, img)
            return img
        
        contour = max(contours_list, key=cv2.contourArea)
        endpoint1, endpoint2 = find_endpoints(contour)
        
        head = endpoint1 if endpoint1[1] < endpoint2[1] else endpoint2
        tail = endpoint2 if endpoint1[1] < endpoint2[1] else endpoint1
        
        if head[1] > tail[1]:
            oriented_img = cv2.rotate(img, cv2.ROTATE_180)
        else:
            oriented_img = img.copy()
        
        cv2.imwrite(output_path, oriented_img)
        return oriented_img
    
    except Exception as e:
        logger.error(f"Error in correct_and_save_orientation: {str(e)}")
        cv2.imwrite(output_path, img)
        return img

def calculate_grain_rgb(image_path):
    """Calculate average RGB values of the grain (excluding cyan background) - RGB-based"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Cannot load image from {image_path}")
            return 0, 0, 0
        
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Create mask to exclude cyan background (using BGR image)
        cyan_mask = create_cyan_mask(img)
        grain_mask = cv2.bitwise_not(cyan_mask)  # Invert: grains are NOT cyan
        
        # Extract only grain pixels (non-cyan)
        grain_mask_bool = grain_mask > 0
        grain_pixels = img_rgb[grain_mask_bool]
        
        if len(grain_pixels) == 0:
            logger.warning(f"No grain pixels found in {image_path}")
            return 0, 0, 0
        
        # Calculate average RGB
        avg_r = np.mean(grain_pixels[:, 0])
        avg_g = np.mean(grain_pixels[:, 1])
        avg_b = np.mean(grain_pixels[:, 2])
        
        return round(avg_r, 2), round(avg_g, 2), round(avg_b, 2)
    
    except Exception as e:
        logger.error(f"Error calculating RGB for {image_path}: {str(e)}")
        return 0, 0, 0

def process_image_stage2(image_path, pixelspermetric=None, exclude_grain=False):
    """Process image for Stage2 - calculate accurate length, breadth, and RGB values using hardcoded PPM
    
    Args:
        image_path: Path to the image file
        pixelspermetric: Pixels per metric value (defaults to hardcoded PPM)
        exclude_grain: If True, skip this grain and return None
    
    Returns:
        Dictionary with measurements or None if grain is excluded
    """
    # Skip processing if grain is excluded
    if exclude_grain:
        logger.info(f"Skipping excluded grain: {os.path.basename(image_path)}")
        return None
    
    try:
        # Always use hardcoded PPM
        if pixelspermetric is None:
            pixelspermetric = Config.HARDCODED_PPM
        
        img, thresh = load_and_preprocess(image_path)
        contour = get_largest_contour(thresh)
        
        if contour is None:
            logger.error(f"No contour found in {image_path}")
            return None
        
        # Calculate accurate length and breadth using minAreaRect
        box = cv2.minAreaRect(contour)
        box = cv2.boxPoints(box)
        box = np.array(box, dtype="int")
        box = perspective.order_points(box)
        
        (tl, tr, br, bl) = box
        (tltrX, tltrY) = midpoint(tl, tr)
        (blbrX, blbrY) = midpoint(bl, br)
        (tlblX, tlblY) = midpoint(tl, bl)
        (trbrX, trbrY) = midpoint(tr, br)
        
        # Calculate distances in pixels
        dA = dist.euclidean((tltrX, tltrY), (blbrX, blbrY))
        dB = dist.euclidean((tlblX, tlblY), (trbrX, trbrY))
        
        # Convert to real world measurements (mm) using hardcoded PPM
        dimA = dA / pixelspermetric
        dimB = dB / pixelspermetric
        
        length = max(dimA, dimB)
        breadth = min(dimA, dimB)
        
        # Calculate RGB values
        avg_r, avg_g, avg_b = calculate_grain_rgb(image_path)
        
        return {
            "Image Name": os.path.basename(image_path),
            "length": length,
            "breadth": breadth,
            "R": avg_r,
            "G": avg_g,
            "B": avg_b
        }
    
    except Exception as e:
        logger.error(f"Error processing image {image_path}: {str(e)}")
        return None

# For testing
if __name__ == "__main__":
    logger.info("Preprocessing module loaded successfully")