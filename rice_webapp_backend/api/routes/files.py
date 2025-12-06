# api/routes/files.py
"""
File serving routes
Serves images, Excel files, and logs from local storage
"""

import os
import logging
from flask import Blueprint, send_from_directory, jsonify, request
from config.settings import Config
from storage.local_storage import load_json, save_json

logger = logging.getLogger(__name__)

file_bp = Blueprint('files', __name__)


# ==================== IMAGE/FILE SERVING ROUTES ====================

@file_bp.route('/grain-image/<path:filename>', methods=['GET'])
def serve_grain_image(filename):
    """
    Serve individual grain images from local storage

    Args:
        filename: Filename or relative path (e.g., "base_name/grain.jpg")

    Returns:
        File: Image file
    """
    try:
        # Handle nested paths
        full_path = os.path.join(Config.GRAIN_FOLDER, filename)

        # Check if file exists
        if not os.path.exists(full_path):
            logger.error(f"Grain image not found: {full_path}")
            return jsonify({"error": "Image not found"}), 404

        # Get directory and filename
        directory = os.path.dirname(full_path)
        file_name = os.path.basename(full_path)

        return send_from_directory(directory, file_name)
    except Exception as e:
        logger.error(f"Error serving grain image {filename}: {str(e)}")
        return jsonify({"error": "Image not found"}), 404


@file_bp.route('/cropped-image/<path:filename>', methods=['GET'])
def serve_cropped_image(filename):
    """Serve cropped images from local storage"""
    try:
        return send_from_directory(Config.CROPPED_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving cropped image {filename}: {str(e)}")
        return jsonify({"error": "Image not found"}), 404


@file_bp.route('/result-image/<path:filename>', methods=['GET'])
def serve_result_image(filename):
    """Serve result images from local storage"""
    try:
        return send_from_directory(Config.RESULT_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving result image {filename}: {str(e)}")
        return jsonify({"error": "Image not found"}), 404


@file_bp.route('/upload/<path:filename>', methods=['GET'])
def serve_upload_image(filename):
    """Serve uploaded images from local storage"""
    try:
        return send_from_directory(Config.UPLOAD_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving upload image {filename}: {str(e)}")
        return jsonify({"error": "Image not found"}), 404


@file_bp.route('/excel/<path:filename>', methods=['GET'])
def serve_excel_file(filename):
    """Serve Excel files from local storage"""
    try:
        return send_from_directory(Config.EXCEL_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving Excel file {filename}: {str(e)}")
        return jsonify({"error": "File not found"}), 404


@file_bp.route('/logs/<path:filename>', methods=['GET'])
def serve_log_file(filename):
    """Serve log files from local storage"""
    try:
        return send_from_directory(Config.LOG_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving log file {filename}: {str(e)}")
        return jsonify({"error": "File not found"}), 404


# ==================== LOG DETAILS ROUTES ====================

@file_bp.route('/logs/<path:logFile>/details', methods=['GET'])
def get_log_details(logFile):
    """
    Get details from a specific log file

    Args:
        logFile: Log filename (e.g., "sample.json")

    Returns:
        JSON: Details data or empty object if not found
    """
    try:
        log_path = os.path.join(Config.LOG_FOLDER, logFile)
        log_data = load_json(log_path)

        if not log_data:
            logger.warning(f"Log file not found: {logFile}")
            return jsonify({}), 404

        # Return details if present, otherwise empty object
        details = log_data.get('details', {})
        return jsonify(details), 200

    except Exception as e:
        logger.error(f"Error fetching details from {logFile}: {str(e)}")
        return jsonify({"error": "Failed to fetch details"}), 500


@file_bp.route('/logs/<path:logFile>/details', methods=['POST'])
def save_log_details(logFile):
    """
    Save details to a specific log file

    Args:
        logFile: Log filename (e.g., "sample.json")

    Expected JSON payload:
        {
            "seller_name": "...",
            "seller_code": "...",
            "variety": "...",
            "type": "...",
            "sample_name": "...",
            "sample_source": "...",
            "lot_size": "...",
            "lot_unit": "..."
        }

    Returns:
        JSON: Success status
    """
    try:
        log_path = os.path.join(Config.LOG_FOLDER, logFile)

        # Load existing log data
        log_data = load_json(log_path)
        if not log_data:
            logger.warning(f"Log file not found for saving details: {logFile}")
            return jsonify({"error": "Log file not found"}), 404

        # Get details from request
        details = request.get_json()
        if not details:
            return jsonify({"error": "No details provided"}), 400

        # Add/update details in log data
        log_data['details'] = details

        # Save updated log data
        if save_json(log_data, log_path):
            logger.info(f"Details saved to log file: {logFile}")
            return jsonify({"message": "Details saved successfully"}), 200
        else:
            return jsonify({"error": "Failed to save details"}), 500

    except Exception as e:
        logger.error(f"Error saving details to {logFile}: {str(e)}")
        return jsonify({"error": "Failed to save details"}), 500


# ==================== MODEL FILE SAVING ROUTE ====================

@file_bp.route('/api/save-model', methods=['POST'])
def save_model():
    """
    Save model file locally from frontend download
    Frontend sends model data as array of bytes after downloading from EC2

    Returns:
        JSON: Success status and file info
    """
    try:
        data = request.get_json()
        file_name = data.get('fileName')
        file_data = data.get('data')  # Array of bytes

        if not file_name or not file_data:
            return jsonify({
                'success': False,
                'message': 'Missing file name or data'
            }), 400

        # Create models directory
        models_folder = os.path.join(Config.BASE_DIR, 'models')
        os.makedirs(models_folder, exist_ok=True)

        # Save the file
        file_path = os.path.join(models_folder, file_name)
        with open(file_path, 'wb') as f:
            f.write(bytes(file_data))

        logger.info(f"Successfully saved model file: {file_path}")

        return jsonify({
            'success': True,
            'message': 'Model file saved successfully',
            'fileName': file_name,
            'path': file_path
        }), 200

    except Exception as e:
        logger.error(f"Error saving model file: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@file_bp.route('/api/verify-models', methods=['GET'])
def verify_models():
    """
    Check if model files exist locally

    Returns:
        JSON: Model existence status and file list
    """
    try:
        models_folder = os.path.join(Config.BASE_DIR, 'models')

        if not os.path.exists(models_folder):
            return jsonify({
                'success': False,
                'modelsExist': False,
                'message': 'Models folder not found',
                'files': []
            }), 404

        # List all CSV files in models folder
        model_files = [f for f in os.listdir(models_folder) if f.endswith('.csv')]

        logger.info(f"Found {len(model_files)} model files in {models_folder}")

        return jsonify({
            'success': True,
            'modelsExist': len(model_files) >= 2,  # Need at least sella + non-sella
            'files': model_files,
            'count': len(model_files),
            'path': models_folder
        }), 200

    except Exception as e:
        logger.error(f"Error verifying models: {e}")
        return jsonify({
            'success': False,
            'modelsExist': False,
            'message': str(e),
            'files': []
        }), 500
