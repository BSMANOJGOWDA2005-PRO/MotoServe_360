import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

from models import (
    User, Vehicle, ServiceRequest, FuelDetails, RepairDetails, TowDetails,
    Product, CartItem, Order, OrderItem, Payment, Notification, ChatMessage, Review, ProviderProfile
)
from services import (
    find_nearest_provider, calculate_haversine_distance, create_notification,
    generate_invoice_html, validate_coordinates, format_distance,
    get_nearby_fuel, get_nearby_repair, get_nearby_towing
)
from extensions import db

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

def customer_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_customer():
            flash('Access denied. Customer panel only.', 'danger')
            return redirect(url_for('auth.login', role='customer'))
        return f(*args, **kwargs)
    return decorated_function

@customer_bp.route('/dashboard')
@login_required
@customer_required
def dashboard():
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    active_requests = ServiceRequest.query.filter(
        ServiceRequest.customer_id == current_user.id,
        ServiceRequest.status.in_(['pending', 'accepted', 'travelling', 'reached', 'working'])
    ).order_by(ServiceRequest.created_at.desc()).all()
    
    recent_orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).limit(3).all()
    recent_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template(
        'customer/dashboard.html',
        vehicles=vehicles,
        active_requests=active_requests,
        recent_orders=recent_orders,
        recent_notifications=recent_notifications
    )

# --- VEHICLES MANAGEMENT ---
@customer_bp.route('/vehicles', methods=['GET', 'POST'])
@login_required
@customer_required
def vehicles():
    if request.method == 'POST':
        make = request.form.get('make')
        model = request.form.get('model')
        year = int(request.form.get('year', 2022))
        license_plate = request.form.get('license_plate')
        fuel_type = request.form.get('fuel_type')
        vehicle_type = request.form.get('vehicle_type', 'car')

        vehicle = Vehicle(
            user_id=current_user.id,
            make=make,
            model=model,
            year=year,
            license_plate=license_plate,
            fuel_type=fuel_type,
            vehicle_type=vehicle_type
        )
        db.session.add(vehicle)
        db.session.commit()
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('customer.vehicles'))

    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('customer/vehicles.html', vehicles=vehicles)

@customer_bp.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@login_required
@customer_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    db.session.delete(vehicle)
    db.session.commit()
    flash('Vehicle removed.', 'info')
    return redirect(url_for('customer.vehicles'))

