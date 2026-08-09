"""
Application factory.

Wires the layers together:
  presentation (templates)  ->  business logic (blueprints, scoring)
  ->  data access (SQLAlchemy ORM)  ->  database (SQLite)
"""
import os
import subprocess
from flask import Flask
from flask_login import LoginManager

from .models import db, User

_FALLBACK_VERSION = "0.4.0-dev"  # used only when git or tags are unavailable


def _describe():
    """Version derived from git tags via `git describe`:
      '0.9.0' exactly on the v0.9.0 tag, '0.9.0-3-gabc1234' three commits later,
      or a short hash if no tag is reachable. Falls back when git is absent."""
    try:
        repo_root = os.path.dirname(os.path.dirname(__file__))
        r = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=repo_root, capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().lstrip("v")
    except Exception:
        pass
    return _FALLBACK_VERSION


__version__ = _describe()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."


def create_app(config=None):
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "dora.db")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if config:
        app.config.update(config)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth_bp
    from .main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_version():
        return {"app_version": __version__}

    with app.app_context():
        db.create_all()

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))