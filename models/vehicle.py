from datetime import datetime
from extensions import db

class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    make = db.Column(db.String(50), nullable=False) # e.g. Toyota, Honda, Royal Enfield
    model = db.Column(db.String(50), nullable=False) # e.g. Camry, Civic, Classic 350
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(30), nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False) # 'petrol', 'diesel', 'cng', 'electric'
    vehicle_type = db.Column(db.String(20), default='car') # 'car', 'bike', 'truck'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    service_requests = db.relationship('ServiceRequest', backref='vehicle', lazy=True)

    def __repr__(self):
        return f"<Vehicle {self.make} {self.model} ({self.license_plate})>"
