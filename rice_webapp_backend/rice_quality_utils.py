import cv2
import numpy as np
import logging
from scipy.spatial import distance as dist
from imutils.perspective import order_points
import imutils

# Constants from agsure-vision
MAX_PIXEL_VALUE = 255
TH1_MIN_CHALKY = 0
TH2_MIN_CHALKY = 178
TH1_MAX_CHALKY = 50
DEFAULT_CHALKY_PERCENTAGE = 30
PADDED_IMAGE_KERNEL = 3
CHALKY_MARGIN = 10
CHALKY_PADDING = 20
MINIMUM_CNT_RICE = 1000
MAXIMUM_CNT_STRIP = 50000
MIN_CNT_AREA_WA = 1000
MIN_CNT_GRAIN_AREA = 1000
MULTIPLE_OBJECTS_DETECTED = "Multiple objects detected"
BOWL_NOT_FOUND = "Bowl not found"
WHITENESS_INDEX_OFFSET = 0
STRIP_WIDTH = 9.98
MAXIMUM_STRIP_LENGTH = 216
MINIMUM_PPM = 15.5
MAXIMUM_PPM = 25.5
MIN_CONTOUR_AREA = 500

# RGB-based cyan detection (BGR format in OpenCV) - from preprocessing.py
LOWER_CYAN_BGR = np.array([110, 80, 0])   # Lower bound for cyan in BGR (B, G, R)
UPPER_CYAN_BGR = np.array([255, 255, 87])  # Upper bound for cyan in BGR (B, G, R)

# HSV color ranges for discolor detection
LOWER_YELLOW_HSV = np.array([20, 55, 90])
UPPER_YELLOW_HSV = np.array([35, 255, 255])
LOWER_BROWN_HSV = np.array([10, 100, 20])
UPPER_BROWN_HSV = np.array([20, 255, 200])
LOWER_RED1_HSV = np.array([0, 100, 50])
UPPER_RED1_HSV = np.array([10, 255, 255])
LOWER_RED2_HSV = np.array([160, 100, 50])
UPPER_RED2_HSV = np.array([180, 255, 255])

# Interpolation constants
INTERPOLATION_MAX = 256
RED_INPUT = [0, 255, 255, 255, 255]
RED_OUTPUT = [0, 150, 150, 150, 255]
GREEN_INPUT = [0, 255, 255, 255, 255]
GREEN_OUTPUT = [0, 150, 150, 150, 255]
BLUE_INPUT = [0, 10, 10, 10, 255]
BLUE_OUTPUT = [0, 0, 0, 0, 0]

# NEW: Adaptive chalkiness parameters - SIMPLIFIED APPROACH
FIXED_BRIGHT_THRESHOLD = 178  # Fixed threshold for truly bright pixels
CHALKY_PERCENTAGE_THRESHOLD = 30  # Default percentage threshold
MIN_BRIGHT_PIXEL_COUNT = 50  # Minimum number of bright pixels to consider chalky
BRIGHTNESS_VARIANCE_THRESHOLD = 90  # Variance threshold - chalky grains have high variance

