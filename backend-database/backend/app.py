from flask import Flask, has_request_context, g, render_template, request, jsonify, current_app
# import stripe
# --- ESSENTIAL IMPORTS ---
from models.lead_model import db # <-- Import the shared 'db' object
from services.backend_robodialer.database.db_init import init_db_connection # <-- Updated path for reorganized structure


# --- BLUEPRINT IMPORTS ---
# from routes.lead_routes import lead_bp
# from routes.main_routes import main_bp
# from routes.auth_routes import auth_bp
# from routes.user_lead_draft_routes import draft_bp
# from routes.credit_routes import credit_bp
# from routes.user_management_routes import user_management_bp
from config.config import config
from flask_login import LoginManager, current_user
from models.user_model import User
from sqlalchemy import event, text
from flask_cors import CORS
# from routes.subscription_routes import subscription_bp
from logging_setup import setup_logging
# from routes.customer_portal_routes import customer_portal_bp
# from routes.contact_routes import contact_bp
from utils.email_utils import init_mail
# from routes.stripe_webhook_routes import stripe_webhook_bp
# from routes.message_routes import message_bp
# from routes.dashboard_routes import dashboard_bp
# from models.release_note_model import ReleaseNote
# from models.user_read_note_model import UserReadNote
# from routes.release_note_routes import bp as release_note_bp
from datetime import datetime
# from routes.admin_routes import bp as admin_bp
# from routes.release_note_views import bp as release_note_views_bp
# from routes.company_routes import bp as company_bp
# from routes.workspace_routes import workspace_bp
# from routes.workspace_web_routes import workspace_web_bp
# from routes.location_routes import location_bp
# from routes.team_routes import team_bp
# from routes.user_routes import user_bp
# from routes.invitation_routes import bp as invitation_bp
# from routes.workspace_task_routes import workspace_task_bp
# from routes.task_lead_routes import task_lead_bp
# from routes.company_news_insight_routes import news_insight_bp
# from routes.feedback_routes import feedback_bp
# from routes.emailgen_template_routes import emailgen_template_bp
# from routes.workspace_join_request_routes import workspace_join_request_bp
# from routes.credit_transfer_log_routes import credit_transfer_log_bp
# from routes.task_submission_routes import task_submission_bp
# from routes.role_request_routes import role_request_bp
# from routes.ai_analysis_routes import ai_analysis_bp
# from routes.coupon_routes import coupon_bp
# from routes.finance_report_gen.financial_report_upload_route import fin_report_upload_bp
# from routes.finance_report_gen.financial_file_route import fin_file_bp
# from routes.finance_report_gen.finance_mapping_routes import fin_stand_col_bp
# from routes.finance_report_gen.save_mapping_routes import fin_save_mapping_bp
# from routes.finance_report_gen.file_upload_route import fin_file_upload_bp
# from routes.contact_verification.contact_verification_routes import contact_verification_bp
# from routes.growjo_aws_apis.growjo_aws_routes import growjo_aws_bp
# from routes.apollo_aws_routes import apollo_bp
# from routes.company_insights_routes import company_insights_bp
# from routes.finance_report_gen.finance_kpi_routes import fin_kpi_cal_bp # KPI calcualtion kpi
# from routes.finance_report_gen.normalized_financial_data_routes import fin_normalized_data_bp
# from routes.finance_report_gen.report_generation_routes import report_gen_bp
# from routes.finance_report_gen.historical_kpi_routes import historical_kpi_bp
# from routes.credits_log_routes import credits_log_bp
# from services.backend_agentic.main import agentic_backend_bp  # Commented out due to dependency issues
from services.backend_robodialer.database.app import robo_dailer_bp # <-- Updated path for reorganized structure

