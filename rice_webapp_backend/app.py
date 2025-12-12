# app.py (Refactored)
"""
Flask application factory
Uses refactored modular architecture
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS

from config.settings import Config
from api.routes import (
    analysis_bp,
    activation_bp,
    file_bp,
    health_bp,
    report_bp,
    varieties_bp,
    sample_details_bp,
    rgb_bp
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _configure_file_logging():
    """
    Persist logs even when running as a hidden console executable
    Creates rotating log files in the configured LOG_FOLDER
    """
    try:
        os.makedirs(Config.LOG_FOLDER, exist_ok=True)
        log_path = os.path.join(Config.LOG_FOLDER, 'backend.log')
        
        handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        logging.getLogger().addHandler(handler)
        logger.info(f"File logging enabled at {log_path}")
    except Exception as exc:
        logger.warning(f"Failed to initialize file logging: {exc}")


# Configure file logging on import
_configure_file_logging()


def create_app():
    """
    Application factory pattern
    Creates and configures Flask application with all routes
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Enable CORS
    CORS(app, origins=Config.CORS_ORIGINS)

    # Create necessary directories
    logger.info("Creating application directories...")
    Config.create_directories()

    # Register blueprints
    logger.info("Registering blueprints...")
    app.register_blueprint(health_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(activation_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(varieties_bp)
    app.register_blueprint(sample_details_bp)
    app.register_blueprint(rgb_bp)

    logger.info("Application initialized successfully")
    logger.info(f"All files will be stored in: {Config.STATIC_ROOT}")
    logger.info(f"Models folder: {os.path.join(Config.BASE_DIR, 'models')}")

    return app


if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting Flask application on {Config.HOST}:{Config.PORT}...")
    logger.info(f"Debug mode: {Config.DEBUG}")
    
    try:
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG
        )
    except Exception as exc:
        logger.exception(f"Backend failed to start: {exc}")
        raise