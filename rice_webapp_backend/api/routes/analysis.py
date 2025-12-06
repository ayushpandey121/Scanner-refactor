# api/routes/analysis.py
"""
Analysis routes
Main endpoints for rice grain quality analysis and prediction
Uses refactored modules: preprocessing, grain, defects, quality, storage
"""

import os
import time
import logging
import tempfile
import cv2
import pandas as pd
from flask import Blueprint, request, jsonify

from config.settings import Config
from config.constants import DEFAULT_MIN_LENGTH, DEFAULT_CHALKY_PERCENTAGE

# Import refactored modules
from preprocessing import decode_and_crop_image, calculate_pixels_per_metric
from grain import extract_grains, calculate_grain_measurements
from defects import (
    detect_chalkiness,
    classify_discoloration,
    calculate_br_statistics,
    is_broken_grain
)
from quality import predict_kett
from storage import LocalStorage
from storage.s3_models import get_local_model_paths

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)


def get_device_id_local():
    """
    Get device ID from locally stored model files (fastest method)
    
    Returns:
        str: Device ID (e.g., "AGS-2001") or None if not found
    """
    try:
        models_folder = os.path.join(Config.BASE_DIR, 'models')
        
        if not os.path.exists(models_folder):
            logger.warning(f"Models folder does not exist: {models_folder}")
            return None
        
        # List all CSV files
        model_files = [f for f in os.listdir(models_folder) if f.endswith('.csv')]
        
        if not model_files:
            logger.warning(f"No model files found in: {models_folder}")
            return None
        
        # Extract model number from first file (e.g., "2001_1.csv" -> "2001")
        import re
        for file in model_files:
            match = re.match(r'(\d{4})_[12]\.csv', file)
            if match:
                model_number = match.group(1)
                device_id = f"AGS-{model_number}"
                logger.info(f"✅ Extracted device ID from local models: {device_id}")
                return device_id
        
        logger.warning(f"Could not extract device ID from model files: {model_files}")
        return None
        
    except Exception as e:
        logger.error(f"Error reading device ID from local storage: {e}")
        return None


