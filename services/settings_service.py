import os
import json
from config import BASE_DIR

SETTINGS_FILE = os.path.join(BASE_DIR, 'instance', 'system_settings.json')

DEFAULT_SETTINGS = {
    'platform_name': 'MotoServe 360',
    'petrol_price': 102.50,
    'diesel_price': 89.20,
    'cng_price': 78.00,
    'delivery_fee': 50.00,
    'emergency_surge': 25.00,
    'platform_fee': 9.00,
    'towing_rate_per_km': 35.00,
    'towing_base_fee': 300.00,
    'mechanic_inspection_fee': 250.00
}

def get_system_settings():
    if not os.path.exists(SETTINGS_FILE):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)
        except Exception as e:
            print(f"[!] Warning writing default settings: {e}")
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception as e:
        print(f"[!] Warning reading settings: {e}")
        return DEFAULT_SETTINGS.copy()

def save_system_settings(form_dict):
    settings = get_system_settings()
    if 'platform_name' in form_dict:
        name_val = str(form_dict.get('platform_name', '')).strip()
        if name_val:
            settings['platform_name'] = name_val
    
    numeric_keys = [
        'petrol_price', 'diesel_price', 'cng_price',
        'delivery_fee', 'emergency_surge', 'platform_fee',
        'towing_rate_per_km', 'towing_base_fee', 'mechanic_inspection_fee'
    ]
    for key in numeric_keys:
        if key in form_dict and form_dict[key] != '':
            try:
                settings[key] = round(float(form_dict[key]), 2)
            except (ValueError, TypeError):
                pass

    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving settings: {e}")
        raise e
    return settings