# --- FUEL DELIVERY MODULE ---
@customer_bp.route('/request/fuel', methods=['GET', 'POST'])
@login_required
@customer_required
def request_fuel():
    if request.method == 'POST':
        # 1. Location Validation
        pickup_lat_raw = request.form.get('pickup_lat')
        pickup_lng_raw = request.form.get('pickup_lng')
        location_address = request.form.get('pickup_address', '').strip()
        locality = request.form.get('locality', '').strip()

        try:
            pickup_lat, pickup_lng = validate_coordinates(pickup_lat_raw, pickup_lng_raw)
        except ValueError as ve:
            flash(f"Invalid location coordinates: {ve}. Please select location on map.", "danger")
            vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
            return render_template('customer/fuel_request.html', vehicles=vehicles)

        if not location_address:
            location_address = f"GPS Pin ({pickup_lat:.4f}, {pickup_lng:.4f})"

        # 2. Prevent Duplicate Submissions within 10 seconds
        recent_req = ServiceRequest.query.filter(
            ServiceRequest.customer_id == current_user.id,
            ServiceRequest.service_type == 'fuel',
            ServiceRequest.created_at >= datetime.utcnow() - timedelta(seconds=10)
        ).first()
        if recent_req:
            flash('A recent fuel request was already submitted. Tracking live request.', 'info')
            return redirect(url_for('customer.tracking', request_id=recent_req.id))

        vehicle_id = request.form.get('vehicle_id') or None
        fuel_type = request.form.get('fuel_type', 'petrol')
        quantity = float(request.form.get('quantity', 5))
        is_emergency = True if request.form.get('is_emergency') else False
        service_notes = request.form.get('service_notes', '').strip()

        # Cost calculation
        fuel_prices = {'petrol': 102.50, 'diesel': 89.20, 'cng': 78.00}
        price_per_l = fuel_prices.get(fuel_type.lower(), 100.0)
        fuel_cost = round(quantity * price_per_l, 2)
        delivery_fee = 75.00 if is_emergency else 50.00
        total_estimated = round(fuel_cost + delivery_fee, 2)

        # 3. Provider Resolution: Registered partner vs External OSM station
        sel_provider_id = request.form.get('selected_provider_id')
        sel_provider_name = request.form.get('selected_provider_name', '').strip()
        prov_lat_raw = request.form.get('provider_lat')
        prov_lng_raw = request.form.get('provider_lng')
        prov_address = request.form.get('provider_address', '').strip()
        prov_source = request.form.get('provider_source', 'registered')

        assigned_provider_id = None
        saved_provider_name = None
        saved_prov_lat = None
        saved_prov_lng = None
        saved_prov_address = None
        saved_prov_source = 'registered'
        dist_km = None

        if sel_provider_id:
            try:
                p_id = int(sel_provider_id)
                reg_p = ProviderProfile.query.filter_by(id=p_id, status='approved').first()
                if reg_p:
                    assigned_provider_id = reg_p.id
                    saved_provider_name = reg_p.business_name
                    saved_prov_lat = reg_p.current_lat
                    saved_prov_lng = reg_p.current_lng
                    saved_prov_address = f"MotoServe Partner Station ({reg_p.business_name})"
                    saved_prov_source = 'registered'
                    dist_km = calculate_haversine_distance(pickup_lat, pickup_lng, reg_p.current_lat, reg_p.current_lng)
            except ValueError:
                pass

        if not assigned_provider_id and sel_provider_name:
            # External OSM station chosen by customer
            saved_provider_name = sel_provider_name
            saved_prov_address = prov_address or f"Mapped Station near ({pickup_lat:.4f}, {pickup_lng:.4f})"
            saved_prov_source = 'osm'
            try:
                if prov_lat_raw and prov_lng_raw:
                    saved_prov_lat, saved_prov_lng = validate_coordinates(prov_lat_raw, prov_lng_raw)
                    dist_km = calculate_haversine_distance(pickup_lat, pickup_lng, saved_prov_lat, saved_prov_lng)
            except ValueError:
                pass

        # If no provider selected, auto-search nearest registered partner, or auto-connect nearest mapped fuel station
        if not assigned_provider_id and not saved_provider_name:
            fallback_provider, fallback_dist, _ = find_nearest_provider(pickup_lat, pickup_lng, 'fuel', max_radius_km=30)
            if fallback_provider:
                assigned_provider_id = fallback_provider.id
                saved_provider_name = fallback_provider.business_name
                saved_prov_lat = fallback_provider.current_lat
                saved_prov_lng = fallback_provider.current_lng
                saved_prov_source = 'registered'
                dist_km = fallback_dist
            else:
                nearby_fuel = get_nearby_fuel(pickup_lat, pickup_lng, radius_km=15, auto_expand=True)
                if nearby_fuel and nearby_fuel.get('providers'):
                    nearest = nearby_fuel['providers'][0]
                    saved_provider_name = nearest.get('business_name') or nearest.get('name') or 'Nearby Fuel Station'
                    saved_prov_lat = nearest.get('lat')
                    saved_prov_lng = nearest.get('lng')
                    saved_prov_address = nearest.get('address') or f"Mapped Station near ({pickup_lat:.4f}, {pickup_lng:.4f})"
                    saved_prov_source = nearest.get('source', 'osm')
                    dist_km = nearest.get('distance_km')

        service_req = ServiceRequest(
            customer_id=current_user.id,
            provider_id=assigned_provider_id,
            vehicle_id=vehicle_id,
            service_type='fuel',
            status='pending', # Acceptance recorded only when accepted by provider
            pickup_address=location_address,
            locality=locality,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            provider_name=saved_provider_name,
            provider_lat=saved_prov_lat,
            provider_lng=saved_prov_lng,
            provider_address=saved_prov_address,
            provider_source=saved_prov_source,
            distance_km=dist_km,
            service_notes=service_notes,
            is_emergency=is_emergency,
            estimated_fee=total_estimated,
            final_amount=total_estimated
        )
        db.session.add(service_req)
        db.session.flush()

        fuel_detail = FuelDetails(
            request_id=service_req.id,
            fuel_type=fuel_type,
            quantity_litres=quantity,
            fuel_price_per_litre=price_per_l,
            delivery_fee=delivery_fee
        )
        db.session.add(fuel_detail)
        db.session.commit()

        # Notifications
        if assigned_provider_id:
            reg_p = ProviderProfile.query.get(assigned_provider_id)
            if reg_p:
                create_notification(reg_p.user_id, "New Fuel Request", f"New fuel delivery request #{service_req.request_number} nearby.", link=url_for('provider.active_job', request_id=service_req.id))
        create_notification(current_user.id, "Fuel Request Created", f"Request #{service_req.request_number} placed at {location_address}. Waiting for provider dispatch.", link=url_for('customer.tracking', request_id=service_req.id))

        flash(f'Fuel Delivery request #{service_req.request_number} created successfully! Live tracking initiated.', 'success')
        return redirect(url_for('customer.tracking', request_id=service_req.id))

    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('customer/fuel_request.html', vehicles=vehicles)


