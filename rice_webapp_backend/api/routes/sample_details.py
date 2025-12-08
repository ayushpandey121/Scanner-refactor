from flask import Blueprint, request, jsonify
import json
import os
from datetime import datetime
from pathlib import Path
from config.settings import Config

# Create Blueprint
sample_details_bp = Blueprint('sample_details', __name__)

# Define the static folder path using Config
SAMPLE_DETAILS_FOLDER = os.path.join(Config.STATIC_ROOT, 'sample_details')

# Ensure the directory exists
os.makedirs(SAMPLE_DETAILS_FOLDER, exist_ok=True)

print(f"[sample_details] Sample details folder path: {SAMPLE_DETAILS_FOLDER}")
print(f"[sample_details] Base static root: {Config.STATIC_ROOT}")


@sample_details_bp.route('/logs/<log_file>/details', methods=['POST'])
def save_sample_details(log_file):
    """
    Save sample details to a JSON file in the static folder
    """
    try:
        print(f"[save_sample_details] Received request for log_file: {log_file}")
        
        # Get the JSON data from request
        details = request.get_json()
        print(f"[save_sample_details] Received data: {details}")
        
        if not details:
            print("[save_sample_details] ERROR: No data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        if not details.get('seller_code'):
            print("[save_sample_details] ERROR: Seller code is required")
            return jsonify({'error': 'Seller code is required'}), 400
        
        # Create filename based on log_file name
        # Remove .json extension if present and add _details.json
        base_name = log_file.replace('.json', '')
        details_filename = f"{base_name}_details.json"
        
        # Full path to save the file
        file_path = os.path.join(SAMPLE_DETAILS_FOLDER, details_filename)
        print(f"[save_sample_details] Saving to: {file_path}")
        
        # Prepare data structure
        data_to_save = {
            'seller_name': details.get('seller_name', ''),
            'seller_code': details.get('seller_code', ''),
            'sample_name': details.get('sample_name', ''),
            'sample_source': details.get('sample_source', ''),
            'lot_size': details.get('lot_size', ''),
            'lot_unit': details.get('lot_unit', ''),
            'variety': details.get('variety', ''),
            'sub_variety': details.get('sub_variety', ''),
            'timestamp': details.get('timestamp') or datetime.now().isoformat(),
            'log_file': log_file,
            'last_updated': datetime.now().isoformat()
        }
        
        # Ensure directory exists
        os.makedirs(SAMPLE_DETAILS_FOLDER, exist_ok=True)
        
        # Save to JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
        print(f"[save_sample_details] Successfully saved to {file_path}")
        
        return jsonify({
            'success': True,
            'message': 'Details saved successfully',
            'file_path': details_filename,
            'saved_at': data_to_save['last_updated']
        }), 200
        
    except Exception as e:
        print(f"[save_sample_details] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sample_details_bp.route('/logs/<log_file>/details', methods=['GET'])
def get_sample_details(log_file):
    """
    Retrieve sample details from JSON file in static folder
    """
    try:
        print(f"[get_sample_details] Received request for log_file: {log_file}")
        
        # Create filename based on log_file name
        base_name = log_file.replace('.json', '')
        details_filename = f"{base_name}_details.json"
        
        # Full path to the file - FIXED: Use SAMPLE_DETAILS_FOLDER
        file_path = os.path.join(SAMPLE_DETAILS_FOLDER, details_filename)
        print(f"[get_sample_details] Looking for file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"[get_sample_details] File not found, returning empty structure")
            # Return empty structure for new samples
            return jsonify({
                'seller_name': '',
                'seller_code': '',
                'sample_name': '',
                'sample_source': '',
                'lot_size': '',
                'lot_unit': '',
                'variety': '',
                'sub_variety': '',
                'exists': False
            }), 200
        
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['exists'] = True
        print(f"[get_sample_details] Successfully loaded data")
        return jsonify(data), 200
        
    except Exception as e:
        print(f"[get_sample_details] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sample_details_bp.route('/logs/details/list', methods=['GET'])
def list_all_details():
    """
    List all saved sample details files
    """
    try:
        print(f"[list_all_details] Listing files in: {SAMPLE_DETAILS_FOLDER}")
        files = []
        # FIXED: Use SAMPLE_DETAILS_FOLDER
        if os.path.exists(SAMPLE_DETAILS_FOLDER):
            for filename in os.listdir(SAMPLE_DETAILS_FOLDER):
                if filename.endswith('_details.json'):
                    file_path = os.path.join(SAMPLE_DETAILS_FOLDER, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        files.append({
                            'filename': filename,
                            'seller_code': data.get('seller_code', ''),
                            'sample_name': data.get('sample_name', ''),
                            'last_updated': data.get('last_updated', ''),
                            'data': data
                        })
                    except Exception as e:
                        print(f"[list_all_details] Error reading {filename}: {e}")
                        continue
        
        # Sort by last_updated (newest first)
        files.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
        
        print(f"[list_all_details] Found {len(files)} files")
        return jsonify({
            'success': True,
            'count': len(files),
            'files': files
        }), 200
        
    except Exception as e:
        print(f"[list_all_details] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sample_details_bp.route('/logs/<log_file>/details', methods=['DELETE'])
def delete_sample_details(log_file):
    """
    Delete sample details file
    """
    try:
        print(f"[delete_sample_details] Received request for log_file: {log_file}")
        
        base_name = log_file.replace('.json', '')
        details_filename = f"{base_name}_details.json"
        # FIXED: Use SAMPLE_DETAILS_FOLDER
        file_path = os.path.join(SAMPLE_DETAILS_FOLDER, details_filename)
        
        if not os.path.exists(file_path):
            print(f"[delete_sample_details] File not found: {file_path}")
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        os.remove(file_path)
        print(f"[delete_sample_details] Successfully deleted: {file_path}")
        
        return jsonify({
            'success': True,
            'message': 'Details deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"[delete_sample_details] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500