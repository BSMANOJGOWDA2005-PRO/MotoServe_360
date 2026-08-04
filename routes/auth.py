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

    role_tab = request.args.get('role', 'customer')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password. Please check your credentials.', 'danger')
            return render_template('auth/login.html', role_tab=role_tab)

        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'warning')
            return render_template('auth/login.html', role_tab=role_tab)

        if user.is_provider():
            profile = user.provider_profile
            if profile and profile.status == 'pending':
                flash('Your provider application is currently pending admin approval.', 'warning')
                return render_template('auth/login.html', role_tab='provider')
            elif profile and profile.status == 'rejected':
                flash('Your provider application was rejected by admin.', 'danger')
                return render_template('auth/login.html', role_tab='provider')
            elif profile and profile.status == 'suspended':
                flash('Your provider account has been suspended.', 'danger')
                return render_template('auth/login.html', role_tab='provider')

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

    return render_template('auth/login.html', role_tab=role_tab)


@auth_bp.route('/register/customer', methods=['GET', 'POST'])
def register_customer():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_customer.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'warning')
            return render_template('auth/register_customer.html')

        user = User(
            name=name,
            email=email,
            phone=phone,
            role='customer'
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Account created successfully! Welcome to MotoServe 360.', 'success')
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
            status='pending' # Requires admin approval
        )
        db.session.add(provider_profile)
        db.session.commit()

        flash('Registration submitted! Your provider application is pending admin approval.', 'info')
        return redirect(url_for('auth.login', role='provider'))

    return render_template('auth/register_provider.html')


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