# --- REPAIR MODULE ---
@customer_bp.route('/request/repair', methods=['GET', 'POST'])
@login_required
@customer_required
def request_repair():
    if request.method == 'POST':
        pickup_lat_raw = request.form.get('pickup_lat')
        pickup_lng_raw = request.form.get('pickup_lng')
        location_address = request.form.get('pickup_address', '').strip()
        locality = request.form.get('locality', '').strip()

        try:
            pickup_lat, pickup_lng = validate_coordinates(pickup_lat_raw, pickup_lng_raw)
        except ValueError as ve:
            flash(f"Invalid location coordinates: {ve}. Please select location on map.", "danger")
            vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
            return render_template('customer/repair_request.html', vehicles=vehicles)

        if not location_address:
            location_address = f"GPS Pin ({pickup_lat:.4f}, {pickup_lng:.4f})"

        # Prevent duplicate submissions within 10 seconds
        recent_req = ServiceRequest.query.filter(
            ServiceRequest.customer_id == current_user.id,
            ServiceRequest.service_type == 'repair',
            ServiceRequest.created_at >= datetime.utcnow() - timedelta(seconds=10)
        ).first()
        if recent_req:
            flash('A recent repair request was already submitted. Tracking live request.', 'info')
            return redirect(url_for('customer.tracking', request_id=recent_req.id))

        vehicle_id = request.form.get('vehicle_id') or None
        category = request.form.get('problem_category', 'General Inspection')
        description = request.form.get('problem_description', '').strip()
        is_emergency = True if request.form.get('is_emergency') else False
        service_notes = request.form.get('service_notes', '').strip()

        # Image Upload
        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                photo_filename = f"repair_{current_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], photo_filename))

        # Provider resolution
        sel_provider_id = request.form.get('selected_provider_id')
        sel_provider_name = request.form.get('selected_provider_name', '').strip()
        prov_lat_raw = request.form.get('provider_lat')
        prov_lng_raw = request.form.get('provider_lng')
        prov_address = request.form.get('provider_address', '').strip()

        assigned_provider_id = None
        saved_provider_name = None
        saved_prov_lat = None
        saved_prov_lng = None
        saved_prov_address = None
        saved_prov_source = 'registered'
        dist_km = None

        if sel_provider_id:
            try:
                p_id = int(sel_provider_id)
                reg_p = ProviderProfile.query.filter_by(id=p_id, status='approved').first()
                if reg_p:
                    assigned_provider_id = reg_p.id
                    saved_provider_name = reg_p.business_name
                    saved_prov_lat = reg_p.current_lat
                    saved_prov_lng = reg_p.current_lng
                    saved_prov_address = f"MotoServe Partner Garage ({reg_p.business_name})"
                    saved_prov_source = 'registered'
                    dist_km = calculate_haversine_distance(pickup_lat, pickup_lng, reg_p.current_lat, reg_p.current_lng)
            except ValueError:
                pass

        if not assigned_provider_id and sel_provider_name:
            saved_provider_name = sel_provider_name
            saved_prov_address = prov_address or f"Workshop near ({pickup_lat:.4f}, {pickup_lng:.4f})"
            saved_prov_source = 'osm'
            try:
                if prov_lat_raw and prov_lng_raw:
                    saved_prov_lat, saved_prov_lng = validate_coordinates(prov_lat_raw, prov_lng_raw)
                    dist_km = calculate_haversine_distance(pickup_lat, pickup_lng, saved_prov_lat, saved_prov_lng)
            except ValueError:
                pass

        if not assigned_provider_id and not saved_provider_name:
            fallback_provider, fallback_dist, _ = find_nearest_provider(pickup_lat, pickup_lng, 'mechanic', max_radius_km=30)
            if fallback_provider:
                assigned_provider_id = fallback_provider.id
                saved_provider_name = fallback_provider.business_name
                saved_prov_lat = fallback_provider.current_lat
                saved_prov_lng = fallback_provider.current_lng
                saved_prov_source = 'registered'
                dist_km = fallback_dist
            else:
                nearby_rep = get_nearby_repair(pickup_lat, pickup_lng, radius_km=15, auto_expand=True)
                if nearby_rep and nearby_rep.get('providers'):
                    nearest = nearby_rep['providers'][0]
                    saved_provider_name = nearest.get('business_name') or nearest.get('name') or 'Nearby Vehicle Repair'
                    saved_prov_lat = nearest.get('lat')
                    saved_prov_lng = nearest.get('lng')
                    saved_prov_address = nearest.get('address') or f"Workshop near ({pickup_lat:.4f}, {pickup_lng:.4f})"
                    saved_prov_source = nearest.get('source', 'osm')
                    dist_km = nearest.get('distance_km')

        service_req = ServiceRequest(
            customer_id=current_user.id,
            provider_id=assigned_provider_id,
            vehicle_id=vehicle_id,
            service_type='repair',
            status='pending',
            pickup_address=location_address,
            locality=locality,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            provider_name=saved_provider_name,
            provider_lat=saved_prov_lat,
            provider_lng=saved_prov_lng,
            provider_address=saved_prov_address,
            provider_source=saved_prov_source,
            distance_km=dist_km,
            service_notes=service_notes,
            is_emergency=is_emergency,
            estimated_fee=250.00,
            final_amount=250.00
        )
        db.session.add(service_req)
        db.session.flush()

        repair_detail = RepairDetails(
            request_id=service_req.id,
            problem_category=category,
            problem_description=description,
            photo_url=photo_filename
        )
        db.session.add(repair_detail)
        db.session.commit()

        if assigned_provider_id:
            reg_p = ProviderProfile.query.get(assigned_provider_id)
            if reg_p:
                create_notification(reg_p.user_id, "New Mechanic Request", f"Assigned to repair request #{service_req.request_number}.", link=url_for('provider.active_job', request_id=service_req.id))
        create_notification(current_user.id, "Repair Request Created", f"Request #{service_req.request_number} logged. Mechanic will be dispatched soon.", link=url_for('customer.tracking', request_id=service_req.id))

        flash(f'Repair request #{service_req.request_number} booked successfully! Mechanic notified.', 'success')
        return redirect(url_for('customer.tracking', request_id=service_req.id))

    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('customer/repair_request.html', vehicles=vehicles)


