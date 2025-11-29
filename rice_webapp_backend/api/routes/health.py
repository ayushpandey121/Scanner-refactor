# api/routes/health.py
"""
Health check endpoint
Simple endpoint to verify server is running
"""

import time
from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    Returns:
        JSON: Status and timestamp
    """
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    }), 200