import json
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from config import Config
import pytz
from utils.s3_utils import (
    download_json_from_s3, 
    upload_json_to_s3, 
    extract_model_number_from_device_id
)

activation_bp = Blueprint('activation', __name__)
logger = logging.getLogger(__name__)

def calculate_expiration_date(activation_date, years=1):
    """
    Calculate expiration date from activation date
    
    Args:
        activation_date: datetime object of activation
        years: number of years until expiration (default: 1)
    
    Returns:
        str: expiration date in 'YYYY-MM-DD HH:MM:SS' format
    """
    expiration = activation_date + timedelta(days=365 * years)
    return expiration.strftime('%Y-%m-%d %H:%M:%S')

def is_key_expired(expiration_date_str):
    """
    Check if activation key has expired
    
    Args:
        expiration_date_str: expiration date string in 'YYYY-MM-DD HH:MM:SS' format
    
    Returns:
        bool: True if expired, False otherwise
    """
    try:
        expiration_date = pytz.timezone("Asia/Kolkata").localize(datetime.strptime(expiration_date_str, '%Y-%m-%d %H:%M:%S'))
        current_date = datetime.now(pytz.timezone("Asia/Kolkata"))
        return current_date > expiration_date
    except Exception as e:
        logger.error(f"Error parsing expiration date: {e}")
        return True  # Treat invalid dates as expired for security

@activation_bp.route('/activate', methods=['POST'])
def activate_key():
    """
    Simplified activation endpoint that returns device info for client-side model download
    """
    data = request.get_json()
    key = data.get('key')
    username = data.get('username')
    client_hardware_id = data.get('hardwareId')

    if not key or not username:
        return jsonify({'success': False, 'message': 'Key and username are required'}), 400

    if not client_hardware_id:
        return jsonify({'success': False, 'message': 'Hardware ID is required'}), 400

    try:
        # Download product keys from S3
        keys_data = download_json_from_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY)
    except Exception as e:
        logger.error(f"Failed to download product keys: {e}")
        return jsonify({'success': False, 'message': 'Failed to access activation data'}), 500

    activations = keys_data.get('activations', {})
    key_entry = activations.get(key)

    if not key_entry:
        return jsonify({'success': False, 'message': 'Invalid activation key'}), 400

    hardware_id = client_hardware_id

    logger.info(f"Activation attempt - Key: {key}, Username: {username}, Hardware ID: {hardware_id}")

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
        return jsonify({'success': False, 'message': 'Invalid device ID format'}), 400

    if key_entry.get('status') == 'activated':
        # Check if the key is activated on a different hardware
        if key_entry.get('hardwareId') != hardware_id:
            return jsonify({
                'success': False, 
                'message': f'This key is already activated on a different device'
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
            
            # Update loggedIn status to true
            key_entry['loggedIn'] = True
            key_entry['lastLoginAt'] = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')
            
            # Update S3
            try:
                upload_json_to_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY, keys_data)
                logger.info(f"Updated loggedIn status to true for key {key}")
            except Exception as e:
                logger.error(f"Failed to update login status: {e}")
                return jsonify({
                    'success': False, 
                    'message': 'Failed to update login status'
                }), 500
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'hardwareId': hardware_id,
                'deviceId': device_id,
                'modelNumber': model_number,
                'expirationDate': expiration_date,
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
    key_entry['expirationDate'] = expiration_date  # NEW: Set expiration date
    key_entry['loggedIn'] = True
    key_entry['lastLoginAt'] = activated_at

    # Update totals
    keys_data['totalActivations'] = keys_data.get('totalActivations', 0) + 1
    keys_data['lastUpdated'] = activated_at

    # Upload updated JSON back to S3
    try:
        upload_json_to_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY, keys_data)
        logger.info(f"Successfully activated key {key} for user {username}")
        logger.info(f"Expiration date set to: {expiration_date}")
    except Exception as e:
        logger.error(f"Failed to update activation data: {e}")
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
    """
    data = request.get_json()
    client_hardware_id = data.get('hardwareId')

    if not client_hardware_id:
        return jsonify({'success': False, 'message': 'Hardware ID is required'}), 400

    try:
        # Download product keys from S3
        keys_data = download_json_from_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY)
    except Exception as e:
        logger.error(f"Failed to download product keys: {e}")
        return jsonify({'success': False, 'message': 'Failed to access activation data'}), 500

    activations = keys_data.get('activations', {})

    # Find the activation entry for this hardware ID
    for key, entry in activations.items():
        if (entry.get('status') == 'activated' and 
            entry.get('hardwareId') == client_hardware_id and
            entry.get('loggedIn') == True):
            
            # CHECK EXPIRATION DATE
            expiration_date = entry.get('expirationDate')
            if expiration_date and is_key_expired(expiration_date):
                logger.warning(f"Activation key {key} has expired during login check. Expiration: {expiration_date}")
                
                # Optionally: Auto-logout expired users
                entry['loggedIn'] = False
                try:
                    upload_json_to_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY, keys_data)
                except Exception as e:
                    logger.error(f"Failed to auto-logout expired user: {e}")
                
                return jsonify({
                    'success': False,
                    'loggedIn': False,
                    'message': 'Your activation key has expired'
                }), 403
            
            device_id = entry.get('deviceId')
            try:
                model_number = extract_model_number_from_device_id(device_id)
            except ValueError:
                continue

            logger.info(f"User logged in - Hardware ID: {client_hardware_id}, Device: {device_id}")
            
            return jsonify({
                'success': True,
                'loggedIn': True,
                'deviceId': device_id,
                'username': entry.get('username'),
                'hardwareId': client_hardware_id,
                'modelNumber': model_number,
                'expirationDate': expiration_date,
                'modelFiles': {
                    'sella': f'{model_number}_1.csv',
                    'nonSella': f'{model_number}_2.csv'
                }
            }), 200

    # No matching logged-in activation found
    logger.info(f"No active login found for Hardware ID: {client_hardware_id}")
    return jsonify({
        'success': True,
        'loggedIn': False,
        'message': 'Not logged in'
    }), 200


@activation_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout user by setting loggedIn to false in S3
    """
    data = request.get_json()
    client_hardware_id = data.get('hardwareId')

    if not client_hardware_id:
        return jsonify({'success': False, 'message': 'Hardware ID is required'}), 400

    try:
        # Download product keys from S3
        keys_data = download_json_from_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY)
    except Exception as e:
        logger.error(f"Failed to download product keys: {e}")
        return jsonify({'success': False, 'message': 'Failed to access activation data'}), 500

    activations = keys_data.get('activations', {})

    # Find and update the activation entry for this hardware ID
    found = False
    for key, entry in activations.items():
        if entry.get('status') == 'activated' and entry.get('hardwareId') == client_hardware_id:
            entry['loggedIn'] = False
            entry['lastLogoutAt'] = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')
            found = True
            logger.info(f"Logging out user - Key: {key}, Hardware ID: {client_hardware_id}")
            break

    if not found:
        return jsonify({'success': False, 'message': 'No active session found'}), 404

    # Upload updated JSON back to S3
    try:
        upload_json_to_s3(Config.S3_BUCKET_NAME, Config.PRODUCT_KEYS_KEY, keys_data)
        logger.info(f"Successfully logged out hardware ID: {client_hardware_id}")
    except Exception as e:
        logger.error(f"Failed to update logout status: {e}")
        return jsonify({
            'success': False, 
            'message': 'Failed to update logout status'
        }), 500

    return jsonify({
        'success': True,
        'message': 'Logout successful'
    }), 200


