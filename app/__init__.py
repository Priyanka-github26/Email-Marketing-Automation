
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config
from flask_mail import Mail

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    mail.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))

    from app.auth import auth
    app.register_blueprint(auth)

    from app.routes import main
    app.register_blueprint(main)

    return app
