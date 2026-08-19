import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import User, ProviderProfile, AdminLog
from extensions import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_provider():
            return redirect(url_for('provider.dashboard'))
        else:
            return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password. Please check your credentials.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'warning')
            return render_template('auth/login.html')

        if user.is_provider():
            profile = user.provider_profile
            if profile and profile.status == 'pending':
                flash('Your provider application is currently pending admin approval.', 'warning')
                return render_template('auth/login.html')
            elif profile and profile.status == 'rejected':
                flash('Your provider application was rejected by admin.', 'danger')
                return render_template('auth/login.html')
            elif profile and profile.status == 'suspended':
                flash('Your provider account has been suspended.', 'danger')
                return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif user.is_provider():
            return redirect(url_for('provider.dashboard'))
        else:
            return redirect(url_for('customer.dashboard'))

    return render_template('auth/login.html')


def detect_role_from_email(email):
    email_lower = email.lower()
    if 'admin' in email_lower:
        return 'admin', None
    elif 'fuel' in email_lower:
        return 'provider', 'fuel'
    elif 'mechanic' in email_lower:
        return 'provider', 'mechanic'
    elif 'tow' in email_lower or 'towing' in email_lower:
        return 'provider', 'tow'
    else:
        return 'customer', None

@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/register/customer', methods=['GET', 'POST'])
def register_customer():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_provider():
            return redirect(url_for('provider.dashboard'))
        else:
            return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password and confirm_password and password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_customer.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'warning')
            return render_template('auth/register_customer.html')

        license_number = request.form.get('license_number', '').strip()

        # Auto-detect role and provider type based on email keyword
        role, provider_type = detect_role_from_email(email)

        user = User(
            name=name,
            email=email,
            phone=phone,
            license_number=license_number if license_number else None,
            role=role
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == 'provider':
            provider_profile = ProviderProfile(
                user_id=user.id,
                provider_type=provider_type or 'mechanic',
                business_name=f"{name}'s {provider_type.capitalize() if provider_type else 'Service'} Station",
                license_number=f"LIC-{user.id:04d}",
                status='approved',
                is_online=True
            )
            db.session.add(provider_profile)

        db.session.commit()

        login_user(user)
        flash(f'Account created successfully! Redirecting to your {role.capitalize()} Panel.', 'success')

        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif user.is_provider():
            return redirect(url_for('provider.dashboard'))
        else:
            return redirect(url_for('customer.dashboard'))

    return render_template('auth/register_customer.html')


@auth_bp.route('/register/provider', methods=['GET', 'POST'])
def register_provider():
    if current_user.is_authenticated:
        return redirect(url_for('provider.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        provider_type = request.form.get('provider_type') # 'fuel', 'mechanic', 'tow'
        business_name = request.form.get('business_name', '').strip()
        license_number = request.form.get('license_number', '').strip()

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'warning')
            return render_template('auth/register_provider.html')

        # Handle Document Upload
        document_filename = None
        if 'document' in request.files:
            file = request.files['document']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                document_filename = f"doc_{email[:5]}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], document_filename))

        user = User(
            name=name,
            email=email,
            phone=phone,
            role='provider'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush() # Get user.id

        provider_profile = ProviderProfile(
            user_id=user.id,
            provider_type=provider_type,
            business_name=business_name,
            license_number=license_number,
            document_url=document_filename,
            status='approved',
            is_online=True
        )
        db.session.add(provider_profile)
        db.session.commit()

        login_user(user)
        flash('Provider account registered successfully! Welcome to MotoServe 360.', 'success')
        return redirect(url_for('provider.dashboard'))

    return render_template('auth/register_provider.html')


@auth_bp.route('/register/admin', methods=['GET', 'POST'])
def register_admin():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_admin.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'warning')
            return render_template('auth/register_admin.html')

        user = User(
            name=name,
            email=email,
            phone=phone,
            role='admin'
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Admin Account created successfully! Welcome to Admin Control Center.', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/register_admin.html')


@auth_bp.route('/logout')
@login_required
def logout():
    if current_user.is_provider() and current_user.provider_profile:
        current_user.provider_profile.is_online = False
        db.session.commit()

    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Password reset link sent to your registered email address (simulated).', 'info')
        else:
            flash('No user found with that email address.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('new_password')
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            flash('Your password has been reset successfully. Please login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid reset attempt.', 'danger')
    return render_template('auth/reset_password.html')
