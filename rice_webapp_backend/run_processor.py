import cv2
import numpy as np
import os
import sys

# Ensure the current directory is in the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from preprocessing.image_processor import ImageProcessor
except ImportError as e:
    print(f"Error importing ImageProcessor: {e}")
    print("Make sure this script is in the 'rice_webapp_backend' directory.")
    sys.exit(1)

# Configuration
INPUT_IMAGE_PATH = "static\\uploads\\19_discolor.jpg"  # Change this to your target image
OUTPUT_IMAGE_PATH = "19_discolor.jpg"

def main():
    # 1. Check if input exists
    if not os.path.exists(INPUT_IMAGE_PATH):
        print(f"Error: Input image not found at {INPUT_IMAGE_PATH}")
        return

    print(f"Loading image from: {INPUT_IMAGE_PATH}")
    try:
        image = ImageProcessor.load_image(INPUT_IMAGE_PATH)
    except Exception as e:
        print(f"Failed to load image: {e}")
        return

    # 2. Run the segmentation (Watershed)
    print("Running watershed segmentation...")
    # separate_touching_grains returns (markers, count) where markers is a labeled image
    markers, num_grains = ImageProcessor.separate_touching_grains(image)
    
    if num_grains == 0:
        print("No grains detected.")
        return

    print(f"Detected {num_grains} grains.")

    # 3. Draw contours on the image
    print("Drawing contours...")
    output_image = image.copy()
    
    # Iterate through each detected grain label
    for label_id in range(1, num_grains + 1):
        # Create a binary mask for the current grain (grain=255, bg=0)
        mask = (markers == label_id).astype(np.uint8) * 255
        
        # Find contours on this mask
        # RETR_EXTERNAL gets the outer boundary of the grain
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Draw the contours in Green (0, 255, 0) with a thickness of 2
        cv2.drawContours(output_image, contours, -1, (0, 0, 255), 2)

    # 4. Save the result
    cv2.imwrite(OUTPUT_IMAGE_PATH, output_image)
    print(f"Success! Processed image saved to: {os.path.abspath(OUTPUT_IMAGE_PATH)}")

if __name__ == "__main__":
    main()