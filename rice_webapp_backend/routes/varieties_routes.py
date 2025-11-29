# routes/varieties_routes.py
import os
import json
import logging
from flask import Blueprint, jsonify, request
from config import Config

logger = logging.getLogger(__name__)

varieties_bp = Blueprint('varieties', __name__)

VARIETIES_FILE = os.path.join(Config.STATIC_ROOT, 'varieties.json')

def load_varieties_data():
    """Load varieties data from JSON file"""
    try:
        if os.path.exists(VARIETIES_FILE):
            with open(VARIETIES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"varieties": []}
    except Exception as e:
        logger.error(f"Error loading varieties data: {e}")
        return {"varieties": []}

def save_varieties_data(data):
    """Save varieties data to JSON file"""
    try:
        # Ensure static directory exists
        os.makedirs(Config.STATIC_ROOT, exist_ok=True)

        with open(VARIETIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Varieties data saved to {VARIETIES_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving varieties data: {e}")
        return False

@varieties_bp.route('/varieties', methods=['GET'])
def get_varieties():
    """Get all varieties data"""
    try:
        data = load_varieties_data()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error getting varieties: {e}")
        return jsonify({"error": "Failed to load varieties data"}), 500

@varieties_bp.route('/varieties', methods=['POST'])
def save_varieties():
    """Save varieties data"""
    try:
        data = request.get_json()
        if not data or 'varieties' not in data:
            return jsonify({"error": "Invalid data format"}), 400

        if save_varieties_data(data):
            return jsonify({"message": "Varieties data saved successfully"}), 200
        else:
            return jsonify({"error": "Failed to save varieties data"}), 500
    except Exception as e:
        logger.error(f"Error saving varieties: {e}")
        return jsonify({"error": "Failed to save varieties data"}), 500

@varieties_bp.route('/varieties/<variety_name>', methods=['DELETE'])
def delete_variety(variety_name):
    """Delete a variety and all its sub-varieties"""
    try:
        data = load_varieties_data()
        data['varieties'] = [v for v in data['varieties'] if v['name'] != variety_name]

        if save_varieties_data(data):
            return jsonify({"message": f"Variety '{variety_name}' deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete variety"}), 500
    except Exception as e:
        logger.error(f"Error deleting variety: {e}")
        return jsonify({"error": "Failed to delete variety"}), 500

@varieties_bp.route('/varieties/<variety_name>', methods=['PUT'])
def update_variety(variety_name):
    """Update a variety name"""
    try:
        data = load_varieties_data()
        variety = next((v for v in data['varieties'] if v['name'] == variety_name), None)

        if not variety:
            return jsonify({"error": "Variety not found"}), 404

        update_data = request.get_json()
        if not update_data or 'name' not in update_data:
            return jsonify({"error": "Invalid data format"}), 400

        new_name = update_data['name']
        # Check if new name already exists (if different from current)
        if new_name != variety_name and any(v['name'] == new_name for v in data['varieties']):
            return jsonify({"error": "Variety name already exists"}), 400

        variety['name'] = new_name

        if save_varieties_data(data):
            return jsonify({"message": f"Variety updated successfully", "variety": variety}), 200
        else:
            return jsonify({"error": "Failed to update variety"}), 500
    except Exception as e:
        logger.error(f"Error updating variety: {e}")
        return jsonify({"error": "Failed to update variety"}), 500

@varieties_bp.route('/varieties/<variety_name>/<sub_variety_name>', methods=['PUT'])
def update_sub_variety(variety_name, sub_variety_name):
    """Update a sub-variety name"""
    try:
        data = load_varieties_data()
        variety = next((v for v in data['varieties'] if v['name'] == variety_name), None)

        if not variety:
            return jsonify({"error": "Variety not found"}), 404

        sub_variety = next((s for s in variety['subVarieties'] if s['name'] == sub_variety_name), None)

        if not sub_variety:
            return jsonify({"error": "Sub-variety not found"}), 404

        update_data = request.get_json()
        if not update_data or 'name' not in update_data:
            return jsonify({"error": "Invalid data format"}), 400

        # Update sub-variety name
        new_name = update_data['name']
        # Check if new name already exists in this variety
        if new_name != sub_variety_name and any(s['name'] == new_name for s in variety['subVarieties']):
            return jsonify({"error": "Sub-variety name already exists"}), 400
        sub_variety['name'] = new_name

        if save_varieties_data(data):
            return jsonify({"message": f"Sub-variety updated successfully", "subVariety": sub_variety}), 200
        else:
            return jsonify({"error": "Failed to update sub-variety"}), 500
    except Exception as e:
        logger.error(f"Error updating sub-variety: {e}")
        return jsonify({"error": "Failed to update sub-variety"}), 500

@varieties_bp.route('/varieties/<variety_name>/<sub_variety_name>/qualities', methods=['POST'])
def add_quality(variety_name, sub_variety_name):
    """Add a quality-length pair to a sub-variety"""
    try:
        data = load_varieties_data()
        variety = next((v for v in data['varieties'] if v['name'] == variety_name), None)

        if not variety:
            return jsonify({"error": "Variety not found"}), 404

        sub_variety = next((s for s in variety['subVarieties'] if s['name'] == sub_variety_name), None)

        if not sub_variety:
            return jsonify({"error": "Sub-variety not found"}), 404

        quality_data = request.get_json()
        if not quality_data or 'quality' not in quality_data or 'length' not in quality_data or 'chalkyPercentage' not in quality_data:
            return jsonify({"error": "Invalid data format"}), 400

        # Initialize qualities array if it doesn't exist
        if 'qualities' not in sub_variety:
            sub_variety['qualities'] = []

        # Check if quality already exists
        if any(q['quality'] == quality_data['quality'] for q in sub_variety['qualities']):
            return jsonify({"error": "Quality already exists for this sub-variety"}), 400

        sub_variety['qualities'].append({
            'quality': quality_data['quality'],
            'length': quality_data['length'],
            'chalkyPercentage': quality_data['chalkyPercentage']
        })

        if save_varieties_data(data):
            return jsonify({"message": "Quality added successfully", "subVariety": sub_variety}), 200
        else:
            return jsonify({"error": "Failed to add quality"}), 500
    except Exception as e:
        logger.error(f"Error adding quality: {e}")
        return jsonify({"error": "Failed to add quality"}), 500

@varieties_bp.route('/varieties/<variety_name>/<sub_variety_name>/qualities/<quality>', methods=['PUT'])
def update_quality(variety_name, sub_variety_name, quality):
    """Update a quality-length pair in a sub-variety"""
    try:
        data = load_varieties_data()
        variety = next((v for v in data['varieties'] if v['name'] == variety_name), None)

        if not variety:
            return jsonify({"error": "Variety not found"}), 404

        sub_variety = next((s for s in variety['subVarieties'] if s['name'] == sub_variety_name), None)

        if not sub_variety:
            return jsonify({"error": "Sub-variety not found"}), 404

        if 'qualities' not in sub_variety:
            return jsonify({"error": "No qualities found"}), 404

        quality_item = next((q for q in sub_variety['qualities'] if q['quality'] == quality), None)

        if not quality_item:
            return jsonify({"error": "Quality not found"}), 404

        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "Invalid data format"}), 400

        if 'quality' in update_data:
            new_quality = update_data['quality']
            # Check if new quality name conflicts
            if new_quality != quality and any(q['quality'] == new_quality for q in sub_variety['qualities']):
                return jsonify({"error": "Quality name already exists"}), 400
            quality_item['quality'] = new_quality

        if 'length' in update_data:
            quality_item['length'] = update_data['length']

        if 'chalkyPercentage' in update_data:
            quality_item['chalkyPercentage'] = update_data['chalkyPercentage']

        if save_varieties_data(data):
            return jsonify({"message": "Quality updated successfully", "subVariety": sub_variety}), 200
        else:
            return jsonify({"error": "Failed to update quality"}), 500
    except Exception as e:
        logger.error(f"Error updating quality: {e}")
        return jsonify({"error": "Failed to update quality"}), 500

