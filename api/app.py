"""
Flask Application Factory
===========================
Creates and configures the Flask application.

  • Serves the dashboard template at ``/``
  • Registers the API blueprint (``/api/*``)
  • Enables CORS for frontend communication
"""

from flask import Flask
from flask_cors import CORS

from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> Flask:
    """
    Application factory.

    Returns
    -------
    Flask
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder=str(Settings.TEMPLATES_FOLDER),
        static_folder=str(Settings.STATIC_FOLDER),
    )
    app.config["SECRET_KEY"] = Settings.SECRET_KEY

    # Enable CORS for all API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from api.routes import api_bp
    app.register_blueprint(api_bp)

    # Dashboard route
    @app.route("/")
    def dashboard():
        """Serve the main dashboard page."""
        from flask import render_template
        return render_template("index.html")

    logger.info("Flask application created")
    return app