@activation_bp.route('/download-model/<device_id>/<model_type>', methods=['GET'])
def download_model(device_id, model_type):
    """
    Download model files through EC2 (EC2 authenticates with S3)
    This keeps user machines free of AWS credentials
    
    Args:
        device_id: Device ID (e.g., "AGS-2001")
        model_type: "sella" or "non-sella"
    """
    try:
        # Extract model number
        model_number = extract_model_number_from_device_id(device_id)
        
        # Determine S3 key based on model type
        if model_type == 'sella':
            s3_key = f'models_sella/{model_number}_1.csv'
        elif model_type == 'non-sella':
            s3_key = f'models_nonsella/{model_number}_2.csv'
        else:
            return jsonify({'success': False, 'message': 'Invalid model type'}), 400
        
        # EC2 downloads from S3 using its own credentials
        from utils.s3_utils import get_s3_client
        s3_client = get_s3_client()
        
        # Stream the file directly to the client
        response = s3_client.get_object(Bucket=Config.S3_BUCKET_NAME, Key=s3_key)
        
        from flask import Response
        return Response(
            response['Body'].read(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={model_number}_{1 if model_type == "sella" else 2}.csv'
            }
        )
        
    except ValueError as e:
        logger.error(f"Invalid device ID: {e}")
        return jsonify({'success': False, 'message': 'Invalid device ID format'}), 400
    except Exception as e:
        logger.error(f"Error downloading model: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Failed to download model: {str(e)}'}), 500