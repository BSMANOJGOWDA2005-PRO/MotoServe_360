from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import Product, Review, ProviderProfile

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    featured_products = Product.query.filter_by(is_active=True).limit(4).all()
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    providers_count = ProviderProfile.query.filter_by(status='approved').count()
    return render_template(
        'index.html',
        featured_products=featured_products,
        recent_reviews=recent_reviews,
        providers_count=providers_count
    )

@main_bp.route('/services')
def services():
    return render_template('index.html', scroll_to='services')

@main_bp.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    flash(f"Thank you {name}! Your message has been received. Our support team will get back to you shortly.", "success")
    return redirect(url_for('main.index'))
