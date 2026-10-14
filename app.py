from flask import Flask, render_template
from flask_login import current_user
from config import Config
from extensions import db, login_manager, migrate, session_ext, mail

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    
    migrate.init_app(app, db)
    session_ext.init_app(app)
    mail.init_app(app)

    # Safe Schema Verification & Non-destructive Migration
    from migrate_db import migrate_database
    with app.app_context():
        migrate_database()

    # Register Blueprints
    from routes import main_bp, auth_bp, customer_bp, provider_bp, admin_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # User loader for Flask-Login
    from models import User, CartItem, Notification
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Global Context Processor
    from services import get_system_settings
    @app.context_processor
    def inject_global_vars():
        unread_notifications_count = 0
        cart_items_count = 0
        if current_user.is_authenticated:
            unread_notifications_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
            if current_user.is_customer():
                cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
                cart_items_count = sum(item.quantity for item in cart_items)

        return dict(
            unread_notifications_count=unread_notifications_count,
            cart_items_count=cart_items_count,
            system_settings=get_system_settings()
        )

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('base.html', page_error="404 - Page Not Found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('base.html', page_error="500 - Internal Server Error"), 500

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
