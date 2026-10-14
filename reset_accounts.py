from app import create_app, db
from models import (
    User, ProviderProfile, Vehicle, ServiceRequest, FuelDetails, RepairDetails, TowDetails,
    Product, CartItem, Order, OrderItem, Payment, Notification, ChatMessage, Review, AdminLog
)

def reset_all_accounts():
    app = create_app()
    with app.app_context():
        print("[*] Deleting all service requests and details...")
        FuelDetails.query.delete()
        RepairDetails.query.delete()
        TowDetails.query.delete()
        ServiceRequest.query.delete()

        print("[*] Deleting all vehicles, cart items, orders, payments, reviews, chats, notifications...")
        Vehicle.query.delete()
        CartItem.query.delete()
        OrderItem.query.delete()
        Order.query.delete()
        Payment.query.delete()
        Review.query.delete()
        Notification.query.delete()
        ChatMessage.query.delete()
        AdminLog.query.delete()

        print("[*] Deleting all provider profiles...")
        ProviderProfile.query.delete()

        print("[*] Deleting all user accounts...")
        User.query.delete()

        print("[*] Re-creating clean Administrator accounts...")
        admin1 = User(
            name="BSMANOJGOWDA",
            email="admin@gamil.com",
            phone="+91 9876543210",
            role="admin"
        )
        admin1.set_password("admin123")
        db.session.add(admin1)

        admin2 = User(
            name="System Administrator",
            email="admin@motoserve360.com",
            phone="+91 9876543211",
            role="admin"
        )
        admin2.set_password("admin123")
        db.session.add(admin2)

        db.session.commit()
        print("\n[SUCCESS] All accounts and booking data have been completely wiped!")
        print("[+] Existing Users in Database:")
        for u in User.query.all():
            print(f"    - [{u.role.upper()}] {u.name} | Email: {u.email}")
        print(f"[+] Total Customers: {User.query.filter_by(role='customer').count()}")
        print(f"[+] Total Providers: {User.query.filter_by(role='provider').count()}")
        print(f"[+] Total Service Requests: {ServiceRequest.query.count()}")
        print(f"[+] Total Vehicles: {Vehicle.query.count()}")

if __name__ == '__main__':
    reset_all_accounts()
