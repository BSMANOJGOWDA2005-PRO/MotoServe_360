from app import app
from extensions import db
from models import (
    User, ProviderProfile, Vehicle, ServiceRequest, FuelDetails, RepairDetails, TowDetails,
    CartItem, Order, OrderItem, Payment, Notification, ChatMessage, Review, AdminLog
)

def clear_all_accounts():
    print("[*] Clearing all user accounts, provider profiles, and user-generated records...")
    with app.app_context():
        try:
            # Delete dependent transaction records
            ChatMessage.query.delete()
            Notification.query.delete()
            Review.query.delete()
            AdminLog.query.delete()
            Payment.query.delete()
            OrderItem.query.delete()
            Order.query.delete()
            CartItem.query.delete()
            
            # Delete service request detail records
            FuelDetails.query.delete()
            RepairDetails.query.delete()
            TowDetails.query.delete()
            ServiceRequest.query.delete()
            
            # Delete vehicle records
            Vehicle.query.delete()
            
            # Delete provider profiles & user accounts
            ProviderProfile.query.delete()
            User.query.delete()

            db.session.commit()
            print("[SUCCESS] All user accounts (Admin, Provider, Customer) and related data successfully removed.")
        except Exception as e:
            db.session.rollback()
            print(f"[!] Error clearing accounts: {e}")

if __name__ == '__main__':
    clear_all_accounts()
