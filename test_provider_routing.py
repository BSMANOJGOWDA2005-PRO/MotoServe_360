import unittest
from app import create_app
from extensions import db
from models import User, ProviderProfile, ServiceRequest, FuelDetails, RepairDetails, TowDetails
from services.location_service import route_order_to_nearest_provider, calculate_haversine_distance

class ProviderRoutingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        with self.app.app_context():
            # Clean up test records
            FuelDetails.query.delete()
            RepairDetails.query.delete()
            TowDetails.query.delete()
            ServiceRequest.query.delete()
            ProviderProfile.query.delete()
            User.query.filter(User.email.like('%@test.com')).delete()
            db.session.commit()

            # Create test admin
            self.admin = User.query.filter_by(role='admin').first()
            if not self.admin:
                self.admin = User(name='Admin Test', email='admin@test.com', phone='9000000001', role='admin')
                self.admin.set_password('admin123')
                db.session.add(self.admin)
                db.session.commit()
            self.admin_id = self.admin.id

            # Create test customer
            self.customer = User(name='Customer Bengaluru', email='customer_blr@test.com', phone='9000000002', role='customer')
            self.customer.set_password('cust123')
            db.session.add(self.customer)
            db.session.commit()
            self.customer_id = self.customer.id

    def login_as(self, user_id):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True

    def test_01_provider_registration_with_service_area(self):
        """Test provider registration capturing city, locality, address, coverage radius and coordinates"""
        form_data = {
            'name': 'Bengaluru Fuel Hub',
            'email': 'blr_fuel1@test.com',
            'phone': '9111111111',
            'password': 'password123',
            'confirm_password': 'password123',
            'business_name': 'Express Bengaluru Fuel',
            'provider_type': 'fuel',
            'license_number': 'LIC-BLR-001',
            'state': 'Karnataka',
            'city': 'Bengaluru',
            'locality': 'Indiranagar',
            'service_address': '100 Feet Rd, Indiranagar, Bengaluru',
            'coverage_radius_km': '25',
            'latitude': '12.9784',
            'longitude': '77.6408'
        }

        resp = self.client.post('/auth/register/provider', data=form_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            user = User.query.filter_by(email='blr_fuel1@test.com').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'provider')
            profile = user.provider_profile
            self.assertIsNotNone(profile)
            self.assertEqual(profile.provider_type, 'fuel')
            self.assertEqual(profile.city, 'Bengaluru')
            self.assertEqual(profile.locality, 'Indiranagar')
            self.assertEqual(profile.coverage_radius_km, 25.0)
            self.assertAlmostEqual(profile.current_lat, 12.9784, places=3)
            self.assertAlmostEqual(profile.current_lng, 77.6408, places=3)
            self.assertEqual(profile.status, 'pending') # Pending admin approval

    def test_02_admin_approval_workflow(self):
        """Test that admin can approve a provider and activate their account"""
        with self.app.app_context():
            user = User(name='Pending Provider', email='pending_p@test.com', phone='9222222222', role='provider')
            user.set_password('pass123')
            db.session.add(user)
            db.session.commit()

            profile = ProviderProfile(
                user_id=user.id,
                business_name='Pending Fuel Works',
                license_number='LIC-BLR-002',
                provider_type='fuel',
                city='Bengaluru',
                coverage_radius_km=20.0,
                current_lat=12.9716,
                current_lng=77.5946,
                status='pending',
                is_available=True
            )
            db.session.add(profile)
            db.session.commit()
            pid = profile.id

        self.login_as(self.admin_id)
        resp = self.client.post(f'/admin/provider/action/{pid}/approve', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            updated = ProviderProfile.query.get(pid)
            self.assertEqual(updated.status, 'approved')

    def test_03_automatic_routing_bengaluru_vs_mysuru(self):
        """Test strict location filtering: Bengaluru customer -> BLR provider, Mysuru customer -> MYS provider"""
        with self.app.app_context():
            # Provider A: Bengaluru Fuel
            u_blr = User(name='BLR Provider', email='blr_fuel@test.com', phone='9333333331', role='provider')
            u_blr.set_password('pass123')
            db.session.add(u_blr)
            db.session.commit()
            p_blr = ProviderProfile(
                user_id=u_blr.id, business_name='Bengaluru Quick Fuel', license_number='LIC-BLR-003', provider_type='fuel',
                city='Bengaluru', coverage_radius_km=25.0,
                current_lat=12.9784, current_lng=77.6408, status='approved', is_available=True
            )
            db.session.add(p_blr)

            # Provider B: Mysuru Fuel
            u_mys = User(name='MYS Provider', email='mys_fuel@test.com', phone='9333333332', role='provider')
            u_mys.set_password('pass123')
            db.session.add(u_mys)
            db.session.commit()
            p_mys = ProviderProfile(
                user_id=u_mys.id, business_name='Mysuru Chamundi Fuel', license_number='LIC-MYS-001', provider_type='fuel',
                city='Mysuru', coverage_radius_km=25.0,
                current_lat=12.2958, current_lng=76.6394, status='approved', is_available=True
            )
            db.session.add(p_mys)
            db.session.commit()

            blr_id = p_blr.id
            mys_id = p_mys.id

        # 1. Routing function for Bengaluru customer (12.9716, 77.5946)
        with self.app.app_context():
            prov, dist = route_order_to_nearest_provider('fuel', 12.9716, 77.5946, customer_city='Bengaluru')
            self.assertIsNotNone(prov)
            self.assertEqual(prov.id, blr_id, "Bengaluru order must be assigned to Bengaluru provider!")
            self.assertNotEqual(prov.id, mys_id, "Bengaluru order must NOT be assigned to Mysuru provider!")
            self.assertLess(dist, 10.0)

        # 2. Routing function for Mysuru customer (12.2958, 76.6394)
        with self.app.app_context():
            prov, dist = route_order_to_nearest_provider('fuel', 12.2958, 76.6394, customer_city='Mysuru')
            self.assertIsNotNone(prov)
            self.assertEqual(prov.id, mys_id, "Mysuru order must be assigned to Mysuru provider!")
            self.assertNotEqual(prov.id, blr_id, "Mysuru order must NOT be assigned to Bengaluru provider!")
            self.assertLess(dist, 5.0)

        # 3. Exclude non-matching category: repair search doesn't return fuel provider
        with self.app.app_context():
            repair_prov, _ = route_order_to_nearest_provider('mechanic', 12.9716, 77.5946, customer_city='Bengaluru')
            self.assertIsNone(repair_prov)

    def test_04_customer_booking_and_provider_dashboard_isolation(self):
        """Test customer submits Fuel booking and provider dashboard isolates orders strictly"""
        with self.app.app_context():
            # BLR Provider
            u1 = User(name='BLR Prov', email='blr_dash@test.com', phone='9444444441', role='provider')
            u1.set_password('pass123')
            db.session.add(u1)
            db.session.commit()
            p1 = ProviderProfile(
                user_id=u1.id, business_name='BLR Dispatcher', license_number='LIC-BLR-004', provider_type='fuel',
                city='Bengaluru', coverage_radius_km=25.0,
                current_lat=12.9716, current_lng=77.5946, status='approved', is_available=True
            )
            db.session.add(p1)

            # MYS Provider
            u2 = User(name='MYS Prov', email='mys_dash@test.com', phone='9444444442', role='provider')
            u2.set_password('pass123')
            db.session.add(u2)
            db.session.commit()
            p2 = ProviderProfile(
                user_id=u2.id, business_name='MYS Dispatcher', license_number='LIC-MYS-002', provider_type='fuel',
                city='Mysuru', coverage_radius_km=25.0,
                current_lat=12.2958, current_lng=76.6394, status='approved', is_available=True
            )
            db.session.add(p2)
            db.session.commit()

            p1_uid = u1.id
            p2_uid = u2.id
            p1_id = p1.id

        # Customer books in Bengaluru
        self.login_as(self.customer_id)
        post_data = {
            'fuel_type': 'petrol',
            'quantity': '10',
            'pickup_address': 'MG Road, Bengaluru, Karnataka',
            'locality': 'MG Road',
            'pickup_lat': '12.9740',
            'pickup_lng': '77.6080'
        }
        res = self.client.post('/customer/request/fuel', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB assignment
        with self.app.app_context():
            booking = ServiceRequest.query.filter_by(service_type='fuel').order_by(ServiceRequest.id.desc()).first()
            self.assertIsNotNone(booking)
            self.assertEqual(booking.provider_id, p1_id)
            self.assertEqual(booking.status, 'pending')

        # BLR Provider logs in: sees order in dashboard
        self.login_as(p1_uid)
        dash_res = self.client.get('/provider/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(str(booking.request_number).encode(), dash_res.data)

        # MYS Provider logs in: does NOT see the BLR order in dashboard
        self.login_as(p2_uid)
        dash_mys = self.client.get('/provider/dashboard')
        self.assertEqual(dash_mys.status_code, 200)
        self.assertNotIn(str(booking.request_number).encode(), dash_mys.data)

    def test_05_provider_rejection_and_rerouting(self):
        """Test that if assigned provider rejects, order re-routes to next eligible provider in service area"""
        with self.app.app_context():
            # Provider 1 in BLR
            u1 = User(name='BLR Primary', email='blr_prim@test.com', phone='9555555551', role='provider')
            u1.set_password('pass123')
            db.session.add(u1)
            db.session.commit()
            p1 = ProviderProfile(
                user_id=u1.id, business_name='Primary Fuel', license_number='LIC-BLR-005', provider_type='fuel',
                city='Bengaluru', coverage_radius_km=25.0,
                current_lat=12.9716, current_lng=77.5946, status='approved', is_available=True
            )
            db.session.add(p1)

            # Provider 2 in BLR (secondary)
            u2 = User(name='BLR Backup', email='blr_back@test.com', phone='9555555552', role='provider')
            u2.set_password('pass123')
            db.session.add(u2)
            db.session.commit()
            p2 = ProviderProfile(
                user_id=u2.id, business_name='Backup Fuel', license_number='LIC-BLR-006', provider_type='fuel',
                city='Bengaluru', coverage_radius_km=25.0,
                current_lat=12.9780, current_lng=77.6000, status='approved', is_available=True
            )
            db.session.add(p2)
            db.session.commit()

            p1_uid = u1.id
            p2_uid = u2.id
            p1_id = p1.id
            p2_id = p2.id

            # Create service request assigned to p1
            req = ServiceRequest(
                customer_id=self.customer_id,
                provider_id=p1_id,
                service_type='fuel',
                status='pending',
                city='Bengaluru',
                pickup_address='MG Road, Bengaluru',
                pickup_lat=12.9740,
                pickup_lng=77.6080,
                estimated_fee=150.0,
                final_amount=150.0
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        # Provider 1 rejects
        self.login_as(p1_uid)
        rej_res = self.client.post(f'/provider/request/reject/{req_id}', data={'reason': 'Busy with another delivery'}, follow_redirects=True)
        self.assertEqual(rej_res.status_code, 200)

        # Order must now be re-routed to Provider 2!
        with self.app.app_context():
            updated = ServiceRequest.query.get(req_id)
            self.assertEqual(updated.provider_id, p2_id, "Order should re-route to secondary provider!")
            self.assertEqual(updated.status, 'pending')
            self.assertIn(str(p1_id), updated.rejected_provider_ids)

        # Provider 2 also rejects: no more providers in BLR, so status becomes 'unassigned'
        self.login_as(p2_uid)
        rej_res2 = self.client.post(f'/provider/request/reject/{req_id}', data={'reason': 'No stock'}, follow_redirects=True)
        self.assertEqual(rej_res2.status_code, 200)

        with self.app.app_context():
            updated2 = ServiceRequest.query.get(req_id)
            self.assertIsNone(updated2.provider_id)
            self.assertEqual(updated2.status, 'unassigned')

    def test_06_no_provider_in_area_marks_unassigned(self):
        """Test booking in an area with no active providers sets status to unassigned and gives clear message"""
        # Customer books in Sullia (no registered providers in Sullia)
        self.login_as(self.customer_id)
        post_data = {
            'fuel_type': 'petrol',
            'quantity': '5',
            'pickup_address': 'Main Road, Sullia, Karnataka',
            'locality': 'Sullia Town',
            'pickup_lat': '12.5562',
            'pickup_lng': '75.3892'
        }
        res = self.client.post('/customer/request/fuel', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        # Verify exact required message is present
        self.assertIn(b"No service provider is currently available in your area. Please try again later or contact support.", res.data)

        with self.app.app_context():
            booking = ServiceRequest.query.filter_by(service_type='fuel').order_by(ServiceRequest.id.desc()).first()
            self.assertIsNotNone(booking)
            self.assertEqual(booking.status, 'unassigned')
            self.assertIsNone(booking.provider_id)

    def test_07_provider_authorization_protection(self):
        """Test provider cannot accept an order assigned to a different provider"""
        with self.app.app_context():
            u1 = User(name='Authorized Prov', email='auth_p@test.com', phone='9666666661', role='provider')
            u1.set_password('pass123')
            db.session.add(u1)
            u2 = User(name='Unauthorized Prov', email='unauth_p@test.com', phone='9666666662', role='provider')
            u2.set_password('pass123')
            db.session.add(u2)
            db.session.commit()

            p1 = ProviderProfile(user_id=u1.id, business_name='Auth Prov', license_number='LIC-AUTH-001', provider_type='fuel', current_lat=12.9716, current_lng=77.5946, status='approved', is_available=True)
            p2 = ProviderProfile(user_id=u2.id, business_name='Unauth Prov', license_number='LIC-UNAUTH-001', provider_type='fuel', current_lat=12.9716, current_lng=77.5946, status='approved', is_available=True)
            db.session.add_all([p1, p2])
            db.session.commit()

            req = ServiceRequest(
                customer_id=self.customer_id,
                provider_id=p1.id,
                service_type='fuel',
                status='pending',
                pickup_address='Bengaluru',
                pickup_lat=12.9716,
                pickup_lng=77.5946
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id
            unauth_uid = u2.id

        # Unauthorized provider attempts to accept
        self.login_as(unauth_uid)
        resp = self.client.post(f'/provider/request/accept/{req_id}', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Verify order was NOT accepted
        with self.app.app_context():
            chk = ServiceRequest.query.get(req_id)
            self.assertNotEqual(chk.status, 'accepted')
            self.assertEqual(chk.status, 'pending')

if __name__ == '__main__':
    unittest.main()
