# app.py
import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from config import Config
from routes.analysis_routes import analysis_bp
from routes.file_routes import file_bp
from routes.health_routes import health_bp
from routes.activation_routes import activation_bp
from routes.report_routes import report_bp
from routes.varieties_routes import varieties_bp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _configure_file_logging():
    """Persist logs even when running as a hidden console executable."""
    try:
        os.makedirs(Config.LOG_FOLDER, exist_ok=True)
        log_path = os.path.join(Config.LOG_FOLDER, 'backend.log')
        handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        logger.info("File logging enabled at %s", log_path)
    except Exception as exc:
        logger.warning("Failed to initialise file logging: %s", exc)


_configure_file_logging()


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Enable CORS
    CORS(app, origins=Config.CORS_ORIGINS)

    # Create necessary directories
    Config.create_directories()

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(activation_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(varieties_bp)

    logger.info("Application initialized successfully")
    logger.info(f"All files will be stored in: {Config.STATIC_ROOT}")

    return app


if __name__ == "__main__":
    app = create_app()
    logger.info("Starting Flask application...")
    try:
        app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    except Exception as exc:
        logger.exception("Backend failed to start: %s", exc)
        raise
