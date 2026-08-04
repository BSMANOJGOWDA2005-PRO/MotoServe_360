from datetime import datetime
import uuid
from extensions import db

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False) # 'Engine Oil', 'Battery', 'Tyres', 'Helmet', 'Accessories', 'Brake Pads', 'Lubricants', 'Cleaning Kit'
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=10)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), default='product_default.png')
    discount_percentage = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade="all, delete-orphan")
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    @property
    def final_price(self):
        if self.discount_percentage > 0:
            return round(self.price * (1 - self.discount_percentage / 100.0), 2)
        return self.price

    def __repr__(self):
        return f"<Product {self.name} - ₹{self.price}>"


class CartItem(db.Model):
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    @property
    def item_total(self):
        return round(self.product.final_price * self.quantity, 2)


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(36), default=lambda: f"ORD-{uuid.uuid4().hex[:8].upper()}", unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='pending') # 'pending', 'paid', 'failed'
    payment_method = db.Column(db.String(30), nullable=False) # 'upi', 'card', 'wallet', 'cash'
    shipping_address = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending') # 'pending', 'processing', 'shipped', 'delivered', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    payments = db.relationship('Payment', backref='order', lazy=True)

    def __repr__(self):
        return f"<Order {self.order_number} - ₹{self.total_amount}>"


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    @property
    def subtotal(self):
        return round(self.unit_price * self.quantity, 2)