# --- TOWING MODULE ---
@customer_bp.route('/request/tow', methods=['GET', 'POST'])
@login_required
@customer_required
def request_tow():
    if request.method == 'POST':
        pickup_lat_raw = request.form.get('pickup_lat')
        pickup_lng_raw = request.form.get('pickup_lng')
        pickup_address = request.form.get('pickup_address', '').strip()
        drop_address = request.form.get('drop_address', '').strip()
        drop_lat_raw = request.form.get('drop_lat')
        drop_lng_raw = request.form.get('drop_lng')
        locality = request.form.get('locality', '').strip()

        try:
            pickup_lat, pickup_lng = validate_coordinates(pickup_lat_raw, pickup_lng_raw)
        except ValueError as ve:
            flash(f"Invalid pickup location: {ve}. Please select location on map.", "danger")
            vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
            return render_template('customer/tow_request.html', vehicles=vehicles)

        drop_lat = None
        drop_lng = None
        if drop_lat_raw and drop_lng_raw:
            try:
                drop_lat, drop_lng = validate_coordinates(drop_lat_raw, drop_lng_raw)
            except ValueError:
                pass

        if not pickup_address:
            pickup_address = f"Breakdown Spot ({pickup_lat:.4f}, {pickup_lng:.4f})"
        if not drop_address:
            drop_address = "Nearest Authorized Service Garage"

        # Prevent duplicate submissions within 10 seconds
        recent_req = ServiceRequest.query.filter(
            ServiceRequest.customer_id == current_user.id,
            ServiceRequest.service_type == 'tow',
            ServiceRequest.created_at >= datetime.utcnow() - timedelta(seconds=10)
        ).first()
        if recent_req:
            flash('A recent towing request was already submitted. Tracking live request.', 'info')
            return redirect(url_for('customer.tracking', request_id=recent_req.id))

        vehicle_id = request.form.get('vehicle_id') or None
        reason = request.form.get('towing_reason', 'Breakdown')
        service_notes = request.form.get('service_notes', '').strip()

        # Towing distance between breakdown spot and drop-off
        if drop_lat and drop_lng:
            tow_dist_km = calculate_haversine_distance(pickup_lat, pickup_lng, drop_lat, drop_lng) or 5.0
        else:
            tow_dist_km = 5.0

        base_charge = 300.00
        rate_per_km = 35.00
        total_fee = round(base_charge + (tow_dist_km * rate_per_km), 2)

        # Provider resolution
        sel_provider_id = request.form.get('selected_provider_id')
        sel_provider_name = request.form.get('selected_provider_name', '').strip()
        prov_lat_raw = request.form.get('provider_lat')
        prov_lng_raw = request.form.get('provider_lng')
        prov_address = request.form.get('provider_address', '').strip()

        assigned_provider_id = None
        saved_provider_name = None
        saved_prov_lat = None
        saved_prov_lng = None
        saved_prov_address = None
        saved_prov_source = 'registered'
        prov_dist_km = None

        if sel_provider_id:
            try:
                p_id = int(sel_provider_id)
                reg_p = ProviderProfile.query.filter_by(id=p_id, status='approved').first()
                if reg_p:
                    assigned_provider_id = reg_p.id
                    saved_provider_name = reg_p.business_name
                    saved_prov_lat = reg_p.current_lat
                    saved_prov_lng = reg_p.current_lng
                    saved_prov_address = f"MotoServe Partner Towing ({reg_p.business_name})"
                    saved_prov_source = 'registered'
                    prov_dist_km = calculate_haversine_distance(pickup_lat, pickup_lng, reg_p.current_lat, reg_p.current_lng)
            except ValueError:
                pass

        if not assigned_provider_id and sel_provider_name:
            saved_provider_name = sel_provider_name
            saved_prov_address = prov_address or f"Towing Service near ({pickup_lat:.4f}, {pickup_lng:.4f})"
            saved_prov_source = 'osm'
            try:
                if prov_lat_raw and prov_lng_raw:
                    saved_prov_lat, saved_prov_lng = validate_coordinates(prov_lat_raw, prov_lng_raw)
                    prov_dist_km = calculate_haversine_distance(pickup_lat, pickup_lng, saved_prov_lat, saved_prov_lng)
            except ValueError:
                pass

        if not assigned_provider_id and not saved_provider_name:
            fallback_provider, fallback_dist, _ = find_nearest_provider(pickup_lat, pickup_lng, 'tow', max_radius_km=30)
            if fallback_provider:
                assigned_provider_id = fallback_provider.id
                saved_provider_name = fallback_provider.business_name
                saved_prov_lat = fallback_provider.current_lat
                saved_prov_lng = fallback_provider.current_lng
                saved_prov_source = 'registered'
                prov_dist_km = fallback_dist
            else:
                nearby_tow = get_nearby_towing(pickup_lat, pickup_lng, radius_km=25, auto_expand=True)
                if nearby_tow and nearby_tow.get('providers'):
                    nearest = nearby_tow['providers'][0]
                    saved_provider_name = nearest.get('business_name') or nearest.get('name') or 'Nearby Towing & Recovery'
                    saved_prov_lat = nearest.get('lat')
                    saved_prov_lng = nearest.get('lng')
                    saved_prov_address = nearest.get('address') or f"Towing Service near ({pickup_lat:.4f}, {pickup_lng:.4f})"
                    saved_prov_source = nearest.get('source', 'osm')
                    prov_dist_km = nearest.get('distance_km')

        service_req = ServiceRequest(
            customer_id=current_user.id,
            provider_id=assigned_provider_id,
            vehicle_id=vehicle_id,
            service_type='tow',
            status='pending',
            pickup_address=pickup_address,
            locality=locality,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            drop_address=drop_address,
            drop_lat=drop_lat,
            drop_lng=drop_lng,
            provider_name=saved_provider_name,
            provider_lat=saved_prov_lat,
            provider_lng=saved_prov_lng,
            provider_address=saved_prov_address,
            provider_source=saved_prov_source,
            distance_km=prov_dist_km,
            service_notes=service_notes,
            estimated_fee=total_fee,
            final_amount=total_fee
        )
        db.session.add(service_req)
        db.session.flush()

        tow_detail = TowDetails(
            request_id=service_req.id,
            towing_reason=reason,
            distance_km=tow_dist_km,
            rate_per_km=rate_per_km,
            base_charge=base_charge
        )
        db.session.add(tow_detail)
        db.session.commit()

        if assigned_provider_id:
            reg_p = ProviderProfile.query.get(assigned_provider_id)
            if reg_p:
                create_notification(reg_p.user_id, "New Towing Request", f"Assigned to tow job #{service_req.request_number}.", link=url_for('provider.active_job', request_id=service_req.id))
        create_notification(current_user.id, "Towing Request Placed", f"Tow truck request #{service_req.request_number} registered. Tracking dispatch.", link=url_for('customer.tracking', request_id=service_req.id))

        flash(f'Towing request #{service_req.request_number} created successfully! Tow truck dispatched.', 'success')
        return redirect(url_for('customer.tracking', request_id=service_req.id))

    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('customer/tow_request.html', vehicles=vehicles)