@varieties_bp.route('/varieties/<variety_name>/<sub_variety_name>/qualities/<quality>', methods=['DELETE'])
def delete_quality(variety_name, sub_variety_name, quality):
    """Delete a quality-length pair from a sub-variety"""
    try:
        data = load_varieties_data()
        variety = next((v for v in data['varieties'] if v['name'] == variety_name), None)

        if not variety:
            return jsonify({"error": "Variety not found"}), 404

        sub_variety = next((s for s in variety['subVarieties'] if s['name'] == sub_variety_name), None)

        if not sub_variety:
            return jsonify({"error": "Sub-variety not found"}), 404

        if 'qualities' not in sub_variety:
            return jsonify({"error": "No qualities found"}), 404

        sub_variety['qualities'] = [q for q in sub_variety['qualities'] if q['quality'] != quality]

        if save_varieties_data(data):
            return jsonify({"message": "Quality deleted successfully", "subVariety": sub_variety}), 200
        else:
            return jsonify({"error": "Failed to delete quality"}), 500
    except Exception as e:
        logger.error(f"Error deleting quality: {e}")
        return jsonify({"error": "Failed to delete quality"}), 500

@varieties_bp.route('/varieties/<variety_name>/<sub_variety_name>', methods=['DELETE'])
def delete_sub_variety(variety_name, sub_variety_name):
    """Delete a sub-variety"""
    try:
        data = load_varieties_data()
        variety = next((v for v in data['varieties'] if v['name'] == variety_name), None)

        if variety:
            variety['subVarieties'] = [s for s in variety['subVarieties'] if s['name'] != sub_variety_name]

            if save_varieties_data(data):
                return jsonify({"message": f"Sub-variety '{sub_variety_name}' deleted successfully"}), 200
            else:
                return jsonify({"error": "Failed to delete sub-variety"}), 500
        else:
            return jsonify({"error": "Variety not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting sub-variety: {e}")
        return jsonify({"error": "Failed to delete sub-variety"}), 500
