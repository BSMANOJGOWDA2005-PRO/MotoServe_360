import unittest
import json
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, ServiceRequest, FuelDetails, RepairDetails, TowDetails, ProviderProfile
from services import (
    validate_coordinates,
    calculate_haversine_distance,
    format_distance,
    get_nearby_fuel,
    get_nearby_repair,
    get_nearby_towing
)

class LocationBookingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def login_customer(self):
        with self.app.app_context():
            user = User.query.filter_by(role='customer').first()
            user_id = str(user.id) if user else '2'

        with self.client.session_transaction() as sess:
            sess['_user_id'] = user_id
            sess['_fresh'] = True
        return user_id

    def test_01_coordinate_validation(self):
        """Test backend latitude and longitude validation"""
        # Valid coordinates
        lat, lng = validate_coordinates(12.2958, 76.6394)
        self.assertEqual((lat, lng), (12.2958, 76.6394))

        # Invalid out-of-bounds
        with self.assertRaises(ValueError):
            validate_coordinates(95.0, 77.0)
        with self.assertRaises(ValueError):
            validate_coordinates(12.0, 195.0)
        with self.assertRaises(ValueError):
            validate_coordinates("invalid", "coords")

    def test_02_distance_calculation(self):
        """Test accurate straight-line Haversine distance calculation"""
        # Mysuru center to Chamundi Hill
        dist = calculate_haversine_distance(12.2958, 76.6394, 12.3020, 76.6450)
        self.assertIsNotNone(dist)
        self.assertLess(dist, 2.0) # Less than 2 km
        self.assertIn("m", format_distance(0.85))
        self.assertIn("km", format_distance(4.2))

        # Mysuru to Bengaluru straight line is ~125-145 km
        dist_blr_mys = calculate_haversine_distance(12.2958, 76.6394, 12.9716, 77.5946)
        self.assertTrue(120 < dist_blr_mys < 155, f"Distance was {dist_blr_mys}")

    def test_03_mysuru_vs_bengaluru_fuel_filtering(self):
        """Test that customer in Mysuru receives Mysuru results and NOT Bengaluru results"""
        # 1. Query Mysuru (12.2958, 76.6394)
        resp_mys = self.client.get('/api/nearby/fuel?lat=12.2958&lng=76.6394&radius=10')
        self.assertEqual(resp_mys.status_code, 200)
        data_mys = resp_mys.get_json()
        self.assertEqual(data_mys['status'], 'success')
        self.assertGreater(data_mys['total_count'], 0)

        # Confirm all returned providers in Mysuru search are within 10 km (NOT in Bengaluru ~135km away!)
        for p in data_mys['providers']:
            self.assertLessEqual(p['distance_km'], 10.0, f"Provider {p['business_name']} is {p['distance_km']} km away!")
            # Must not be Bengaluru providers
            self.assertNotIn("Express Fuel Tankers", p['business_name'])
            self.assertNotIn("suresh's", p['business_name'].lower())

        # Confirm Mysuru registered partner or local stations are found
        names = [p['business_name'] for p in data_mys['providers']]
        self.assertTrue(any("Chamundi" in n or "Indian Oil" in n or "Fuel" in n or "Petroleum" in n for n in names))

        # 2. Query Bengaluru (12.9716, 77.5946)
        resp_blr = self.client.get('/api/nearby/fuel?lat=12.9716&lng=77.5946&radius=10')
        self.assertEqual(resp_blr.status_code, 200)
        data_blr = resp_blr.get_json()
        for p in data_blr['providers']:
            self.assertLessEqual(p['distance_km'], 10.0)
            self.assertNotIn("Chamundi", p['business_name']) # Chamundi is in Mysuru, should NOT appear in Bengaluru!

    def test_04_repair_and_towing_location_filtering(self):
        """Test that repair and towing services filter by actual customer coordinates"""
        # Mysuru repair
        resp_rep = self.client.get('/api/nearby/repair?lat=12.2958&lng=76.6394&radius=15')
        self.assertEqual(resp_rep.status_code, 200)
        data_rep = resp_rep.get_json()
        self.assertGreater(data_rep['total_count'], 0)
        for p in data_rep['providers']:
            self.assertLessEqual(p['distance_km'], 15.0)

        # Mysuru towing
        resp_tow = self.client.get('/api/nearby/towing?lat=12.2958&lng=76.6394&radius=25')
        self.assertEqual(resp_tow.status_code, 200)
        data_tow = resp_tow.get_json()
        self.assertGreater(data_tow['total_count'], 0)
        for p in data_tow['providers']:
            self.assertLessEqual(p['distance_km'], 25.0)

    def test_05_api_location_endpoints(self):
        """Test API validation, reverse geocode, and distance calculation endpoints"""
        # Validate endpoint
        val_res = self.client.get('/api/location/validate?lat=12.2958&lng=76.6394')
        self.assertEqual(val_res.status_code, 200)
        self.assertTrue(val_res.get_json()['valid'])

        # Invalid coords validation
        bad_res = self.client.get('/api/location/validate?lat=999&lng=76.6394')
        self.assertEqual(bad_res.status_code, 400)

        # Distance endpoint
        dist_res = self.client.get('/api/distance?lat1=12.2958&lon1=76.6394&lat2=12.3020&lon2=76.6450')
        self.assertEqual(dist_res.status_code, 200)
        self.assertIn('distance_km', dist_res.get_json())

        # Reverse geocoding endpoint
        rev_res = self.client.get('/api/location/reverse?lat=12.2958&lng=76.6394')
        self.assertEqual(rev_res.status_code, 200)
        self.assertIn('city', rev_res.get_json()['data'])

    def test_06_booking_fuel_in_mysuru(self):
        """Test submitting fuel booking with actual Mysuru coordinates and saving to DB"""
        self.login_customer()

        post_data = {
            'fuel_type': 'petrol',
            'quantity': '10',
            'pickup_address': 'Sayyaji Rao Road, Mysuru, Karnataka',
            'locality': 'Agrahara, Mysuru',
            'pickup_lat': '12.2958',
            'pickup_lng': '76.6394',
            'selected_provider_name': 'Indian Oil Station Mysuru',
            'provider_lat': '12.2993',
            'provider_lng': '76.6429',
            'provider_address': 'Sayyaji Rao Rd, Mysuru',
            'provider_source': 'osm',
            'service_notes': 'Parked outside Palace North Gate'
        }

        resp = self.client.post('/customer/request/fuel', data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            latest = ServiceRequest.query.filter_by(service_type='fuel').order_by(ServiceRequest.id.desc()).first()
            self.assertIsNotNone(latest)
            self.assertAlmostEqual(latest.pickup_lat, 12.2958, places=3)
            self.assertAlmostEqual(latest.pickup_lng, 76.6394, places=3)
            self.assertEqual(latest.locality, 'Agrahara, Mysuru')
            self.assertEqual(latest.provider_name, 'Indian Oil Station Mysuru')
            self.assertEqual(latest.provider_source, 'osm')
            self.assertEqual(latest.status, 'pending')
            self.assertIsNotNone(latest.distance_km)
            self.assertEqual(latest.service_notes, 'Parked outside Palace North Gate')

    def test_07_booking_repair_with_provider_assignment(self):
        """Test repair booking saving location and provider info correctly"""
        self.login_customer()

        with self.app.app_context():
            # Find the registered Mysuru mechanic
            mys_mech = ProviderProfile.query.filter_by(provider_type='mechanic', current_lat=12.2980).first()
            mech_id = mys_mech.id if mys_mech else None

        post_data = {
            'problem_category': 'Brake Issue',
            'problem_description': 'Brake pedal feels spongy and brake fluid leaking',
            'pickup_address': 'Kuvempunagar, Mysuru',
            'locality': 'Kuvempunagar',
            'pickup_lat': '12.2890',
            'pickup_lng': '76.6270',
            'selected_provider_id': str(mech_id) if mech_id else '',
            'service_notes': 'Please bring dot4 brake fluid'
        }

        resp = self.client.post('/customer/request/repair', data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            latest = ServiceRequest.query.filter_by(service_type='repair').order_by(ServiceRequest.id.desc()).first()
            self.assertIsNotNone(latest)
            self.assertAlmostEqual(latest.pickup_lat, 12.2890, places=3)
            self.assertEqual(latest.locality, 'Kuvempunagar')
            self.assertEqual(latest.status, 'pending')
            self.assertEqual(latest.service_notes, 'Please bring dot4 brake fluid')

    def test_08_duplicate_submission_prevention(self):
        """Test that rapid duplicate submissions within 10 seconds are prevented"""
        self.login_customer()
        post_data = {
            'fuel_type': 'diesel',
            'quantity': '5',
            'pickup_address': 'Gokulam 3rd Stage, Mysuru',
            'pickup_lat': '12.3250',
            'pickup_lng': '76.6210'
        }

        # 1st submission
        r1 = self.client.post('/customer/request/fuel', data=post_data, follow_redirects=True)
        self.assertEqual(r1.status_code, 200)

        # 2nd immediate submission (duplicate)
        r2 = self.client.post('/customer/request/fuel', data=post_data, follow_redirects=True)
        self.assertEqual(r2.status_code, 200)
        self.assertIn(b"recent fuel request was already submitted", r2.data)

if __name__ == '__main__':
    unittest.main()