def create_app(config_class=config):
    """Create and configure the Flask application"""
    setup_logging()
    app = Flask(__name__)
    app.config.from_object(config_class)

    # :white_check_mark: Production cookie settings for session auth
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True

    # Initialize CORS
    CORS(app, origins=[
        "http://localhost:3000",
        "http://54.71.107.242:3000",
        "http://54.71.107.242:9002",
        "http://localhost:3000"
        "http://localhost:5173",
        "http://localhost:9002",  # Added for RoboDialer frontend
        "https://capraeleadseekers.site",
        "https://35.165.209.201",
        "https://main.d2fzqm2i2qb7f3.amplifyapp.com",
        "http://35.165.209.201",
        "https://sandboxdev.saasquatchleads.com",
        "https://www.saasquatchleads.com",
        "http://54.166.155.63:3000",
        "http://54.166.155.63",
        "https://app.saasquatchleads.com",
    ], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True)

    # Initialize extensions

    # 💡 FIX: Use the non-blocking initialization function
    init_db_connection(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Initialize Flask-Mail
    init_mail(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            current_app.logger.info(f"Logged in user is : {user_id}")
            # Use db.session.get for modern SQLAlchemy
            return db.session.get(User, str(user_id))
        except Exception as e:
            current_app.logger.error(f"Error loading user: {e}")
            return None

    def set_app_user_on_connect(dbapi_connection, connection_record):
        try:
            # Only set if in a request context and user is authenticated
            if has_request_context() and current_user.is_authenticated:
                username = getattr(current_user, 'username', None)
                if username:
                    cursor = dbapi_connection.cursor()
                    # Execute SQL function to set the app user
                    cursor.execute("SELECT set_app_user(%s);", (username,))
                    cursor.close()
        except Exception:
            pass # Ignore if user is not available (e.g., during migrations)

    # Register blueprints (All unchanged)
    # app.register_blueprint(main_bp)
    # app.register_blueprint(auth_bp)
    # app.register_blueprint(lead_bp)
    # app.register_blueprint(subscription_bp)
    # app.register_blueprint(credit_bp)
    # app.register_blueprint(customer_portal_bp)
    # app.register_blueprint(contact_bp)
    # app.register_blueprint(user_management_bp)
    # app.register_blueprint(stripe_webhook_bp)
    # app.register_blueprint(message_bp)
    # app.register_blueprint(draft_bp)
    # app.register_blueprint(dashboard_bp)
    # app.register_blueprint(release_note_bp)
    # app.register_blueprint(admin_bp)
    # app.register_blueprint(release_note_views_bp)
    # app.register_blueprint(company_bp)
    # app.register_blueprint(workspace_bp)
    # app.register_blueprint(workspace_web_bp)
    # app.register_blueprint(location_bp)
    # app.register_blueprint(team_bp)
    # app.register_blueprint(user_bp)
    # app.register_blueprint(invitation_bp)
    # app.register_blueprint(workspace_task_bp)
    # app.register_blueprint(task_lead_bp)
    # app.register_blueprint(news_insight_bp, url_prefix='')
    # app.register_blueprint(feedback_bp)
    # app.register_blueprint(emailgen_template_bp)
    # app.register_blueprint(workspace_join_request_bp)
    # app.register_blueprint(credit_transfer_log_bp)
    # app.register_blueprint(task_submission_bp)
    # app.register_blueprint(role_request_bp)
    # app.register_blueprint(ai_analysis_bp)
    # app.register_blueprint(coupon_bp)
    # app.register_blueprint(fin_file_upload_bp)
    # app.register_blueprint(fin_report_upload_bp)
    # app.register_blueprint(fin_file_bp)
    # app.register_blueprint(fin_stand_col_bp)
    # app.register_blueprint(fin_save_mapping_bp)
    # app.register_blueprint(fin_kpi_cal_bp)
    # app.register_blueprint(growjo_aws_bp)
    # app.register_blueprint(apollo_bp)
    # app.register_blueprint(fin_normalized_data_bp)
    # app.register_blueprint(report_gen_bp)
    # app.register_blueprint(historical_kpi_bp)
    # app.register_blueprint(contact_verification_bp)
    # app.register_blueprint(credits_log_bp)

    # app.register_blueprint(agentic_backend_bp)  # Commented out due to dependency issues
    app.register_blueprint(robo_dailer_bp)

    # Final setup in application context
    with app.app_context():
        # ❌ REMOVED: db.create_all() - Use Alembic instead for production.
        event.listen(db.engine, "connect", set_app_user_on_connect)

        # stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    # Add missing Jinja2 filters
    @app.template_filter('todate')
    def todate_filter(value, format='%Y-%m-%d'):
        """Format a date object to string"""
        if value is None:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime(format)
        return str(value)

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # This remains the same, but the app starts faster now.
    app.run(debug=True, host='0.0.0.0', port=8001)