# --- SOS EMERGENCY PANIC BUTTON ---
@customer_bp.route('/sos', methods=['POST'])
@login_required
@customer_required
def sos_panic():
    pickup_address = request.form.get('pickup_address', 'Emergency SOS Breakdown Location')
    pickup_lat_raw = request.form.get('pickup_lat', 12.9716)
    pickup_lng_raw = request.form.get('pickup_lng', 77.5946)
    sos_type = request.form.get('sos_type', 'repair') # 'fuel', 'repair', 'tow'

    try:
        pickup_lat, pickup_lng = validate_coordinates(pickup_lat_raw, pickup_lng_raw)
    except ValueError:
        pickup_lat, pickup_lng = 12.9716, 77.5946

    provider, dist, eta = find_nearest_provider(pickup_lat, pickup_lng, sos_type, max_radius_km=30)

    service_req = ServiceRequest(
        customer_id=current_user.id,
        provider_id=provider.id if provider else None,
        service_type=sos_type,
        status='pending',
        pickup_address=f"🚨 EMERGENCY SOS: {pickup_address}",
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        is_emergency=True,
        estimated_fee=300.00,
        final_amount=300.00
    )
    db.session.add(service_req)
    db.session.flush()

    if sos_type == 'fuel':
        db.session.add(FuelDetails(request_id=service_req.id, fuel_type='petrol', quantity_litres=5))
    elif sos_type == 'tow':
        db.session.add(TowDetails(request_id=service_req.id, towing_reason='Emergency Breakdown', distance_km=5.0))
    else:
        db.session.add(RepairDetails(request_id=service_req.id, problem_category='Emergency SOS Breakdown', problem_description='Customer triggered emergency SOS button.'))

    db.session.commit()

    if provider:
        create_notification(provider.user_id, "🚨 EMERGENCY SOS BROADCAST", f"Priority emergency SOS request #{service_req.request_number}!", link=url_for('provider.active_job', request_id=service_req.id))

    flash('🚨 EMERGENCY SOS BROADCASTED! Request placed and nearby providers notified.', 'danger')
    return redirect(url_for('customer.tracking', request_id=service_req.id))