@analysis_bp.route('/predict', methods=['POST'])
def predict():
    """
    Grain prediction endpoint
    Performs complete analysis: extraction, measurements, defect detection, Kett prediction
    
    Expected form data:
        - file: Image file
        - minlen: Minimum length threshold (optional, default: 5.0)
        - chalky_percentage: Chalky threshold (optional, default: 30.0)
        - rice_variety: 'sella' or 'non_sella' (optional, default: 'non_sella')
    
    Returns:
        JSON: Complete analysis results with statistics and grain data
    """
    start_time = time.time()
    request_id = f"predict_{int(time.time())}"
    logger.info(f"Starting prediction request {request_id}")

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Get parameters
    minlen = request.form.get('minlen', type=float, default=DEFAULT_MIN_LENGTH)
    chalky_percentage = request.form.get('chalky_percentage', type=float,
                                        default=DEFAULT_CHALKY_PERCENTAGE)
    rice_variety = request.form.get('rice_variety', default='non_sella')

    # logger.info(f"Parameters: minlen={minlen}mm, chalky={chalky_percentage}%, variety={rice_variety}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # ====================================================================
        # STEP 1: Save and preprocess image
        # ====================================================================
        input_path = os.path.join(tmp_dir, file.filename)
        file.save(input_path)
        base_name = os.path.splitext(file.filename)[0]
        
        LocalStorage.save_upload(input_path, file.filename)
        
        # Crop image
        # logger.info("Cropping input image")
        cropped_image = decode_and_crop_image(input_path)
        if cropped_image is None:
            return jsonify({"error": "Failed to crop input image"}), 500
        
        # Save cropped image
        cropped_filename = f"{base_name}_cropped.jpg"
        LocalStorage.save_cropped(cropped_image, cropped_filename)
        cropped_url = f"http://localhost:{Config.PORT}/cropped-image/{cropped_filename}"
        
        # Calculate PPM
        # logger.info("Calculating PPM")
        pixels_per_metric, _ = calculate_pixels_per_metric(cropped_image)
        if pixels_per_metric is None:
            return jsonify({"error": "Failed to calculate pixels per metric"}), 500
        
        logger.info(f"PPM: {pixels_per_metric}")
        
        # ====================================================================
        # STEP 2: Extract grains
        # ====================================================================
        logger.info("Extracting grains")
        try:
            # Updated: Extract grains returns a single list of grain data
            extracted_grains = extract_grains(
                cropped_image, base_name, pixels_per_metric
            )
            
            if not extracted_grains:
                logger.error("No grains found")
                return jsonify({"error": "No grains detected in image"}), 400
            
            # Generate result image (visualize bounding boxes)
            result_image = cropped_image.copy()
            for _, _, bbox, _ in extracted_grains:
                x, y, w, h = bbox
                cv2.rectangle(result_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
        except Exception as e:
            logger.error(f"Grain extraction error: {str(e)}")
            return jsonify({"error": f"Grain extraction error: {str(e)}"}), 500
        
        # Save extracted grains
        padded_dir = os.path.join(tmp_dir, "padded")
        os.makedirs(padded_dir, exist_ok=True)
        
        exclude_flags_dict = {}
        filename_to_coords = {}
        
        # Updated loop for extracted_grains
        for padded_image, filename, bbox, exclude_grain in extracted_grains:
            exclude_flags_dict[filename] = exclude_grain
            
            grain_path = os.path.join(padded_dir, filename)
            cv2.imwrite(grain_path, padded_image)
            
            coords = [int(coord) for coord in bbox]
            filename_to_coords[filename] = coords
        
        num_grains = len(extracted_grains)
        logger.info(f"Extracted {num_grains} grains")
        
        # ====================================================================
        # STEP 3: Calculate measurements and collect RGB values
        # ====================================================================
        logger.info("Calculating grain measurements")
        
        grain_data_list = []
        all_rgb_values = []
        
        for filename in os.listdir(padded_dir):
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            
            grain_path = os.path.join(padded_dir, filename)
            exclude_grain = exclude_flags_dict.get(filename, False)
            
            # Skip excluded grains
            if exclude_grain:
                logger.debug(f"Skipping excluded grain: {filename}")
                continue
            
            # Calculate measurements
            measurements = calculate_grain_measurements(grain_path, pixels_per_metric)
            
            if measurements:
                grain_data_list.append({
                    'filename': filename,
                    'R': measurements['R'],
                    'G': measurements['G'],
                    'B': measurements['B'],
                    'length': measurements['length'],
                    'width': measurements['breadth'],
                    'coordinates': filename_to_coords.get(filename, [])
                })
                
                all_rgb_values.append({
                    'R': measurements['R'],
                    'G': measurements['G'],
                    'B': measurements['B']
                })
        
        logger.info(f"Processed {len(grain_data_list)} grains (excluded {num_grains - len(grain_data_list)})")
        
        # ====================================================================
        # STEP 4: Determine sample type and calculate (B-R) statistics
        # ====================================================================
        if all_rgb_values:
            avg_r = sum(g['R'] for g in all_rgb_values) / len(all_rgb_values)
            avg_g = sum(g['G'] for g in all_rgb_values) / len(all_rgb_values)
            avg_b = sum(g['B'] for g in all_rgb_values) / len(all_rgb_values)
            
            # Calculate (B-R) statistics for discoloration
            avg_br, std_br = calculate_br_statistics(all_rgb_values)
            logger.info(f"(B-R) stats: avg={avg_br:.2f}, std={std_br:.2f}, threshold={avg_br-11:.2f}")
        else:
            sample_type = "White"
            avg_r = avg_g = avg_b = 0
            avg_br = std_br = 0
            logger.warning("No RGB values, defaulting to White")
        
        # ====================================================================
        # STEP 5: Analyze each grain for defects
        # ====================================================================
        logger.info("Analyzing grain defects")
        
        results = []
        chalky_rgb_values = []
        non_chalky_rgb_values = []
        
        for grain_data in grain_data_list:
            filename = grain_data['filename']
            grain_path = os.path.join(padded_dir, filename)
            grain_image = cv2.imread(grain_path)
            
            # Chalkiness detection
            is_chalky, chalky_pct = detect_chalkiness(
                grain_image,
                threshold_percentage=chalky_percentage
            )
            
            # Discoloration (RGB-based)
            discolor_status = classify_discoloration(
                grain_data['B'],
                grain_data['R'],
                avg_br
            )
            
            # Broken detection
            is_broken = is_broken_grain(grain_data['length'], minlen)
            
            # Collect RGB by chalky status
            if is_chalky:
                chalky_rgb_values.append({
                    'R': grain_data['R'],
                    'G': grain_data['G'],
                    'B': grain_data['B']
                })
            else:
                non_chalky_rgb_values.append({
                    'R': grain_data['R'],
                    'G': grain_data['G'],
                    'B': grain_data['B']
                })
            
            # Save grain image
            grain_relative_path = LocalStorage.save_grain(
                grain_path, base_name, filename
            )
            grain_url = LocalStorage.get_url('grain', grain_relative_path)
            
            results.append({
                'id': os.path.splitext(filename)[0],
                'length': grain_data['length'],
                'width': grain_data['width'],
                'R': grain_data['R'],
                'G': grain_data['G'],
                'B': grain_data['B'],
                'discolor': discolor_status,
                'chalky': "Yes" if is_chalky else "No",
                'chalky_pct': chalky_pct,
                'broken': is_broken,
                'grain_coordinates': grain_data['coordinates'],
                'grain_url': f"http://localhost:{Config.PORT}{grain_url}"
            })
        
        logger.info(f"Defect analysis complete: {len(results)} grains analyzed")
        
        # Calculate average RGB by chalky status
        logger.info("="*60)
        logger.info("RGB AVERAGES:")
        if all_rgb_values:
            logger.info(f"ALL GRAINS: R={avg_r:.2f}, G={avg_g:.2f}, B={avg_b:.2f}")
        
        if non_chalky_rgb_values:
            avg_nc_r = sum(g['R'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)
            avg_nc_g = sum(g['G'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)
            avg_nc_b = sum(g['B'] for g in non_chalky_rgb_values) / len(non_chalky_rgb_values)
            logger.info(f"NON-CHALKY: R={avg_nc_r:.2f}, G={avg_nc_g:.2f}, B={avg_nc_b:.2f}")
        
        if chalky_rgb_values:
            avg_c_r = sum(g['R'] for g in chalky_rgb_values) / len(chalky_rgb_values)
            avg_c_g = sum(g['G'] for g in chalky_rgb_values) / len(chalky_rgb_values)
            avg_c_b = sum(g['B'] for g in chalky_rgb_values) / len(chalky_rgb_values)
            logger.info(f"CHALKY: R={avg_c_r:.2f}, G={avg_c_g:.2f}, B={avg_c_b:.2f}")
        logger.info("="*60)
        
        # ====================================================================
        # STEP 6: Calculate statistics and predict Kett
        # ====================================================================
        # Auto-detect device ID
        device_id = get_device_id_local()
        if not device_id:
            logger.warning("Could not auto-detect device ID, Kett prediction may fail")
        
        # Calculate statistics
        statistics = {
            'total_grains': len(results),
            'avg_length': round(sum(g['length'] for g in results) / len(results), 2) if results else 0,
            'avg_breadth': round(sum(g['width'] for g in results) / len(results), 2) if results else 0,
            'chalky_count': sum(1 for g in results if g['chalky'] == 'Yes'),
            'discolored_count': sum(1 for g in results if g['discolor'] == 'YES'),
            'broken_count': sum(1 for g in results if g['broken'])
        }

        
        # Predict Kett value (using full dataset RGB averages)
        try:
            if all_rgb_values and device_id:
                kett_value = predict_kett(
                    avg_r, avg_g, avg_b,
                    sample_type=rice_variety,
                    device_id=device_id
                )
                statistics['kett_value'] = round(kett_value, 2)
                logger.info(f"Kett value predicted: {kett_value:.2f}")
            else:
                statistics['kett_value'] = None
                logger.warning("Kett prediction skipped (no RGB or device ID)")
        except Exception as e:
            logger.error(f"Kett prediction failed: {e}")
            statistics['kett_value'] = None
        
        # Add RGB averages to statistics
        if all_rgb_values:
            statistics['all_rgb_avg'] = {
                'R': round(avg_r, 2),
                'G': round(avg_g, 2),
                'B': round(avg_b, 2),
                'count': len(all_rgb_values)
            }
        
        if non_chalky_rgb_values:
            statistics['non_chalky_rgb_avg'] = {
                'R': round(avg_nc_r, 2),
                'G': round(avg_nc_g, 2),
                'B': round(avg_nc_b, 2),
                'count': len(non_chalky_rgb_values)
            }
        
        if chalky_rgb_values:
            statistics['chalky_rgb_avg'] = {
                'R': round(avg_c_r, 2),
                'G': round(avg_c_g, 2),
                'B': round(avg_c_b, 2),
                'count': len(chalky_rgb_values)
            }
        
        # ====================================================================
        # STEP 7: Save Excel files and results
        # ====================================================================
        excel_url = None
        kett_excel_url = None
        # COMMENTED OUT: Excel creation and saving functionality
        """
        excel_url = None
        kett_excel_url = None

        if results:
            try:
                # Full Excel file
                excel_data = [{
                    'Image Name': g['id'] + '.jpg',
                    'Length (mm)': round(g['length'], 2),
                    'Breadth (mm)': round(g['width'], 2),
                    'R': round(g['R'], 2),
                    'G': round(g['G'], 2),
                    'B': round(g['B'], 2),
                    'B-R': round(g['B'] - g['R'], 2),
                    'Discoloration': g['discolor'],
                    'Chalky': g['chalky']
                } for g in results]

                excel_filename = f"{base_name}_measurements.xlsx"
                df = pd.DataFrame(excel_data)
                LocalStorage.save_excel_file(df, excel_filename)
                excel_url = f"/excel/{excel_filename}"

                # Kett Excel (non-discolored only)
                kett_data = [
                    {
                        'Image Name': row['Image Name'],
                        'R': row['R'],
                        'G': row['G'],
                        'B': row['B'],
                        'B-R': row['B-R']
                    }
                    for row in excel_data if row['Discoloration'] == 'NO'
                ]

                if kett_data:
                    kett_excel_filename = f"{base_name}_kett.xlsx"
                    kett_df = pd.DataFrame(kett_data)
                    LocalStorage.save_excel_file(kett_df, kett_excel_filename)
                    kett_excel_url = f"/excel/{kett_excel_filename}"

            except Exception as e:
                logger.error(f"Failed to create Excel files: {e}")
        """
        
        # Save result image
        result_image_filename = f"{base_name}_result.jpg"
        LocalStorage.save_result(result_image, result_image_filename)
        output_image_url = f"http://localhost:{Config.PORT}/result-image/{result_image_filename}"
        
        # Save log
        log_entry = {
            "request_id": request_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "filename": file.filename,
            "pixels_per_metric": pixels_per_metric,
            "parameters": {
                "minlen": minlen,
                "chalky_percentage": chalky_percentage,
                "rice_variety": rice_variety
            },
            "statistics": statistics,
            "grains": results,
            "cropped_url": cropped_url,
            "duration": time.time() - start_time,
            "input_url": f"/upload/{file.filename}",
            "output_image_url": output_image_url
        }
        
        LocalStorage.save_log(log_entry, f"{base_name}.json")
        
        # Build response
        response = {
            "input_url": f"/upload/{file.filename}",
            "result": {
                "statistics": statistics,
                "grain": results
            },
            "cropped_url": cropped_url,
            "pixels_per_metric": round(pixels_per_metric, 2),
            "parameters": {
                "minlen": minlen,
                "chalky_percentage": chalky_percentage,
                "rice_variety": rice_variety
            }
        }
        
        duration = time.time() - start_time
        logger.info(f"Prediction request {request_id} completed in {duration:.2f}s")
        
        return jsonify(response), 200