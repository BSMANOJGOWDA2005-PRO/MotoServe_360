from datetime import datetime
from extensions import db

class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('service_requests.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id])

    def __repr__(self):
        return f"<Review {self.rating} Stars by Customer {self.customer_id}>"