# --- LIVE TRACKING & HISTORY ---
@customer_bp.route('/tracking/<int:request_id>')
@login_required
@customer_required
def tracking(request_id):
    req = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.id).first_or_404()

    # Automatically resolve and connect nearest fuel station or provider if not already assigned
    if not req.provider_id and not req.provider_name and req.pickup_lat and req.pickup_lng:
        try:
            if req.service_type == 'fuel':
                res = get_nearby_fuel(req.pickup_lat, req.pickup_lng, radius_km=15, auto_expand=True)
            elif req.service_type == 'repair':
                res = get_nearby_repair(req.pickup_lat, req.pickup_lng, radius_km=15, auto_expand=True)
            else:
                res = get_nearby_towing(req.pickup_lat, req.pickup_lng, radius_km=25, auto_expand=True)

            if res and res.get('providers'):
                nearest = res['providers'][0]
                if nearest.get('is_partner') and nearest.get('id') and not str(nearest.get('id')).startswith('osm'):
                    req.provider_id = int(nearest['id'])
                req.provider_name = nearest.get('business_name') or nearest.get('name')
                req.provider_lat = nearest.get('lat')
                req.provider_lng = nearest.get('lng')
                req.provider_address = nearest.get('address')
                req.provider_source = nearest.get('source', 'osm')
                req.distance_km = nearest.get('distance_km')
                db.session.commit()
        except Exception as e:
            print(f"[!] Tracking provider auto-connect warning: {e}")

    return render_template('customer/tracking.html', req=req)


