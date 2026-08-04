import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'motoserve360-super-secret-key-2026'
    
    # SQLite Database Configuration
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(INSTANCE_DIR, 'database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads Configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload limit
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Flask-Session
    SESSION_TYPE = 'filesystem'
    
    # Flask-Mail (Mocked/Configurable)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'noreply@motoserve360.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'secret')
    MAIL_DEFAULT_SENDER = ('MotoServe 360', 'noreply@motoserve360.com')
