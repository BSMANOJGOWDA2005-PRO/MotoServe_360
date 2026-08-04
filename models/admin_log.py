from datetime import datetime
from extensions import db

class AdminLog(db.Model):
    __tablename__ = 'admin_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    admin = db.relationship('User', foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AdminLog {self.action} by Admin {self.admin_id}>"
