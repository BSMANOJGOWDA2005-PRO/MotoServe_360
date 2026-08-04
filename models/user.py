from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer') # 'customer', 'provider', 'admin'
    avatar = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True, cascade="all, delete-orphan")
    provider_profile = db.relationship('ProviderProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    customer_requests = db.relationship('ServiceRequest', foreign_keys='ServiceRequest.customer_id', backref='customer', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade="all, delete-orphan")
    orders = db.relationship('Order', backref='customer', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_provider(self):
        return self.role == 'provider'

    def is_customer(self):
        return self.role == 'customer'

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class ProviderProfile(db.Model):
    __tablename__ = 'providers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    provider_type = db.Column(db.String(30), nullable=False) # 'fuel', 'mechanic', 'tow'
    business_name = db.Column(db.String(150), nullable=False)
    license_number = db.Column(db.String(50), nullable=False)
    document_url = db.Column(db.String(255), nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    current_lat = db.Column(db.Float, default=12.9716) # Default Bengaluru coordinates
    current_lng = db.Column(db.Float, default=77.5946)
    rating = db.Column(db.Float, default=5.0)
    total_ratings = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending') # 'pending', 'approved', 'rejected', 'suspended'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assigned_requests = db.relationship('ServiceRequest', foreign_keys='ServiceRequest.provider_id', backref='provider_profile', lazy=True)
    reviews = db.relationship('Review', backref='provider_profile', lazy=True)

    def update_rating(self, new_rating):
        total_score = (self.rating * self.total_ratings) + new_rating
        self.total_ratings += 1
        self.rating = round(total_score / self.total_ratings, 1)

    def __repr__(self):
        return f"<ProviderProfile {self.business_name} ({self.provider_type}) - {self.status}>"
