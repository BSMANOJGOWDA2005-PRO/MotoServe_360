from flask import Blueprint, request, jsonify
from flask_login import current_user
from services import (
    validate_coordinates,
    calculate_haversine_distance,
    format_distance,
    reverse_geocode,
    search_location,
    get_nearby_fuel,
    get_nearby_repair,
    get_nearby_towing
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/location/validate', methods=['GET'])
def api_validate_location():
    """
    Validates provided latitude and longitude.
    Query params: lat, lng
    """
    lat = request.args.get('lat')
    lng = request.args.get('lng')

    if lat is None or lng is None:
        return jsonify({
            'status': 'error',
            'message': 'Both lat and lng parameters are required.'
        }), 400

    try:
        lat_f, lng_f = validate_coordinates(lat, lng)
        return jsonify({
            'status': 'success',
            'valid': True,
            'lat': lat_f,
            'lng': lng_f
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'valid': False,
            'message': str(e)
        }), 400


@api_bp.route('/location/reverse', methods=['GET'])
def api_reverse_geocode():
    """
    Reverse geocodes coordinates to obtain address, city, locality, postal code.
    Query params: lat, lng
    """
    lat = request.args.get('lat')
    lng = request.args.get('lng')

    if lat is None or lng is None:
        return jsonify({
            'status': 'error',
            'message': 'Both lat and lng parameters are required.'
        }), 400

    try:
        data = reverse_geocode(lat, lng)
        return jsonify({
            'status': 'success',
            'data': data
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Geocoding service unavailable: {str(e)}"
        }), 502


@api_bp.route('/location/search', methods=['GET'])
def api_search_location():
    """
    Searches places, landmarks, or addresses.
    Query param: q
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({
            'status': 'error',
            'message': 'Search query parameter "q" is required.'
        }), 400

    try:
        results = search_location(query)
        return jsonify({
            'status': 'success',
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Search service error: {str(e)}"
        }), 502


@api_bp.route('/distance', methods=['GET'])
def api_calculate_distance():
    """
    Calculates straight-line Haversine distance between two coordinates.
    Query params: lat1, lon1, lat2, lon2
    """
    lat1 = request.args.get('lat1')
    lon1 = request.args.get('lon1')
    lat2 = request.args.get('lat2')
    lon2 = request.args.get('lon2')

    if any(param is None for param in [lat1, lon1, lat2, lon2]):
        return jsonify({
            'status': 'error',
            'message': 'All parameters (lat1, lon1, lat2, lon2) are required.'
        }), 400

    try:
        lat1_f, lon1_f = validate_coordinates(lat1, lon1)
        lat2_f, lon2_f = validate_coordinates(lat2, lon2)
        dist_km = calculate_haversine_distance(lat1_f, lon1_f, lat2_f, lon2_f)
        return jsonify({
            'status': 'success',
            'distance_km': dist_km,
            'distance_meters': int(round(dist_km * 1000)),
            'formatted_distance': format_distance(dist_km),
            'distance_type': 'straight_line_haversine'
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@api_bp.route('/nearby/fuel', methods=['GET'])
def api_nearby_fuel():
    """
    Finds nearby fuel stations (registered + OSM) around coordinates.
    Query params: lat, lng, radius (in km, default 10)
    """
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radius = request.args.get('radius', 10)

    if lat is None or lng is None:
        return jsonify({
            'status': 'error',
            'message': 'Coordinates lat and lng are required.'
        }), 400

    try:
        lat_f, lng_f = validate_coordinates(lat, lng)
        radius_f = float(radius)
        if radius_f <= 0 or radius_f > 100:
            radius_f = 10.0

        data = get_nearby_fuel(lat_f, lng_f, radius_km=radius_f, auto_expand=True)
        return jsonify({
            'status': 'success',
            'service_type': 'fuel',
            'customer_lat': lat_f,
            'customer_lng': lng_f,
            **data
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Failed to retrieve nearby fuel stations: {str(e)}"
        }), 500


@api_bp.route('/nearby/repair', methods=['GET'])
def api_nearby_repair():
    """
    Finds nearby mechanics, garages, and repair shops (registered prioritized + OSM).
    Query params: lat, lng, radius (in km, default 15)
    """
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radius = request.args.get('radius', 15)

    if lat is None or lng is None:
        return jsonify({
            'status': 'error',
            'message': 'Coordinates lat and lng are required.'
        }), 400

    try:
        lat_f, lng_f = validate_coordinates(lat, lng)
        radius_f = float(radius)
        if radius_f <= 0 or radius_f > 100:
            radius_f = 15.0

        data = get_nearby_repair(lat_f, lng_f, radius_km=radius_f, auto_expand=True)
        return jsonify({
            'status': 'success',
            'service_type': 'repair',
            'customer_lat': lat_f,
            'customer_lng': lng_f,
            **data
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Failed to retrieve nearby repair providers: {str(e)}"
        }), 500


@api_bp.route('/nearby/towing', methods=['GET'])
def api_nearby_towing():
    """
    Finds nearby towing and roadside recovery providers (registered + OSM).
    Query params: lat, lng, radius (in km, default 25)
    """
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radius = request.args.get('radius', 25)

    if lat is None or lng is None:
        return jsonify({
            'status': 'error',
            'message': 'Coordinates lat and lng are required.'
        }), 400

    try:
        lat_f, lng_f = validate_coordinates(lat, lng)
        radius_f = float(radius)
        if radius_f <= 0 or radius_f > 100:
            radius_f = 25.0

        data = get_nearby_towing(lat_f, lng_f, radius_km=radius_f, auto_expand=True)
        return jsonify({
            'status': 'success',
            'service_type': 'towing',
            'customer_lat': lat_f,
            'customer_lng': lng_f,
            **data
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Failed to retrieve nearby towing providers: {str(e)}"
        }), 500