@customer_bp.route('/tracking/status/<int:request_id>')
@login_required
def tracking_status_json(request_id):
    req = ServiceRequest.query.get_or_404(request_id)

    # Automatically resolve nearest provider if not yet assigned
    if not req.provider_id and not req.provider_name and req.pickup_lat and req.pickup_lng:
        try:
            if req.service_type == 'fuel':
                res = get_nearby_fuel(req.pickup_lat, req.pickup_lng, radius_km=15, auto_expand=True)
            elif req.service_type == 'repair':
                res = get_nearby_repair(req.pickup_lat, req.pickup_lng, radius_km=15, auto_expand=True)
            else:
                res = get_nearby_towing(req.pickup_lat, req.pickup_lng, radius_km=25, auto_expand=True)

            if res and res.get('providers'):
                nearest = res['providers'][0]
                if nearest.get('is_partner') and nearest.get('id') and not str(nearest.get('id')).startswith('osm'):
                    req.provider_id = int(nearest['id'])
                req.provider_name = nearest.get('business_name') or nearest.get('name')
                req.provider_lat = nearest.get('lat')
                req.provider_lng = nearest.get('lng')
                req.provider_address = nearest.get('address')
                req.provider_source = nearest.get('source', 'osm')
                req.distance_km = nearest.get('distance_km')
                db.session.commit()
        except Exception as e:
            print(f"[!] Tracking status JSON auto-connect warning: {e}")

    provider_info = None

    if req.provider_profile:
        provider_info = {
            'business_name': req.provider_profile.business_name,
            'name': req.provider_profile.user.name if req.provider_profile.user else req.provider_profile.business_name,
            'phone': req.provider_profile.user.phone if req.provider_profile.user else '',
            'lat': req.provider_profile.current_lat,
            'lng': req.provider_profile.current_lng,
            'rating': req.provider_profile.rating,
            'source': 'registered'
        }
    elif req.provider_name:
        provider_info = {
            'business_name': req.provider_name,
            'name': req.provider_name,
            'phone': req.provider_phone or 'Contact on dispatch',
            'lat': req.provider_lat if req.provider_lat is not None else req.pickup_lat,
            'lng': req.provider_lng if req.provider_lng is not None else req.pickup_lng,
            'rating': 4.8,
            'source': req.provider_source or 'osm'
        }

    return jsonify({
        'status': req.status,
        'payment_status': req.payment_status,
        'service_type': req.service_type,
        'pickup_lat': req.pickup_lat,
        'pickup_lng': req.pickup_lng,
        'pickup_address': req.pickup_address,
        'drop_lat': req.drop_lat,
        'drop_lng': req.drop_lng,
        'drop_address': req.drop_address,
        'provider': provider_info,
        'distance_km': req.distance_km
    })

@customer_bp.route('/history')
@login_required
@customer_required
def history():
    requests = ServiceRequest.query.filter_by(customer_id=current_user.id).order_by(ServiceRequest.created_at.desc()).all()
    return render_template('customer/history.html', requests=requests)


# --- E-COMMERCE VEHICLE PRODUCTS STORE ---
@customer_bp.route('/store')
@login_required
@customer_required
def store():
    category = request.args.get('category')
    search_query = request.args.get('q', '').strip()

    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    if search_query:
        query = query.filter(Product.name.ilike(f"%{search_query}%"))

    products = query.all()
    categories = ['Engine Oil', 'Battery', 'Tyres', 'Helmet', 'Accessories', 'Brake Pads', 'Lubricants', 'Cleaning Kit']

    return render_template('customer/store.html', products=products, categories=categories, selected_category=category, search_query=search_query)

@customer_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
@customer_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty = int(request.form.get('quantity', 1))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += qty
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=qty)
        db.session.add(cart_item)

    db.session.commit()
    flash(f'{product.name} added to your cart!', 'success')
    return redirect(url_for('customer.store'))

@customer_bp.route('/cart')
@login_required
@customer_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_amount = sum(item.item_total for item in cart_items)
    return render_template('customer/cart.html', cart_items=cart_items, total_amount=total_amount)

@customer_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
@customer_required
def update_cart(item_id):
    cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    action = request.form.get('action')
    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            db.session.delete(cart_item)
    elif action == 'remove':
        db.session.delete(cart_item)
    db.session.commit()
    return redirect(url_for('customer.view_cart'))

@customer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@customer_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('customer.store'))

    total_amount = sum(item.item_total for item in cart_items)

    if request.method == 'POST':
        shipping_address = request.form.get('shipping_address')
        payment_method = request.form.get('payment_method')

        order = Order(
            customer_id=current_user.id,
            total_amount=total_amount,
            payment_method=payment_method,
            shipping_address=shipping_address,
            status='processing',
            payment_status='paid' if payment_method != 'cash' else 'pending'
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.product.final_price
            )
            # Reduce product stock
            item.product.stock -= item.quantity
            db.session.add(order_item)
            db.session.delete(item)

        payment = Payment(
            user_id=current_user.id,
            order_id=order.id,
            amount=total_amount,
            payment_method=payment_method,
            status='completed' if payment_method != 'cash' else 'pending'
        )
        db.session.add(payment)
        db.session.commit()

        create_notification(current_user.id, "Order Confirmed!", f"Your order #{order.order_number} has been placed.", link=url_for('customer.orders'))
        flash('Order placed successfully!', 'success')
        return redirect(url_for('customer.orders'))

    return render_template('customer/checkout.html', cart_items=cart_items, total_amount=total_amount)

