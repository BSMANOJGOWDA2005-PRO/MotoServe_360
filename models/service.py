from datetime import datetime
import uuid
from extensions import db

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(36), default=lambda: f"REQ-{uuid.uuid4().hex[:8].upper()}", unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    
    service_type = db.Column(db.String(20), nullable=False) # 'fuel', 'repair', 'tow'
    # Statuses: 'pending', 'accepted', 'travelling', 'reached', 'working', 'completed', 'cancelled'
    status = db.Column(db.String(20), default='pending', nullable=False)
    
    pickup_address = db.Column(db.String(255), nullable=False)
    locality = db.Column(db.String(100), nullable=True)
    pickup_lat = db.Column(db.Float, nullable=False)
    pickup_lng = db.Column(db.Float, nullable=False)
    
    # Selected Provider Snapshot (for registered or external OSM stations)
    provider_name = db.Column(db.String(150), nullable=True)
    provider_lat = db.Column(db.Float, nullable=True)
    provider_lng = db.Column(db.Float, nullable=True)
    provider_address = db.Column(db.String(255), nullable=True)
    provider_phone = db.Column(db.String(50), nullable=True)
    provider_source = db.Column(db.String(20), default='registered') # 'registered' or 'osm'
    distance_km = db.Column(db.Float, nullable=True) # Straight-line distance from customer to provider
    
    drop_address = db.Column(db.String(255), nullable=True) # Used for towing
    drop_lat = db.Column(db.Float, nullable=True)
    drop_lng = db.Column(db.Float, nullable=True)
    
    is_emergency = db.Column(db.Boolean, default=False)
    scheduled_at = db.Column(db.DateTime, default=datetime.utcnow)
    service_notes = db.Column(db.Text, nullable=True)
    
    estimated_fee = db.Column(db.Float, default=0.0)
    final_amount = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='unpaid') # 'unpaid', 'paid'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Specific details relationships
    fuel_detail = db.relationship('FuelDetails', backref='request', uselist=False, cascade="all, delete-orphan")
    repair_detail = db.relationship('RepairDetails', backref='request', uselist=False, cascade="all, delete-orphan")
    tow_detail = db.relationship('TowDetails', backref='request', uselist=False, cascade="all, delete-orphan")
    
    payments = db.relationship('Payment', backref='service_request', lazy=True)
    chat_messages = db.relationship('ChatMessage', backref='service_request', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='service_request', lazy=True)

    def __repr__(self):
        return f"<ServiceRequest {self.request_number} ({self.service_type}) - {self.status}>"


class FuelDetails(db.Model):
    __tablename__ = 'fuel_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=False, unique=True)
    fuel_type = db.Column(db.String(20), nullable=False) # 'petrol', 'diesel', 'cng'
    quantity_litres = db.Column(db.Float, nullable=False)
    fuel_price_per_litre = db.Column(db.Float, nullable=False, default=100.0)
    delivery_fee = db.Column(db.Float, nullable=False, default=50.0)


class RepairDetails(db.Model):
    __tablename__ = 'repair_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=False, unique=True)
    problem_category = db.Column(db.String(50), nullable=False) # 'Engine', 'Brakes', 'Electrical', 'Tires', 'General'
    problem_description = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(255), nullable=True)
    mechanic_notes = db.Column(db.Text, nullable=True)


class TowDetails(db.Model):
    __tablename__ = 'tow_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=False, unique=True)
    towing_reason = db.Column(db.String(100), nullable=False) # 'Breakdown', 'Accident', 'Flat Tire', 'Out of Fuel'
    distance_km = db.Column(db.Float, nullable=False, default=5.0)
    rate_per_km = db.Column(db.Float, nullable=False, default=30.0)
    base_charge = db.Column(db.Float, nullable=False, default=200.0)
