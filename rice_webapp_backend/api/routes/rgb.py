# api/routes/rgb.py
"""
RGB extraction routes
Endpoint for extracting RGB values from uploaded images
"""

import os
import time
import logging
import tempfile
import cv2
from flask import Blueprint, request, jsonify

from config.settings import Config
from storage import LocalStorage
from utils.rgb import extract_rgb_from_square

logger = logging.getLogger(__name__)

rgb_bp = Blueprint('rgb', __name__)


@rgb_bp.route('/extract-rgb', methods=['POST'])
def extract_rgb():
    """
    Extract RGB values from uploaded image
    
    Expected form data:
        - file: Image file
        - square_size_ratio: Optional, size of extraction square (default: 0.6)
    
    Returns:
        JSON: {
            'success': bool,
            'rgb': {'R': float, 'G': float, 'B': float},
            'square_size': int,
            'contour_image_url': str (URL to image with square drawn)
        }
    """
    start_time = time.time()
    request_id = f"rgb_{int(time.time())}"
    logger.info(f"Starting RGB extraction request {request_id}")
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Get optional parameters
    square_size_ratio = request.form.get('square_size_ratio', type=float, default=0.6)
    
    # Validate square_size_ratio
    if not (0.1 <= square_size_ratio <= 1.0):
        return jsonify({"error": "square_size_ratio must be between 0.1 and 1.0"}), 400
    
    logger.info(f"Parameters: square_size_ratio={square_size_ratio}")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Save uploaded file
        input_path = os.path.join(tmp_dir, file.filename)
        file.save(input_path)
        base_name = os.path.splitext(file.filename)[0]
        
        # Save original upload
        LocalStorage.save_upload(input_path, file.filename)
        
        # Load image
        image = cv2.imread(input_path)
        if image is None:
            return jsonify({"error": "Failed to load image"}), 500
        
        # Extract RGB values
        try:
            result = extract_rgb_from_square(image, square_size_ratio=square_size_ratio)
            
            if result is None:
                return jsonify({"error": "Failed to extract RGB values"}), 500
            
            # Save contour image
            contour_filename = f"{base_name}_rgb_contour.jpg"
            LocalStorage.save_result(result['contour_image'], contour_filename)
            contour_url = f"http://localhost:{Config.PORT}/result-image/{contour_filename}"
            
            # Prepare response
            response = {
                "success": True,
                "rgb": {
                    "R": result['R'],
                    "G": result['G'],
                    "B": result['B']
                }
            }
            
            # logger.info(f"✅ RGB extraction completed in {response['processing_time']}s")
            logger.info(f"   RGB values: R={result['R']}, G={result['G']}, B={result['B']}")
            
            return jsonify(response), 200
            
        except Exception as e:
            logger.error(f"Error extracting RGB: {str(e)}")
            return jsonify({"error": f"RGB extraction error: {str(e)}"}), 500


@rgb_bp.route('/extract-rgb-from-existing', methods=['POST'])
def extract_rgb_from_existing():
    """
    Extract RGB values from an already uploaded/stored image
    
    Expected JSON data:
        - image_path: Path to existing image (relative to storage folders)
        - square_size_ratio: Optional, size of extraction square (default: 0.6)
    
    Returns:
        Same as /extract-rgb
    """
    data = request.get_json()
    
    if not data or 'image_path' not in data:
        return jsonify({"error": "image_path is required"}), 400
    
    image_path = data['image_path']
    square_size_ratio = data.get('square_size_ratio', 0.6)
    
    # Try to find image in various storage folders
    possible_paths = [
        os.path.join(Config.UPLOAD_FOLDER, image_path),
        os.path.join(Config.CROPPED_FOLDER, image_path),
        os.path.join(Config.RESULT_FOLDER, image_path),
        image_path  # Try as absolute path
    ]
    
    actual_path = None
    for path in possible_paths:
        if os.path.exists(path):
            actual_path = path
            break
    
    if not actual_path:
        return jsonify({"error": f"Image not found: {image_path}"}), 404
    
    # Load image
    image = cv2.imread(actual_path)
    if image is None:
        return jsonify({"error": "Failed to load image"}), 500
    
    # Extract RGB values
    try:
        result = extract_rgb_from_square(image, square_size_ratio=square_size_ratio)
        
        if result is None:
            return jsonify({"error": "Failed to extract RGB values"}), 500
        
        # Prepare response
        response = {
            "success": True,
            "rgb": {
                "R": result['R'],
                "G": result['G'],
                "B": result['B']
            },
            "square_size": result['square_size'],
            "square_coords": result['square_coords']
        }
        
        logger.info(f"✅ RGB extraction from existing image: {image_path}")
        logger.info(f"   RGB values: R={result['R']}, G={result['G']}, B={result['B']}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error extracting RGB: {str(e)}")
        return jsonify({"error": f"RGB extraction error: {str(e)}"}), 500