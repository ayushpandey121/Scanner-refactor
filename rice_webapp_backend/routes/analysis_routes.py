# routes/analysis_routes.py
import os
import time
import logging
import tempfile
import cv2
from flask import Blueprint, request, jsonify
from utils.image_utils import decode_and_crop_image, calculate_pixels_per_metric
from services.grain_service import GrainService
from services.quality_service import QualityService
from services.prediction_service import PredictionService
from services.storage_service import StorageService
from config import Config

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/analyze_quality', methods=['POST'])
def analyze_quality():
    """Enhanced quality analysis endpoint"""
    start_time = time.time()
    request_id = f"quality_{int(time.time())}"
    logger.info(f"Starting quality analysis request {request_id}")

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    minlen = request.form.get('minlen', type=float, default=Config.DEFAULT_MIN_LENGTH)
    chalky_percentage = request.form.get('chalky_percentage', type=float,
                                        default=Config.DEFAULT_CHALKY_PERCENTAGE)
    rice_variety = request.form.get('rice_variety', default='non_sella')

    logger.info(f"Using minimum length threshold: {minlen}mm")
    logger.info(f"Using chalky percentage threshold: {chalky_percentage}%")
    logger.info(f"Using rice variety: {rice_variety}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Save uploaded file
        input_path = os.path.join(tmp_dir, file.filename)
        file.save(input_path)
        base_name = os.path.splitext(file.filename)[0]
        
        StorageService.save_uploaded_file(input_path, file.filename)
        
        # Crop image
        logger.info("Cropping input image")
        cropped_image = decode_and_crop_image(input_path)
        if cropped_image is None:
            return jsonify({"error": "Failed to crop input image"}), 500
        
        # Calculate PPM
        logger.info("Calculating PPM")
        pixels_per_metric, strip_contour = calculate_pixels_per_metric(cropped_image)
        if pixels_per_metric is None:
            return jsonify({"error": "Failed to calculate pixels per metric"}), 500
        
        # Extract grains
        logger.info("Starting grain extraction")
        try:
            masked_padded_images, grain_info_list, result_image = GrainService.extract_grains(
                cropped_image, base_name, pixels_per_metric, strip_contour
            )
            
            if not masked_padded_images:
                logger.error("No grains found")
                return jsonify({"error": "No grains detected in image"}), 400
                
        except Exception as e:
            logger.error(f"Grain extraction error: {str(e)}")
            return jsonify({"error": f"Grain extraction error: {str(e)}"}), 500
        
        # Save extracted grains and track exclusions
        padded_dir = os.path.join(tmp_dir, "padded")
        os.makedirs(padded_dir, exist_ok=True)
        
        exclude_flags_dict = {}
        
        for item, grain_info in zip(masked_padded_images, grain_info_list):
            if len(item) == 4:
                padded_image, filename, bbox, exclude_grain = item
            else:
                padded_image, filename, bbox = item
                exclude_grain = False
            
            # Get exclusion flag from grain_info
            exclude_grain = grain_info.get('exclude_grain', exclude_grain)
            exclude_flags_dict[filename] = exclude_grain
            
            grain_path = os.path.join(padded_dir, filename)
            cv2.imwrite(grain_path, padded_image)
            
            if exclude_grain:
                logger.info(f"Grain {filename} marked for exclusion (large bbox area)")
        
        grain_images = [f for f in os.listdir(padded_dir) 
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Perform quality analysis with exclusion flags
        analysis_results = QualityService.analyze_quality(
            grain_images, padded_dir, pixels_per_metric,
            minlen, chalky_percentage, base_name,
            exclude_flags_dict=exclude_flags_dict, rice_variety=rice_variety
        )
        
        # Save result image
        result_image_filename = f"{base_name}_quality_result.jpg"
        StorageService.save_result_image(result_image, result_image_filename)
        output_image_url = f"http://localhost:{Config.PORT}/result-image/{result_image_filename}"
        
        # Save comprehensive log for quality analysis
        log_entry = {
            "request_id": request_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "filename": file.filename,
            "sample_type": analysis_results['sample_type'],
            "pixels_per_metric": pixels_per_metric,
            "minlen": minlen,
            "chalky_percentage": chalky_percentage,
            "num_grains": len(analysis_results['grain_quality_data']),
            "processed_grains": len(analysis_results['grain_quality_data']),
            "quality_report": analysis_results['quality_report'],
            "grain_analysis": analysis_results['grain_quality_data'],  # All grain analysis information
            "defect_summary": analysis_results['defect_summary'],
            "output_image_url": output_image_url,
            "excel_url": analysis_results['excel_url'],
            "kett_excel_url": analysis_results['kett_excel_url'],
            "parameters": {
                "minlen": minlen,
                "chalky_percentage": chalky_percentage
            },
            "duration": time.time() - start_time,
            "input_url": f"/upload/{file.filename}"
        }

        StorageService.save_log(log_entry, f"{base_name}.json")

        response = {
            "request_id": request_id,
            "sample_type": analysis_results['sample_type'],
            "quality_report": analysis_results['quality_report'],
            "grain_analysis": analysis_results['grain_quality_data'],
            "defect_summary": analysis_results['defect_summary'],
            "output_image_url": output_image_url,
            "pixels_per_metric": round(pixels_per_metric, 2),
            "processing_time": round(time.time() - start_time, 2),
            "excel_url": analysis_results['excel_url'],
            "kett_excel_url": analysis_results['kett_excel_url']
        }

        duration = time.time() - start_time
        logger.info(f"Quality analysis request {request_id} completed in {duration:.2f}s")

        return jsonify(response)


@analysis_bp.route('/predict', methods=['POST'])
def predict():
    """Grain prediction endpoint"""
    start_time = time.time()
    request_id = f"req_{int(time.time())}"
    logger.info(f"Starting request {request_id}")

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    minlen = request.form.get('minlen', type=float, default=Config.DEFAULT_MIN_LENGTH)
    chalky_percentage = request.form.get('chalky_percentage', type=float,
                                        default=Config.DEFAULT_CHALKY_PERCENTAGE)
    rice_variety = request.form.get('rice_variety', default='non_sella')

    logger.info(f"Using minimum length threshold: {minlen}mm")
    logger.info(f"Using chalky percentage threshold: {chalky_percentage}%")
    logger.info(f"Using rice variety: {rice_variety}")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Save uploaded file
        input_path = os.path.join(tmp_dir, file.filename)
        file.save(input_path)
        base_name = os.path.splitext(file.filename)[0]
        
        StorageService.save_uploaded_file(input_path, file.filename)
        
        # Crop image
        logger.info("Cropping input image")
        cropped_image = decode_and_crop_image(input_path)
        if cropped_image is None:
            return jsonify({"error": "Failed to crop input image"}), 500
        
        # Save cropped image
        cropped_filename = f"{base_name}_cropped.jpg"
        StorageService.save_cropped_image(cropped_image, cropped_filename)
        cropped_url = f"http://localhost:{Config.PORT}/cropped-image/{cropped_filename}"
        
        # Calculate PPM
        logger.info("Calculating PPM")
        pixels_per_metric, strip_contour = calculate_pixels_per_metric(cropped_image)
        if pixels_per_metric is None:
            return jsonify({"error": "Failed to calculate pixels per metric"}), 500
        
        logger.info(f"PPM calculated: {pixels_per_metric}")
        
        # Extract grains
        logger.info("Starting grain extraction")
        try:
            masked_padded_images, grain_info_list, result_image = GrainService.extract_grains(
                cropped_image, base_name, pixels_per_metric, strip_contour
            )
            
            if not masked_padded_images:
                logger.error("No grains found")
                return jsonify({"error": "No grains detected in image"}), 400
                
        except Exception as e:
            logger.error(f"Grain extraction error: {str(e)}")
            return jsonify({"error": f"Grain extraction error: {str(e)}"}), 500
        
        # Save extracted grains and build coordinate mapping with exclusion tracking
        padded_dir = os.path.join(tmp_dir, "padded")
        os.makedirs(padded_dir, exist_ok=True)
        
        filename_to_coords = {}
        exclude_flags_dict = {}
        
        for item, grain_info in zip(masked_padded_images, grain_info_list):
            if len(item) == 4:
                padded_image, filename, bbox, exclude_grain = item
            else:
                padded_image, filename, bbox = item
                exclude_grain = False
            
            # Get exclusion flag from grain_info
            exclude_grain = grain_info.get('exclude_grain', exclude_grain)
            exclude_flags_dict[filename] = exclude_grain
            
            grain_path = os.path.join(padded_dir, filename)
            cv2.imwrite(grain_path, padded_image)
            coords = [int(coord) for coord in bbox]
            filename_to_coords[filename] = coords
            
            if exclude_grain:
                logger.info(f"Grain {filename} marked for exclusion (large bbox area)")
        
        num_grains = len(masked_padded_images)
        logger.info(f"Grain extraction complete: Found {num_grains} grains")
        
        grain_images = [f for f in os.listdir(padded_dir)
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Perform prediction with exclusion flags
        prediction_results = PredictionService.predict_grains(
            grain_images, padded_dir, filename_to_coords,
            pixels_per_metric, minlen, chalky_percentage, base_name,
            exclude_flags_dict=exclude_flags_dict, rice_variety=rice_variety
        )
        
        # Save result image
        result_image_filename = f"{base_name}_result.jpg"
        StorageService.save_result_image(result_image, result_image_filename)
        output_image_url = f"http://localhost:{Config.PORT}/result-image/{result_image_filename}"

        # Save comprehensive log with all API response information
        log_entry = {
            "request_id": request_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "filename": file.filename,
            "sample_type": prediction_results['sample_type'],
            "pixels_per_metric": pixels_per_metric,
            "minlen": minlen,
            "chalky_percentage": chalky_percentage,
            "num_grains": num_grains,
            "processed_grains": len(prediction_results['grains']),
            "statistics": prediction_results['statistics'],
            "grains": prediction_results['grains'],  # All grain information
            "cropped_url": cropped_url,
            "excel_url": prediction_results['excel_url'],
            "kett_excel_url": prediction_results['kett_excel_url'],
            "parameters": {
                "minlen": minlen,
                "chalky_percentage": chalky_percentage
            },
            "duration": time.time() - start_time,
            "input_url": f"/upload/{file.filename}",
            "output_image_url": output_image_url
        }

        StorageService.save_log(log_entry, f"{base_name}.json")
        
        response = {
            "input_url": f"/upload/{file.filename}",
            "sample_type": prediction_results['sample_type'],
            "result": {
                "statistics": prediction_results['statistics'],
                "grain": prediction_results['grains']
            },
            "cropped_url": cropped_url,
            "pixels_per_metric": round(pixels_per_metric, 2),
            "excel_url": prediction_results['excel_url'],
            "kett_excel_url": prediction_results['kett_excel_url'],
            "parameters": {
                "minlen": minlen,
                "chalky_percentage": chalky_percentage
            }
        }
        
        duration = time.time() - start_time
        logger.info(f"Request {request_id} completed in {duration:.2f}s")
        
        return jsonify(response)