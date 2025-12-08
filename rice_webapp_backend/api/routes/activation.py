# api/routes/activation.py
"""
Activation routes
Handles product key activation, login/logout, and model downloads
Updated to include correction fields for length and whiteness index
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Response
import pytz

from config.settings import Config
from storage import (
    get_activation_data,
    update_activation_data,
    get_activation_by_key,
    get_activation_by_hardware_id,
    is_key_expired,
    update_login_status
)
from storage.s3_models import (
    extract_model_number_from_device_id,
    get_model_s3_keys
)
from storage.s3_client import get_s3_client

activation_bp = Blueprint('activation', __name__)
logger = logging.getLogger(__name__)


def calculate_expiration_date(activation_date, years=1):
    """
    Calculate expiration date from activation date
    
    Args:
        activation_date: datetime object of activation
        years: Number of years until expiration (default: 1)
    
    Returns:
        str: Expiration date in 'YYYY-MM-DD HH:MM:SS' format
    """
    expiration = activation_date + timedelta(days=365 * years)
    return expiration.strftime('%Y-%m-%d %H:%M:%S')


@activation_bp.route('/activate', methods=['POST'])
def activate_key():
    """
    Simplified activation endpoint that returns device info for client-side model download
    Updated to include correction fields (length_correction, wi_correction, ww_correction)
    
    Returns:
        JSON: Activation status and device information
    """
    data = request.get_json()
    key = data.get('key')
    username = data.get('username')
    client_hardware_id = data.get('hardwareId')

    if not key or not username:
        return jsonify({
            'success': False,
            'message': 'Key and username are required'
        }), 400

    if not client_hardware_id:
        return jsonify({
            'success': False,
            'message': 'Hardware ID is required'
        }), 400

    try:
        # Download product keys from S3
        keys_data = get_activation_data()
        if keys_data is None:
            return jsonify({
                'success': False,
                'message': 'Failed to access activation data'
            }), 500
    except Exception as e:
        logger.error(f"Failed to download product keys: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to access activation data'
        }), 500

    activations = keys_data.get('activations', {})
    key_entry = activations.get(key)

    if not key_entry:
        return jsonify({
            'success': False,
            'message': 'Invalid activation key'
        }), 400

    hardware_id = client_hardware_id

    logger.info(f"Activation attempt - Key: {key}, Username: {username}, Hardware ID: {hardware_id[:8]}...")

    # Check if this hardware is already activated with a different key
    for k, entry in activations.items():
        if entry.get('status') == 'activated' and entry.get('hardwareId') == hardware_id and k != key:
            return jsonify({
                'success': False, 
                'message': 'This device is already activated with a different key'
            }), 400

    # Get device ID from key entry
    device_id = key_entry.get('deviceId')
    if not device_id:
        return jsonify({
            'success': False, 
            'message': 'Device ID not found for this activation key'
        }), 400

    # Extract model number for file paths
    try:
        model_number = extract_model_number_from_device_id(device_id)
    except ValueError as e:
        logger.error(f"Invalid device ID format: {e}")
        return jsonify({
            'success': False,
            'message': 'Invalid device ID format'
        }), 400

    if key_entry.get('status') == 'activated':
        # Check if the key is activated on a different hardware
        if key_entry.get('hardwareId') != hardware_id:
            return jsonify({
                'success': False, 
                'message': 'This key is already activated on a different device'
            }), 400
        
        # CHECK EXPIRATION DATE BEFORE RE-LOGIN
        expiration_date = key_entry.get('expirationDate')
        if expiration_date and is_key_expired(expiration_date):
            logger.warning(f"Activation key {key} has expired. Expiration date: {expiration_date}")
            return jsonify({
                'success': False, 
                'message': 'Your activation key has expired'
            }), 403
        
        # Re-activation on same hardware - UPDATE loggedIn status to true
        if key_entry.get('username') == username:
            logger.info(f"Re-login detected for key {key} on same hardware")
            
            # Update loggedIn status
            if update_login_status(hardware_id, logged_in=True):
                logger.info(f"Updated loggedIn status to true for key {key}")
            else:
                logger.error(f"Failed to update login status for key {key}")
                return jsonify({
                    'success': False, 
                    'message': 'Failed to update login status'
                }), 500
            
            # Get correction values (use defaults if not present)
            length_correction = key_entry.get('length_correction', 0)
            wi_correction = key_entry.get('wi_correction', 0)
            ww_correction = key_entry.get('ww_correction', 1)
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'hardwareId': hardware_id,
                'deviceId': device_id,
                'modelNumber': model_number,
                'expirationDate': expiration_date,
                'length_correction': length_correction,
                'wi_correction': wi_correction,
                'ww_correction': ww_correction,
                'modelFiles': {
                    'sella': f'{model_number}_1.csv',
                    'nonSella': f'{model_number}_2.csv'
                }
            }), 200
        
        return jsonify({
            'success': False, 
            'message': 'Activation key already used by a different user'
        }), 400

    # First-time activation - Update the activation entry
    current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
    activated_at = current_time.strftime('%Y-%m-%d %H:%M:%S')
    expiration_date = calculate_expiration_date(current_time, years=1)  # Default: 1 year
    
    key_entry['status'] = 'activated'
    key_entry['username'] = username
    key_entry['hardwareId'] = hardware_id
    key_entry['activatedAt'] = activated_at
    key_entry['expirationDate'] = expiration_date
    key_entry['loggedIn'] = True
    key_entry['lastLoginAt'] = activated_at
    
    #Add correction fields with default values
    key_entry['length_correction'] = 0
    key_entry['wi_correction'] = 0
    key_entry['ww_correction'] = 1

    # Update totals
    keys_data['totalActivations'] = keys_data.get('totalActivations', 0) + 1
    keys_data['lastUpdated'] = activated_at

    # Upload updated JSON back to S3
    if update_activation_data(keys_data):
        logger.info(f"Successfully activated key {key} for user {username}")
        logger.info(f"Expiration date set to: {expiration_date}")
        logger.info(f"Correction fields initialized: length=0, wi=0, ww=1")
    else:
        logger.error(f"Failed to update activation data for key {key}")
        return jsonify({
            'success': False, 
            'message': 'Failed to update activation records'
        }), 500

    return jsonify({
        'success': True,
        'message': 'Activation successful',
        'hardwareId': hardware_id,
        'deviceId': device_id,
        'modelNumber': model_number,
        'expirationDate': expiration_date,
        'length_correction': 0,
        'wi_correction': 0,
        'ww_correction': 1,
        'modelFiles': {
            'sella': f'{model_number}_1.csv',
            'nonSella': f'{model_number}_2.csv'
        }
    }), 200


@activation_bp.route('/check-login-status', methods=['POST'])
def check_login_status():
    """
    Check if user is logged in by verifying S3 data
    Also checks if activation key has expired
    Returns correction values for logged-in users
    
    Returns:
        JSON: Login status and device information including correction values
    """
    data = request.get_json()
    client_hardware_id = data.get('hardwareId')

    if not client_hardware_id:
        return jsonify({
            'success': False,
            'message': 'Hardware ID is required'
        }), 400

    try:
        # Find activation by hardware ID
        key, entry = get_activation_by_hardware_id(client_hardware_id)
        
        if not entry:
            logger.info(f"No activation found for Hardware ID: {client_hardware_id[:8]}...")
            return jsonify({
                'success': True,
                'loggedIn': False,
                'message': 'Not logged in'
            }), 200
        
        # Check if logged in
        if entry.get('loggedIn') != True:
            return jsonify({
                'success': True,
                'loggedIn': False,
                'message': 'Not logged in'
            }), 200
        
        # CHECK EXPIRATION DATE
        expiration_date = entry.get('expirationDate')
        if expiration_date and is_key_expired(expiration_date):
            logger.warning(f"Activation key {key} has expired during login check. Expiration: {expiration_date}")
            
            # Auto-logout expired users
            update_login_status(client_hardware_id, logged_in=False)
            
            return jsonify({
                'success': False,
                'loggedIn': False,
                'message': 'Your activation key has expired'
            }), 403
        
        # Get device info
        device_id = entry.get('deviceId')
        try:
            model_number = extract_model_number_from_device_id(device_id)
        except ValueError:
            return jsonify({
                'success': False,
                'loggedIn': False,
                'message': 'Invalid device ID'
            }), 400

        # Get correction values (use defaults if not present)
        length_correction = entry.get('length_correction', 0)
        wi_correction = entry.get('wi_correction', 0)
        ww_correction = entry.get('ww_correction', 1)

        logger.info(f"User logged in - Hardware ID: {client_hardware_id[:8]}..., Device: {device_id}")
        logger.info(f"Corrections - length: {length_correction}, wi: {wi_correction}, ww: {ww_correction}")
        
        return jsonify({
            'success': True,
            'loggedIn': True,
            'deviceId': device_id,
            'username': entry.get('username'),
            'hardwareId': client_hardware_id,
            'modelNumber': model_number,
            'expirationDate': expiration_date,
            'length_correction': length_correction,
            'wi_correction': wi_correction,
            'ww_correction': ww_correction,
            'modelFiles': {
                'sella': f'{model_number}_1.csv',
                'nonSella': f'{model_number}_2.csv'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to check login status'
        }), 500


@activation_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout user by setting loggedIn to false in S3
    
    Returns:
        JSON: Logout status
    """
    data = request.get_json()
    client_hardware_id = data.get('hardwareId')

    if not client_hardware_id:
        return jsonify({
            'success': False,
            'message': 'Hardware ID is required'
        }), 400

    try:
        # Update login status
        if update_login_status(client_hardware_id, logged_in=False):
            logger.info(f"Successfully logged out hardware ID: {client_hardware_id[:8]}...")
            return jsonify({
                'success': True,
                'message': 'Logout successful'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No active session found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({
            'success': False, 
            'message': 'Failed to update logout status'
        }), 500


@activation_bp.route('/download-model/<device_id>/<model_type>', methods=['GET'])
def download_model(device_id, model_type):
    """
    Download model files through EC2 (EC2 authenticates with S3)
    This keeps user machines free of AWS credentials
    
    Args:
        device_id: Device ID (e.g., "AGS-2001")
        model_type: "sella" or "non-sella"
    
    Returns:
        File: CSV model file
    """
    try:
        # Extract model number
        model_number = extract_model_number_from_device_id(device_id)
        
        # Determine S3 key based on model type
        if model_type == 'sella':
            s3_key = f'{Config.MODELS_SELLA_FOLDER}/{model_number}_1.csv'
        elif model_type == 'non-sella':
            s3_key = f'{Config.MODELS_NONSELLA_FOLDER}/{model_number}_2.csv'
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid model type'
            }), 400
        
        # EC2 downloads from S3 using its own credentials
        s3_client = get_s3_client()
        
        # Stream the file directly to the client
        response = s3_client.get_object(Bucket=Config.S3_BUCKET_NAME, Key=s3_key)
        
        return Response(
            response['Body'].read(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={model_number}_{1 if model_type == "sella" else 2}.csv'
            }
        )
        
    except ValueError as e:
        logger.error(f"Invalid device ID: {e}")
        return jsonify({
            'success': False,
            'message': 'Invalid device ID format'
        }), 400
    except Exception as e:
        logger.error(f"Error downloading model: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to download model: {str(e)}'
        }), 500