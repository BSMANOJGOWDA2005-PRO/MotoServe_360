import math
from models import ProviderProfile

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    R = 6371.0 # Radius of the Earth in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return round(distance, 2)


def calculate_eta(distance_km, avg_speed_kmh=35):
    """
    Calculates estimated arrival time in minutes based on distance.
    """
    if distance_km <= 0:
        return 5
    time_hours = distance_km / avg_speed_kmh
    time_minutes = int(time_hours * 60)
    # Add 5 minutes buffer for dispatch
    return max(time_minutes + 5, 5)


def find_nearest_provider(lat, lng, provider_type):
    """
    Finds the nearest online and approved provider of a given type.
    """
    providers = ProviderProfile.query.filter_by(
        provider_type=provider_type,
        status='approved',
        is_online=True
    ).all()
    
    if not providers:
        # Fallback: if no online provider is found, get any approved provider of that type for simulation
        providers = ProviderProfile.query.filter_by(
            provider_type=provider_type,
            status='approved'
        ).all()

    if not providers:
        return None, None, None

    nearest_provider = None
    min_distance = float('inf')

    for p in providers:
        dist = calculate_haversine_distance(lat, lng, p.current_lat, p.current_lng)
        if dist < min_distance:
            min_distance = dist
            nearest_provider = p

    eta = calculate_eta(min_distance) if nearest_provider else 15
    return nearest_provider, min_distance, eta
