from datetime import datetime
import uuid
from extensions import db

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(36), default=lambda: f"TXN-{uuid.uuid4().hex[:10].upper()}", unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Can be for a service request or an e-commerce order
    request_id = db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(30), nullable=False) # 'upi', 'card', 'wallet', 'cash'
    status = db.Column(db.String(20), default='completed') # 'pending', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Payment {self.transaction_id} - ₹{self.amount} ({self.status})>"
