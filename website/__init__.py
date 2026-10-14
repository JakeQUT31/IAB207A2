import os
from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

DB_NAME = "sporttix.db"

def create_app(test_config=None):
    app = Flask(__name__)
    Bootstrap5(app)
    app.config.from_mapping(
        SECRET_KEY='thisisasecret',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{DB_NAME}',
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    CSRFProtect(app)
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

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app

def create_database(app):
    db_path = os.path.join("website", DB_NAME)
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all()
        print('Created Database!')