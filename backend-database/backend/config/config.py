import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base config class"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # Use os.getenv for reading environment variables
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

    # Read individual price IDs and reconstruct the dictionary
    STRIPE_PRICES = {
        'bronze': os.getenv('STRIPE_PRICE_BRONZE'),
        'silver': os.getenv('STRIPE_PRICE_SILVER'),
        'gold': os.getenv('STRIPE_PRICE_GOLD'),
        'platinum': os.getenv('STRIPE_PRICE_PLATINUM'),
        'bronze_annual': os.getenv('STRIPE_PRICE_BRONZE_ANNUAL'),
        'silver_annual': os.getenv('STRIPE_PRICE_SILVER_ANNUAL'),
        'gold_annual': os.getenv('STRIPE_PRICE_GOLD_ANNUAL'),
        'platinum_annual': os.getenv('STRIPE_PRICE_PLATINUM_ANNUAL'),

        'student_monthly': os.getenv('STRIPE_PRICE_STUDENT_MONTHLY'),
        'student_semester': os.getenv('STRIPE_PRICE_STUDENT_SEMESTER'),
        'student_annual': os.getenv('STRIPE_PRICE_STUDENT_ANNUAL'),

        'call_outreach': os.getenv('STRIPE_PRICE_CALL_OUTREACH'),

        'pause_30': os.getenv('pause_30'),
        'pause_60': os.getenv('pause_60'),
        'pause_90': os.getenv('pause_90'),
    }

    # You might want to add checks to ensure these keys are loaded
    if not all([STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET] + list(STRIPE_PRICES.values())):
         print("Warning: Stripe environment variables not fully loaded!")

    # # Ensure webhook events list remains
    # STRIPE_WEBHOOK_EVENTS = [
    #     'checkout.session.completed', 'customer.subscription.created',
    #     'customer.subscription.updated', 'customer.subscription.deleted',
    #     'invoice.payment_succeeded', 'invoice.payment_failed'
    # ]

    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')





    # DeepSeek API Key
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

    # AWS DynamoDB Configuration
    AWS_REGION = os.getenv('AWS_REGION')
    DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')

    # Endpoints & token caps (constants, not from env)
    OPENAI_BASE_URL     = "https://api.deepseek.com"
    CLAUDE_MAX_TOKENS   = 1024
    BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
    PROMPT_DIR          = os.path.join(BASE_DIR, '..', 'data', 'email_prompt_bank', 'prompt_bank_v1')
    PROMPT_DIR_V2      = os.path.join(BASE_DIR, '..', 'data', 'email_prompt_bank', 'prompt_bank_v2')
    PROMPT_TEMPLATE_VERSION = 'v1'
    PROMPT_TEMPLATE_VERSION_V2 = 'v2'
    PREDEFINED_TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'data', 'email_predefine_template')
    PREDEFINED_TEMPLATE_VERSION = 'v1'

    # Sandbox environment configuration
    SANDBOX_ALLOWED_ROLES = os.getenv('SANDBOX_ALLOWED_ROLES').split(',')
    SANDBOX_DOMAINS = os.getenv('SANDBOX_DOMAINS').split(',')

    # Constants and derived paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Finance report constants (defined here per request)
    FIN_TEMP_FOLDER_NAME = 'temp'
    FIN_UPLOAD_FOLDER_NAME = 'uploads'
    FIN_DATA_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..' , 'data', 'finance_report_gen'))
    FIN_TEMP_DIR = os.path.join(FIN_DATA_ROOT, FIN_TEMP_FOLDER_NAME)
    FIN_UPLOAD_DIR = os.path.join(FIN_DATA_ROOT, FIN_UPLOAD_FOLDER_NAME)

    FIN_PER_FILE_MAX_MB =  10   # CSV/XLS/XLSX per-file cap
    FIN_MAX_ZIP_SIZE_MB = 200  # ZIP file cap

    # Upload format and size constants
    ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "zip"}
    MAX_FILE_SIZE_BYTES = FIN_PER_FILE_MAX_MB * 1024 * 1024

    # File persistence settings for finance_report_gen
    FINANCE_FILE_STORAGE_PATH = os.path.join(FIN_DATA_ROOT, "uploads")
    FINANCE_FILE_RETENTION_DAYS = 90
    FINANCE_STAGES = ['uploaded', 'mapped', 'normalized', 'kpi_calculated', 'llm_generation', 'processed', 'final']

    # Apollo configuration
    APOLLO_ORG_TABLE_NAME = os.getenv('APOLLO_ORG_TABLE_NAME')
    APOLLO_PER_TABLE_NAME = os.getenv('APOLLO_PER_TABLE_NAME')

    #


class DevelopmentConfig(Config):
    """Development config"""
    DEBUG = True


class ProductionConfig(Config):
    """Production config"""
    DEBUG = False


# Use development config by default
config = DevelopmentConfig