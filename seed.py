from extensions import db
from models import (
    User, ProviderProfile, Vehicle, ServiceRequest, FuelDetails, RepairDetails, TowDetails,
    Product, CartItem, Order, OrderItem, Payment, Notification, ChatMessage, Review, AdminLog
)

def populate_seed_data():
    """Populates the database with initial demo accounts, products, and records."""
    if User.query.first() is not None and Product.query.first() is not None:
        return

        # 1. CREATE ADMIN USER
        admin = User(
            name="System Administrator",
            email="admin@motoserve360.com",
            phone="+91 9876543210",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)

        # 2. CREATE CUSTOMERS
        customer1 = User(
            name="Alex Johnson",
            email="alex@example.com",
            phone="+91 9123456789",
            role="customer"
        )
        customer1.set_password("customer123")

        customer2 = User(
            name="Sarah Parker",
            email="sarah@example.com",
            phone="+91 9988776655",
            role="customer"
        )
        customer2.set_password("customer123")

        db.session.add_all([customer1, customer2])
        db.session.flush()

        # 3. CREATE CUSTOMER VEHICLES
        v1 = Vehicle(
            user_id=customer1.id,
            make="Honda",
            model="City ZX",
            year=2023,
            license_plate="KA-01-MJ-2026",
            fuel_type="petrol",
            vehicle_type="car"
        )
        v2 = Vehicle(
            user_id=customer1.id,
            make="Royal Enfield",
            model="Classic 350",
            year=2022,
            license_plate="KA-05-RE-8899",
            fuel_type="petrol",
            vehicle_type="bike"
        )
        v3 = Vehicle(
            user_id=customer2.id,
            make="Hyundai",
            model="Creta SX",
            year=2024,
            license_plate="KA-03-HY-4411",
            fuel_type="diesel",
            vehicle_type="car"
        )
        db.session.add_all([v1, v2, v3])

        # 4. CREATE SERVICE PROVIDERS
        # Provider 1: Fuel Delivery
        p1_user = User(
            name="Rajesh Kumar",
            email="fuel_express@motoserve.com",
            phone="+91 9811122233",
            role="provider"
        )
        p1_user.set_password("provider123")
        db.session.add(p1_user)
        db.session.flush()

        p1_profile = ProviderProfile(
            user_id=p1_user.id,
            provider_type="fuel",
            business_name="Express Fuel Tankers",
            license_number="FL-99201-IND",
            is_online=True,
            current_lat=12.9780,
            current_lng=77.5990,
            rating=4.9,
            total_ratings=12,
            status="approved"
        )
        db.session.add(p1_profile)

        # Provider 2: Mechanic
        p2_user = User(
            name="David Miller",
            email="quick_mechanic@motoserve.com",
            phone="+91 9844455566",
            role="provider"
        )
        p2_user.set_password("provider123")
        db.session.add(p2_user)
        db.session.flush()

        p2_profile = ProviderProfile(
            user_id=p2_user.id,
            provider_type="mechanic",
            business_name="Apex Auto Pitstop Garage",
            license_number="MC-54321-KA",
            is_online=True,
            current_lat=12.9650,
            current_lng=77.5900,
            rating=4.8,
            total_ratings=25,
            status="approved"
        )
        db.session.add(p2_profile)

        # Provider 3: Towing Driver
        p3_user = User(
            name="Vikram Singh",
            email="titan_tow@motoserve.com",
            phone="+91 9777788899",
            role="provider"
        )
        p3_user.set_password("provider123")
        db.session.add(p3_user)
        db.session.flush()

        p3_profile = ProviderProfile(
            user_id=p3_user.id,
            provider_type="tow",
            business_name="Titan Towing & Recovery",
            license_number="TW-88771-KA",
            is_online=True,
            current_lat=12.9800,
            current_lng=77.6100,
            rating=5.0,
            total_ratings=8,
            status="approved"
        )
        db.session.add(p3_profile)

        # Provider 4: Pending Approval Demo
        p4_user = User(
            name="Suresh Patel",
            email="pending_mechanic@motoserve.com",
            phone="+91 9666655544",
            role="provider"
        )
        p4_user.set_password("provider123")
        db.session.add(p4_user)
        db.session.flush()

        p4_profile = ProviderProfile(
            user_id=p4_user.id,
            provider_type="mechanic",
            business_name="Suresh Mobile Repair Garage",
            license_number="MC-11002-KA",
            is_online=False,
            current_lat=12.9500,
            current_lng=77.5800,
            rating=5.0,
            total_ratings=1,
            status="pending"
        )
        db.session.add(p4_profile)
        db.session.flush()

        # Provider 5: Mysuru Fuel Delivery Partner
        p5_user = User(
            name="Ramesh Gowda",
            email="mysore_fuel@motoserve.com",
            phone="+91 9880011223",
            role="provider"
        )
        p5_user.set_password("provider123")
        db.session.add(p5_user)
        db.session.flush()

        p5_profile = ProviderProfile(
            user_id=p5_user.id,
            provider_type="fuel",
            business_name="Chamundi Express Fuel Logistics",
            license_number="FL-44021-MYS",
            is_online=True,
            current_lat=12.3020,
            current_lng=76.6450,
            rating=4.9,
            total_ratings=19,
            status="approved"
        )
        db.session.add(p5_profile)

        # Provider 6: Mysuru Mechanic Partner
        p6_user = User(
            name="Anand Murthy",
            email="mysore_mechanic@motoserve.com",
            phone="+91 9880033445",
            role="provider"
        )
        p6_user.set_password("provider123")
        db.session.add(p6_user)
        db.session.flush()

        p6_profile = ProviderProfile(
            user_id=p6_user.id,
            provider_type="mechanic",
            business_name="Royal Mysore Auto Works & Garage",
            license_number="MC-77112-MYS",
            is_online=True,
            current_lat=12.2980,
            current_lng=76.6380,
            rating=4.8,
            total_ratings=31,
            status="approved"
        )
        db.session.add(p6_profile)

        # Provider 7: Mysuru Towing Partner
        p7_user = User(
            name="Chetan Kumar",
            email="mysore_tow@motoserve.com",
            phone="+91 9880055667",
            role="provider"
        )
        p7_user.set_password("provider123")
        db.session.add(p7_user)
        db.session.flush()

        p7_profile = ProviderProfile(
            user_id=p7_user.id,
            provider_type="tow",
            business_name="Chamundi Rapid Towing Services",
            license_number="TW-99334-MYS",
            is_online=True,
            current_lat=12.3100,
            current_lng=76.6500,
            rating=5.0,
            total_ratings=14,
            status="approved"
        )
        db.session.add(p7_profile)
        db.session.flush()

        # 5. CREATE E-COMMERCE PRODUCTS
        products = [
            Product(
                name="Motul 7100 4T 10W40 Fully Synthetic Engine Oil (1L)",
                category="Engine Oil",
                price=950.00,
                stock=50,
                description="Premium 100% synthetic lubricant for high-performance 4-stroke motorcycle engines.",
                discount_percentage=10.0,
                image_url="https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?w=500&q=80"
            ),
            Product(
                name="Exide Xplore 12V 35Ah Maintenance Free Car Battery",
                category="Battery",
                price=4200.00,
                stock=15,
                description="Heavy duty maintenance-free battery with 48-month warranty for cars.",
                discount_percentage=5.0,
                image_url="https://images.unsplash.com/photo-1620021650390-349c25608d0e?w=500&q=80"
            ),
            Product(
                name="Michelin Pilot Sport 4 Car Tyre 205/55 R16",
                category="Tyres",
                price=8500.00,
                stock=20,
                description="Ultra-high performance tyre engineered for exceptional grip on wet and dry roads.",
                discount_percentage=12.0,
                image_url="https://images.unsplash.com/photo-1578844251758-2f71da64c96f?w=500&q=80"
            ),
            Product(
                name="Studds Ninja Elite Full Face Helmet (Matt Black)",
                category="Helmet",
                price=1850.00,
                stock=30,
                description="ISI certified full face helmet with quick release visor and anti-allergic padding.",
                discount_percentage=15.0,
                image_url="https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=500&q=80"
            ),
            Product(
                name="Brembo Front Ceramic Brake Pad Set",
                category="Brake Pads",
                price=2400.00,
                stock=25,
                description="Superior braking performance and low noise ceramic pad composition.",
                discount_percentage=8.0,
                image_url="https://images.unsplash.com/photo-1600706432520-72ce6f809d43?w=500&q=80"
            ),
            Product(
                name="3M Auto Care Complete Car Cleaning Kit",
                category="Cleaning Kit",
                price=1250.00,
                stock=40,
                description="Includes Car Wash Shampoo, Liquid Wax, Tyre Dresser, and Microfiber Cloth.",
                discount_percentage=20.0,
                image_url="https://images.unsplash.com/photo-1520340356584-f9917d1eea6f?w=500&q=80"
            )
        ]
        db.session.add_all(products)
        db.session.flush()

        # 6. CREATE INITIAL SERVICE REQUESTS (FOR ACTIVE DEMO)
        req1 = ServiceRequest(
            customer_id=customer1.id,
            provider_id=p1_profile.id,
            vehicle_id=v1.id,
            service_type="fuel",
            status="travelling",
            pickup_address="MG Road Metro Station, Bengaluru",
            pickup_lat=12.9756,
            pickup_lng=77.6068,
            estimated_fee=562.50,
            final_amount=562.50,
            payment_status="paid"
        )
        db.session.add(req1)
        db.session.flush()

        fd1 = FuelDetails(
            request_id=req1.id,
            fuel_type="petrol",
            quantity_litres=5.0,
            fuel_price_per_litre=102.50,
            delivery_fee=50.0
        )
        db.session.add(fd1)

        # 7. ADD INITIAL REVIEWS
        rev1 = Review(
            request_id=req1.id,
            customer_id=customer1.id,
            provider_id=p1_profile.id,
            rating=5,
            comment="Arrived within 15 minutes! Delivered clean petrol directly into my tank. Extremely recommended!"
        )
        db.session.add(rev1)

        db.session.commit()
        print("[SUCCESS] Database successfully seeded with demo accounts, vehicles, providers, products, and active requests!")

def seed_database():
    print("[+] Initializing database and seeding data...")
    from app import app
    with app.app_context():
        db.drop_all()
        db.create_all()
        populate_seed_data()

if __name__ == '__main__':
    seed_database()
