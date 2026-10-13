from .main import main_bp
from .auth import auth_bp
from .customer import customer_bp
from .provider import provider_bp
from .admin import admin_bp
from .api import api_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'customer_bp',
    'provider_bp',
    'admin_bp',
    'api_bp'
]
