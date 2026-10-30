import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func

from models import (
    User, ProviderProfile, ServiceRequest, Payment, Review, Notification
)
from services import create_notification, calculate_haversine_distance
from extensions import db

provider_bp = Blueprint('provider', __name__, url_prefix='/provider')

def provider_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_provider():
            flash('Access denied. Provider panel only.', 'danger')
            return redirect(url_for('auth.login', role='provider'))
        profile = current_user.provider_profile
        if not profile or profile.status != 'approved':
            flash('Your account is not approved to access provider features.', 'warning')
            return redirect(url_for('auth.login', role='provider'))
        return f(*args, **kwargs)
    return decorated_function

@provider_bp.route('/dashboard')
@login_required
@provider_required
def dashboard():
    profile = current_user.provider_profile

    active_job = ServiceRequest.query.filter(
        ServiceRequest.provider_id == profile.id,
        ServiceRequest.status.in_(['accepted', 'travelling', 'reached', 'working'])
    ).first()

    pending_requests = ServiceRequest.query.filter(
        ServiceRequest.service_type == profile.provider_type,
        ServiceRequest.status == 'pending'
    ).order_by(ServiceRequest.created_at.desc()).all()

    completed_jobs_count = ServiceRequest.query.filter_by(provider_id=profile.id, status='completed').count()
    
    # Calculate Total Earnings (Fuel charges + delivery fees; excluding platform fee)
    completed_requests = ServiceRequest.query.filter_by(provider_id=profile.id, status='completed').all()
    total_earnings = round(sum(req.provider_payout for req in completed_requests), 2)

    return render_template(
        'provider/dashboard.html',
        profile=profile,
        active_job=active_job,
        pending_requests=pending_requests,
        completed_jobs_count=completed_jobs_count,
        total_earnings=total_earnings
    )

@provider_bp.route('/toggle-online', methods=['POST'])
@login_required
@provider_required
def toggle_online():
    profile = current_user.provider_profile
    profile.is_online = not profile.is_online
    db.session.commit()
    status_str = "ONLINE" if profile.is_online else "OFFLINE"
    flash(f'You are now {status_str} and ready to receive requests.', 'success' if profile.is_online else 'info')
    return redirect(url_for('provider.dashboard'))

@provider_bp.route('/update-location', methods=['POST'])
@login_required
@provider_required
def update_location():
    profile = current_user.provider_profile
    data = request.get_json() or {}
    lat = data.get('lat')
    lng = data.get('lng')
    if lat and lng:
        profile.current_lat = float(lat)
        profile.current_lng = float(lng)
        db.session.commit()
        return jsonify({'status': 'updated', 'lat': lat, 'lng': lng})
    return jsonify({'status': 'invalid_data'}), 400

@provider_bp.route('/requests')
@login_required
@provider_required
def requests_list():
    profile = current_user.provider_profile
    pending_requests = ServiceRequest.query.filter(
        ServiceRequest.service_type == profile.provider_type,
        ServiceRequest.status == 'pending'
    ).order_by(ServiceRequest.created_at.desc()).all()
    return render_template('provider/requests.html', requests=pending_requests, profile=profile)

@provider_bp.route('/request/accept/<int:request_id>', methods=['POST'])
@login_required
@provider_required
def accept_request(request_id):
    profile = current_user.provider_profile
    req = ServiceRequest.query.filter_by(id=request_id, status='pending').first_or_404()

    req.provider_id = profile.id
    req.status = 'accepted'
    db.session.commit()

    create_notification(req.customer_id, "Provider Accepted", f"{profile.business_name} has accepted your service request #{req.request_number}!", link=url_for('customer.tracking', request_id=req.id))
    flash('Service request accepted! Head over to Active Job.', 'success')
    return redirect(url_for('provider.active_job', request_id=req.id))

@provider_bp.route('/request/reject/<int:request_id>', methods=['POST'])
@login_required
@provider_required
def reject_request(request_id):
    flash('Request declined.', 'info')
    return redirect(url_for('provider.dashboard'))

@provider_bp.route('/job/<int:request_id>')
@login_required
@provider_required
def active_job(request_id):
    profile = current_user.provider_profile
    req = ServiceRequest.query.filter_by(id=request_id, provider_id=profile.id).first_or_404()
    return render_template('provider/active_job.html', req=req, profile=profile)

@provider_bp.route('/job/update-status/<int:request_id>', methods=['POST'])
@login_required
@provider_required
def update_status(request_id):
    profile = current_user.provider_profile
    req = ServiceRequest.query.filter_by(id=request_id, provider_id=profile.id).first_or_404()
    new_status = request.form.get('status')

    # Allowed status progression: accepted -> travelling -> reached -> working -> completed / cancelled
    valid_statuses = ['accepted', 'travelling', 'reached', 'working', 'completed', 'cancelled']
    if new_status in valid_statuses:
        req.status = new_status
        db.session.commit()

        status_messages = {
            'travelling': f"Provider {profile.business_name} is on the way!",
            'reached': f"Provider {profile.business_name} has arrived at your location.",
            'working': f"Provider {profile.business_name} has started work on your vehicle.",
            'completed': f"Service #{req.request_number} completed! Please review and process payment.",
            'cancelled': f"Service #{req.request_number} was cancelled."
        }
        if new_status in status_messages:
            create_notification(req.customer_id, f"Service Status: {new_status.title()}", status_messages[new_status], link=url_for('customer.tracking', request_id=req.id))

        flash(f'Status updated to {new_status.upper()}', 'success')

    return redirect(url_for('provider.active_job', request_id=req.id))

@provider_bp.route('/earnings')
@login_required
@provider_required
def earnings():
    profile = current_user.provider_profile
    completed_jobs = ServiceRequest.query.filter_by(provider_id=profile.id, status='completed').order_by(ServiceRequest.updated_at.desc()).all()
    
    today = datetime.utcnow().date()
    start_of_month = today.replace(day=1)

    daily_earnings = round(sum(job.provider_payout for job in completed_jobs if job.updated_at.date() == today), 2)
    monthly_earnings = round(sum(job.provider_payout for job in completed_jobs if job.updated_at.date() >= start_of_month), 2)
    total_earnings = round(sum(job.provider_payout for job in completed_jobs), 2)

    reviews = Review.query.filter_by(provider_id=profile.id).order_by(Review.created_at.desc()).all()

    return render_template(
        'provider/earnings.html',
        profile=profile,
        completed_jobs=completed_jobs,
        daily_earnings=daily_earnings,
        monthly_earnings=monthly_earnings,
        total_earnings=total_earnings,
        reviews=reviews
    )

@provider_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@provider_required
def profile():
    profile = current_user.provider_profile
    if request.method == 'POST':
        profile.business_name = request.form.get('business_name')
        profile.license_number = request.form.get('license_number')
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')

        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                avatar_filename = f"avatar_provider_{current_user.id}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], avatar_filename))
                current_user.avatar = avatar_filename

        db.session.commit()
        flash('Provider profile updated successfully!', 'success')
        return redirect(url_for('provider.profile'))
    return render_template('provider/profile.html', profile=profile)
