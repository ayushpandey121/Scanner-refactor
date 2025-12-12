# api/routes/__init__.py
"""
API routes module
Individual blueprint imports
"""

from .analysis import analysis_bp
from .activation import activation_bp
from .files import file_bp
from .health import health_bp
from .reports import report_bp
from .varieties import varieties_bp
from .sample_details import sample_details_bp
from .rgb import rgb_bp

__all__ = [
    'analysis_bp',
    'activation_bp',
    'file_bp',
    'health_bp',
    'report_bp',
    'varieties_bp',
    'sample_details_bp',
    'rgb_bp'
]