@customer_bp.route('/orders')
@login_required
@customer_required
def orders():
    user_orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=user_orders)


# --- PAYMENTS & INVOICES ---
@customer_bp.route('/payment/process/<int:request_id>', methods=['POST'])
@login_required
@customer_required
def process_service_payment(request_id):
    req = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.id).first_or_404()
    payment_method = request.form.get('payment_method', 'upi')

    payment = Payment(
        user_id=current_user.id,
        request_id=req.id,
        amount=req.final_amount,
        payment_method=payment_method,
        status='completed'
    )
    req.payment_status = 'paid'
    db.session.add(payment)
    db.session.commit()

    if req.provider_profile:
        create_notification(req.provider_profile.user_id, "Payment Received", f"Payment of ₹{req.final_amount} received for request #{req.request_number}.")

    flash('Payment completed successfully!', 'success')
    return redirect(url_for('customer.tracking', request_id=req.id))

@customer_bp.route('/invoice/<type_name>/<int:item_id>')
@login_required
def download_invoice(type_name, item_id):
    if type_name == 'service':
        item = ServiceRequest.query.get_or_404(item_id)
    else:
        item = Order.query.get_or_404(item_id)
    return generate_invoice_html(item, type_name)


# --- CHAT & REVIEWS ---
@customer_bp.route('/chat/<int:request_id>', methods=['GET', 'POST'])
@login_required
def chat(request_id):
    req = ServiceRequest.query.get_or_404(request_id)

    # Verify authorization (Customer, Provider assigned, or Admin)
    is_customer = (current_user.id == req.customer_id)
    is_provider = (req.provider_profile and req.provider_profile.user_id == current_user.id)
    is_admin = current_user.is_admin()

    if not (is_customer or is_provider or is_admin):
        flash('Access denied. You are not a party to this service request chat.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        msg_text = request.form.get('message')
        if msg_text:
            chat_msg = ChatMessage(
                request_id=req.id,
                sender_id=current_user.id,
                message=msg_text
            )
            db.session.add(chat_msg)
            db.session.commit()

            # Create notification for recipient
            chat_url = url_for('customer.chat', request_id=req.id)
            if is_customer and req.provider_profile:
                create_notification(
                    user_id=req.provider_profile.user_id,
                    title="New Chat Message 💬",
                    message=f"{current_user.name}: {msg_text[:50]}",
                    link=chat_url
                )
            elif is_provider:
                provider_name = req.provider_profile.business_name if req.provider_profile else current_user.name
                create_notification(
                    user_id=req.customer_id,
                    title="New Message from Provider 💬",
                    message=f"{provider_name}: {msg_text[:50]}",
                    link=chat_url
                )

            return jsonify({'status': 'success'})

    messages = ChatMessage.query.filter_by(request_id=req.id).order_by(ChatMessage.created_at.asc()).all()
    if request.args.get('json'):
        return jsonify([{
            'sender_id': m.sender_id,
            'sender_name': m.sender.name,
            'message': m.message,
            'time': m.created_at.strftime('%H:%M')
        } for m in messages])

    base_template = 'provider/base_provider.html' if current_user.is_provider() else 'customer/base_customer.html'
    return render_template('customer/chat.html', req=req, messages=messages, base_template=base_template)

@customer_bp.route('/review/submit/<int:request_id>', methods=['POST'])
@login_required
@customer_required
def submit_review(request_id):
    req = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.id).first_or_404()
    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment')

    if req.provider_profile:
        review = Review(
            request_id=req.id,
            customer_id=current_user.id,
            provider_id=req.provider_profile.id,
            rating=rating,
            comment=comment
        )
        req.provider_profile.update_rating(rating)
        db.session.add(review)
        db.session.commit()
        flash('Thank you for rating your service provider!', 'success')

    return redirect(url_for('customer.history'))

@customer_bp.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    # Mark as read
    for n in user_notifications:
        n.is_read = True
    db.session.commit()
    return render_template('customer/notifications.html', notifications=user_notifications)

@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@customer_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')
        current_user.license_number = request.form.get('license_number')

        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                avatar_filename = f"avatar_user_{current_user.id}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], avatar_filename))
                current_user.avatar = avatar_filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('customer.profile'))
    return render_template('customer/profile.html')
