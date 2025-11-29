# api/routes/reports.py
"""
Report routes
Fetches analysis logs and provides summary data
"""

import os
import logging
from flask import Blueprint, jsonify
from config.settings import Config
from storage.local_storage import load_json

logger = logging.getLogger(__name__)

report_bp = Blueprint('report', __name__)


@report_bp.route('/get_logs', methods=['GET'])
def get_logs():
    """
    Fetch all log data from static/logs directory
    
    Returns:
        JSON: List of log summaries sorted by timestamp
    """
    try:
        logs_data = []
        logs_dir = Config.LOG_FOLDER

        if not os.path.exists(logs_dir):
            return jsonify({"error": "Logs directory not found"}), 404

        # Get all JSON files in logs directory
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.json')]

        for log_file in log_files:
            try:
                log_path = os.path.join(logs_dir, log_file)
                log_data = load_json(log_path)
                
                if not log_data:
                    continue

                # Extract required fields for summary
                if 'statistics' in log_data:
                    stats = log_data['statistics']
                    entry = {
                        'timestamp': log_data.get('timestamp', ''),
                        'average_length': stats.get('avg_length', 0),
                        'average_width': stats.get('avg_breadth', 0),
                        'lb_ratio': round(
                            stats.get('avg_length', 0) / max(stats.get('avg_breadth', 1), 0.01),
                            2
                        ),
                        'broken': stats.get('broken_count', 0),
                        'chalky': stats.get('chalky_count', 0),
                        'discolor': stats.get('discolored_count', 0),
                        'full_data': log_data  # Include full log data for loading into Result page
                    }
                    logs_data.append(entry)
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {str(e)}")
                continue

        # Sort by timestamp descending (newest first)
        logs_data.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify({"logs": logs_data}), 200

    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        return jsonify({"error": "Failed to fetch logs"}), 500