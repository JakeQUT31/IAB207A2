import os
from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

DB_NAME = "sporttix.db"

def create_app(test_config=None):
    app = Flask(__name__)
    Bootstrap5(app)
    app.config['SECRET_KEY'] = 'thisisasecret'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    create_database(app)

    from . import views
    app.register_blueprint(views.main_bp)

    from . import eventsRoutes
    app.register_blueprint(eventsRoutes.event_bp)

    from . import auth
    app.register_blueprint(auth.auth_bp)

    from . import bookings
    app.register_blueprint(bookings.booking_bp)

    return app

def create_database(app):
    db_path = os.path.join("website", DB_NAME)
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all()
        print('Created Database!')