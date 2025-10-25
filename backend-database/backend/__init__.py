from flask import Flask, redirect, url_for
from flask_login import LoginManager
from models.user_model import User, db
import os
from uuid import UUID as UUID_type


def create_app(test_config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)

    # Set default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Initialize database
    db.init_app(app)

    # Create database tables if they do not exist
    with app.app_context():
        # Import all models to ensure they're registered with SQLAlchemy
        from models.user_model import User
        from models.lead_model import Lead
        from models.user_lead_drafts_model import UserLeadDraft
        from models.search_logs_model import SearchLog
        from models.audit_logs_model import AuditLog
        from models.release_note_model import ReleaseNote
        from models.user_read_note_model import UserReadNote

        # Create all tables
        db.create_all()

    # Set up LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(UUID_type(user_id))
        except Exception:
            return None

    # Register blueprints
    print("Starting blueprint registration...")

    from routes.lead_routes import lead_bp
    from routes.auth_routes import auth_bp
    from routes.lead_drafts_routes import drafts_bp
    from routes.edit_drafts_routes import drafts_edit_bp
    from routes.release_note_routes import release_note_bp
    from routes.release_note_views_routes import release_note_views_bp
    from routes.admin_routes import admin_bp
    from routes.company_news_insight_routes import news_insight_bp
    from routes.finance_report_gen.file_upload_route import fin_file_upload_bp

    app.register_blueprint(lead_bp, url_prefix='')
    app.register_blueprint(auth_bp, url_prefix='')
    app.register_blueprint(drafts_bp, url_prefix='')
    app.register_blueprint(drafts_edit_bp, url_prefix='')
    app.register_blueprint(release_note_bp, url_prefix='')
    app.register_blueprint(release_note_views_bp, url_prefix='')
    app.register_blueprint(admin_bp, url_prefix='')
    app.register_blueprint(news_insight_bp, url_prefix='')
    app.register_blueprint(fin_file_upload_bp, url_prefix='')

    # Create a basic route
    @app.route('/')
    def index():
        return 'LeadGen API is running!'

    return app


# Create application instance
app = create_app()
