from models import Notification
from extensions import db

def create_notification(user_id, title, message, link=None):
    """
    Creates and saves a system notification for a specific user.
    """
    try:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    except Exception as e:
        db.session.rollback()
        print(f"Error creating notification: {e}")
        return None