class RiceQualityAnalysis:
    @staticmethod
    def create_cyan_mask(image):
        """Create a binary mask where cyan pixels are white (255) - from preprocessing.py"""
        cyan_mask = cv2.inRange(image, LOWER_CYAN_BGR, UPPER_CYAN_BGR)
        return cyan_mask

    @staticmethod
    def calculate_chalkiness_percentage(image, use_adaptive=True, use_texture=False):
        """Calculate chalkiness percentage - SIMPLIFIED: Back to basics with better filtering
        
        Args:
            image: Input BGR image with cyan background
            use_adaptive: If True, use variance-based filtering to reduce false positives
            use_texture: Not used in this version
        
        Logic:
        - Uses fixed brightness threshold (178) like original
        - Adds variance check: chalky grains have HIGH variance (bright AND dark spots)
        - Non-chalky grains have LOW variance (uniform color)
        - This simple approach works better than complex adaptive methods
        """
        try:
            # Create mask to exclude cyan background
            cyan_mask = RiceQualityAnalysis.create_cyan_mask(image)
            grain_mask = cv2.bitwise_not(cyan_mask)  # Grains are NOT cyan
            
            # Convert to grayscale
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Get only grain pixels
            grain_pixels = gray_image[grain_mask > 0]
            
            # Total grain pixels (excluding cyan background)
            total_grain_pixels = len(grain_pixels)
            
            if total_grain_pixels == 0:
                logging.warning("No grain pixels found in image")
                return 0
            
            # Count black/dark pixels (0-50) within grain area
            bpx = np.sum(
                (gray_image >= TH1_MIN_CHALKY) & 
                (gray_image <= TH1_MAX_CHALKY) & 
                (grain_mask > 0)
            )
            
            # Grain pixels excluding the black/dark regions
            gpx = total_grain_pixels - bpx

            if gpx <= 0:
                logging.warning(f"No valid grain pixels after excluding dark regions")
                return 0
            
            # Calculate grain statistics
            mean_brightness = np.mean(grain_pixels)
            variance = np.var(grain_pixels)
            std_brightness = np.std(grain_pixels)
            
            # Count bright pixels using FIXED threshold (original method)
            wpx = np.sum(
                (gray_image >= FIXED_BRIGHT_THRESHOLD) & 
                (grain_mask > 0)
            )
            
            # Calculate raw percentage
            wpx_percentage = (wpx / gpx * 100) if gpx > 0 else 0
            
            # VARIANCE-BASED FILTERING (if adaptive mode enabled)
            if use_adaptive:
                # Chalky grains have HIGH variance (bright spots + darker areas)
                # Non-chalky grains have LOW variance (uniform color)
                # If variance is too low, the grain is probably uniform (non-chalky)
                
                if variance < BRIGHTNESS_VARIANCE_THRESHOLD:
                    # Low variance = uniform color = likely NOT chalky
                    # Reduce the percentage significantly
                    wpx_percentage = wpx_percentage * 0.3  # Reduce by 70%
                    logging.debug(f"Low variance grain ({variance:.1f} < {BRIGHTNESS_VARIANCE_THRESHOLD}): "
                                f"Reducing chalkiness from calculated to {wpx_percentage:.2f}%")
                
                # Additional filter: Very low bright pixel count
                if wpx < MIN_BRIGHT_PIXEL_COUNT:
                    wpx_percentage = wpx_percentage * 0.5
                    logging.debug(f"Few bright pixels ({wpx} < {MIN_BRIGHT_PIXEL_COUNT}): "
                                f"Reducing to {wpx_percentage:.2f}%")
            
            # Debug logging
            logging.debug(f"Grain analysis: mean={mean_brightness:.1f}, std={std_brightness:.1f}, "
                         f"var={variance:.1f}, wpx={wpx}, gpx={gpx}, "
                         f"raw_pct={(wpx/gpx*100):.2f}%, final_pct={wpx_percentage:.2f}%")
            
            return wpx_percentage
            
        except Exception as e:
            logging.error(f"Error in calculate_chalkiness_percentage: {str(e)}")
            return 0

    @staticmethod
    def find_discolor(image):
        """Detect discoloration in grain image from agsure-vision"""
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            mask_yellow = cv2.inRange(hsv, LOWER_YELLOW_HSV, UPPER_YELLOW_HSV)
            mask_brown = cv2.inRange(hsv, LOWER_BROWN_HSV, UPPER_BROWN_HSV)
            mask_red1 = cv2.inRange(hsv, LOWER_RED1_HSV, UPPER_RED1_HSV)
            mask_red2 = cv2.inRange(hsv, LOWER_RED2_HSV, UPPER_RED2_HSV)
            mask_red = cv2.bitwise_or(mask_red1, mask_red2)

            contours_yellow, area_yellow = RiceQualityAnalysis.get_total_valid_area(
                mask_yellow, "Yellow"
            )
            contours_brown, area_brown = RiceQualityAnalysis.get_total_valid_area(
                mask_brown, "Brown"
            )
            contours_red, area_red = RiceQualityAnalysis.get_total_valid_area(mask_red, "Red")

            color_name = None
            max_contours = []
            bgr_color = (0, 0, 0)

            if area_red >= 1.5 * area_brown and area_red > 0:
                color_name = "Red"
                max_contours = contours_red
                bgr_color = (0, 0, 255)
            elif area_brown > 0 and area_yellow > 0:
                color_name = "Brown"
                max_contours = contours_brown
                bgr_color = (19, 69, 139)
            elif area_red > 0 and area_yellow > 0:
                color_name = "Red"
                max_contours = contours_red
                bgr_color = (0, 0, 255)
            elif area_yellow > 0 and area_brown == 0 and area_red == 0:
                color_name = "Yellow"
                max_contours = contours_yellow
                bgr_color = (0, 255, 255)

            contour_image = image.copy()
            for cnt in max_contours:
                try:
                    x, y, w, h = cv2.boundingRect(cnt)
                    cv2.rectangle(contour_image, (x, y), (x + w, y + h), bgr_color, 2)
                except Exception as e:
                    logging.error(f"Error drawing contour: {str(e)}")
                    continue
            if color_name is not None:
                return color_name
            else:
                return "No"

        except Exception as e:
            logging.error(f"Error in find_discolor: {str(e)}")
            return "No"

    @staticmethod
    def find_chalkiness(image, percent=DEFAULT_CHALKY_PERCENTAGE, use_adaptive=True, use_texture=False):
        """Determine if grain is chalky - SIMPLIFIED with variance filtering
        
        Args:
            image: Input BGR image with cyan background
            percent: Threshold percentage for chalkiness (default 30%)
            use_adaptive: Use variance-based filtering to reduce false positives (recommended: True)
            use_texture: Not used in this version
        
        The chalkiness detection works by:
        1. Finding each grain contour from the original image
        2. Cropping each grain 
        3. Calculating chalkiness using fixed threshold (178)
        4. Filtering false positives using brightness variance:
           - Chalky grains have HIGH variance (bright spots + darker areas)
           - Non-chalky grains have LOW variance (uniform color)
        5. Comparing against threshold (default 30%)
        """
        try:
            logging.info(f"Running chalky detection (variance filtering={use_adaptive})")
            
            # Store original image for chalkiness calculation
            original_image = image.copy()

            chalky_indices = []
            chalkypercent = []

            # Get contours for processing
            cnt_dict = RiceQualityAnalysis.get_contours(original_image, 1)
            
            logging.info(f"Found {len(cnt_dict)} contours to process")

            for idx, c in cnt_dict.items():
                try:
                    contour_area = cv2.contourArea(c)
                    if (
                        contour_area < MINIMUM_CNT_RICE
                        or contour_area > MAXIMUM_CNT_STRIP
                    ):
                        logging.debug(f"Skipping contour {idx}: area={contour_area}")
                        continue

                    x, y, w_c, h_c = cv2.boundingRect(c)
                    
                    # Skip grains too close to image edges
                    if (
                        x < CHALKY_MARGIN
                        or y < CHALKY_MARGIN
                        or (x + w_c) > (original_image.shape[1] - CHALKY_MARGIN)
                        or (y + h_c) > (original_image.shape[0] - CHALKY_MARGIN)
                    ):
                        logging.debug(f"Skipping contour {idx}: too close to edges")
                        continue

                    # Add padding to crop region
                    x = max(0, x - PADDED_IMAGE_KERNEL)
                    y = max(0, y - PADDED_IMAGE_KERNEL)
                    w_c = min(w_c + CHALKY_PADDING, original_image.shape[1] - x)
                    h_c = min(h_c + CHALKY_PADDING, original_image.shape[0] - y)

                    if w_c > 0 and h_c > 0:
                        # Crop the grain region from ORIGINAL image
                        cropped_image1 = original_image[y : y + h_c, x : x + w_c]
                        
                        # Calculate chalkiness using variance filtering
                        chalkiness_percent = (
                            RiceQualityAnalysis.calculate_chalkiness_percentage(
                                cropped_image1, 
                                use_adaptive=use_adaptive,
                                use_texture=use_texture
                            )
                        )
                        
                        logging.info(f"Grain {idx}: chalkiness={chalkiness_percent:.2f}%, area={contour_area:.0f}")
                        chalkypercent.append(chalkiness_percent)
                        
                        # Use default threshold if provided is too low
                        effective_threshold = max(percent, DEFAULT_CHALKY_PERCENTAGE)
                            
                        # Mark as chalky if exceeds threshold
                        if chalkiness_percent >= effective_threshold:
                            chalky_indices.append(idx)
                            logging.info(f"  -> Grain {idx} marked as CHALKY ({chalkiness_percent:.2f}% >= {effective_threshold}%)")
                            
                except Exception as e:
                    logging.error(f"Error processing contour {idx}: {str(e)}")
                    continue

            logging.info(f"Total grains processed: {len(chalkypercent)}")
            logging.info(f"Threshold used: {max(percent, DEFAULT_CHALKY_PERCENTAGE)}%")
            logging.info(f"Chalky count: {len(chalky_indices)} out of {len(chalkypercent)} grains")
            
            if len(chalkypercent) > 0:
                logging.info(f"Chalkiness percentages: min={min(chalkypercent):.1f}%, "
                           f"max={max(chalkypercent):.1f}%, avg={np.mean(chalkypercent):.1f}%")
            
            count = len(chalky_indices)
            return count, chalky_indices
            
        except Exception as e:
            logging.error(f"Error in find_chalkiness: {str(e)}")
            return 0, []

    @staticmethod
    def get_contours(image, min_area=1000):
        """Get contours from image - updated for cyan background
        
        Uses cyan mask to identify grain regions (non-cyan pixels).
        """
        try:
            # Create mask: grains are NOT cyan (using RGB/BGR)
            cyan_mask = RiceQualityAnalysis.create_cyan_mask(image)
            thresh = cv2.bitwise_not(cyan_mask)  # Invert to get grains as white
            
            # Apply morphological operations to clean up the mask
            kernel = np.ones((3, 3), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnt_dict = {}

            for i, cnt in enumerate(contours):
                if cv2.contourArea(cnt) > min_area:
                    cnt_dict[i] = cnt

            return cnt_dict
            
        except Exception as e:
            logging.error(f"Error getting contours: {str(e)}")
            return {}

    @staticmethod
    def get_total_valid_area(mask, color_name):
        """Get contours and total area for a color mask"""
        try:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid_contours = []
            total_area = 0

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 10:
                    valid_contours.append(cnt)
                    total_area += area

            return valid_contours, total_area
        except Exception as e:
            logging.error(f"Error in get_total_valid_area for {color_name}: {str(e)}")
            return [], 0

    @staticmethod
    def midpoint(ptA, ptB):
        """Calculate midpoint between two points"""
        return ((ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5)

    @staticmethod
    def calculate_length_breadth(contour, pixelspermetric):
        """Calculate length and breadth from contour using strip-based pixels per metric"""
        try:
            box = cv2.minAreaRect(contour)
            box = cv2.boxPoints(box)
            box = np.array(box, dtype="int")
            box = order_points(box)

            (tl, tr, br, bl) = box
            (tltrX, tltrY) = RiceQualityAnalysis.midpoint(tl, tr)
            (blbrX, blbrY) = RiceQualityAnalysis.midpoint(bl, br)
            (tlblX, tlblY) = RiceQualityAnalysis.midpoint(tl, bl)
            (trbrX, trbrY) = RiceQualityAnalysis.midpoint(tr, br)

            dA = dist.euclidean((tltrX, tltrY), (blbrX, blbrY))
            dB = dist.euclidean((tlblX, tlblY), (trbrX, trbrY))

            # Convert to real world measurements using strip-based pixels per metric
            dimA = dA / pixelspermetric if pixelspermetric > 0 else dA
            dimB = dB / pixelspermetric if pixelspermetric > 0 else dB

            length = max(dimA, dimB)
            breadth = min(dimA, dimB)

            return length, breadth
        except Exception as e:
            logging.error(f"Error calculating length and breadth: {str(e)}")
            return 0.0, 0.0

    @staticmethod
    def add_defects_to_grain_info(grain_info_list, chalky_indices, discolor_indices, broken_indices):
        """Add defect information to grain info list"""
        for grain_info in grain_info_list:
            if "defects" not in grain_info:
                grain_info["defects"] = {
                    "broken": False,
                    "discolor": False,
                    "chalky": False,
                }

        for i in chalky_indices:
            for j in grain_info_list:
                if i == j["index"]:
                    j["defects"]["chalky"] = True

        for i in discolor_indices:
            for j in grain_info_list:
                if i == j["index"]:
                    j["defects"]["discolor"] = True

        for i in broken_indices:
            for j in grain_info_list:
                if i == j["index"]:
                    j["defects"]["broken"] = True
                    j["defects"]["chalky"] = False
                    j["defects"]["discolor"] = False

        return grain_info_list

    @staticmethod
    def generate_quality_report(grain_info_list, pixelspermetric):
        """Generate quality report with statistics"""
        try:
            num_grains = len(grain_info_list)
            length_list = []
            breadth_list = []

            for grain in grain_info_list:
                if not grain.get("defects", {}).get("broken", False):
                    length_list.append(grain.get("dimensions", {}).get("length", 0))
                    breadth_list.append(grain.get("dimensions", {}).get("breadth", 0))

            if len(length_list) == 0:
                return {
                    "num_grains": num_grains,
                    "average_length": 0,
                    "average_breadth": 0,
                    "max_length": 0,
                    "min_length": 0,
                    "chalky_count": 0,
                    "discolor_count": 0,
                    "broken_count": 0
                }

            avg_length = np.mean(length_list)
            avg_breadth = np.mean(breadth_list)
            max_length = max(length_list)
            min_length = min(length_list)

            chalky_count = sum(1 for g in grain_info_list if g.get("defects", {}).get("chalky", False))
            discolor_count = sum(1 for g in grain_info_list if g.get("defects", {}).get("discolor", False))
            broken_count = sum(1 for g in grain_info_list if g.get("defects", {}).get("broken", False))

            return {
                "num_grains": num_grains,
                "average_length": avg_length,
                "average_breadth": avg_breadth,
                "max_length": max_length,
                "min_length": min_length,
                "chalky_count": chalky_count,
                "discolor_count": discolor_count,
                "broken_count": broken_count,
                "chalky_percentage": (chalky_count / num_grains * 100) if num_grains > 0 else 0,
                "discolor_percentage": (discolor_count / num_grains * 100) if num_grains > 0 else 0,
                "broken_percentage": (broken_count / num_grains * 100) if num_grains > 0 else 0
            }
        except Exception as e:
            logging.error(f"Error generating quality report: {str(e)}")
            return {}