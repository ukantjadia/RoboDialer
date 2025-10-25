import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, BaseLoader
from datetime import datetime
from config.config import config

logger = logging.getLogger(__name__)

class EmailService:
    """Service for handling email sending with embedded HTML template."""

    # Embedded full HTML template for missed call emails
    MISSED_CALL_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8" />
        <title>Sorry We Missed You</title>
        <style>
            body {
                background-color: #020817;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
                    Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                margin: 0;
                padding: 0;
                color: #ffffff;
            }
            .email-wrapper {
                max-width: 600px;
                margin: 40px auto;
                background-color: #0f172a;
                border-radius: 12px;
                overflow: hidden;
                padding: 40px 32px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
            }
            .logo { display: block; margin: 0 auto 32px; width: 280px; }
            .header { font-size: 22px; font-weight: 600; color: #ffffff; margin-bottom: 16px; text-align: center; }
            .paragraph { font-size: 16px; color: #e2e8f0; line-height: 1.6; margin: 12px 0; text-align: center; }
            .button-wrapper { text-align: center; margin: 30px 0; }
            .btn { background-color: #7bc3a3; color: #0f172a; padding: 14px 32px; font-size: 16px; font-weight: 600; border-radius: 8px; text-decoration: none; display: inline-block; }
            .btn:hover { background-color: #64a88b; }
            .footer { font-size: 13px; color: #94a3b8; text-align: center; margin-top: 40px; }
        </style>
    </head>

    <body>
        <div class="email-wrapper">
            <img src="https://app.saasquatchleads.com/images/logo_horizontal.png" alt="SaaSquatch Leads" class="logo" />
            <div class="header">Hello, {{ name }}!</div>
            <p class="paragraph">We tried reaching you earlier today but were unable to connect. We’d love the opportunity to discuss about our services and explore how we can add value to your company's goals.</p>
            <p class="paragraph">If you’re still interested, please feel free to schedule a convenient time for a quick conversation using the Schedule a Call button below.</p>
            <div class="button-wrapper">
                <a href="{{ schedule_url }}" class="btn">Schedule a Call</a>
            </div>
            <p class="paragraph">We look forward to hearing from you!</p>
            <div class="footer">
                Best regards,<br />The SaaSquatch Leads Team<br /><br />
                &copy; {{ now().year }} SaaSquatch Leads
            </div>
        </div>
    </body>

    </html>
    """

    def __init__(self):
        self.MAIL_SERVER = config.MAIL_SERVER
        self.MAIL_PORT = config.MAIL_PORT
        self.MAIL_USERNAME = config.MAIL_USERNAME
        self.MAIL_PASSWORD = config.MAIL_PASSWORD
        self.MAIL_DEFAULT_SENDER = config.MAIL_DEFAULT_SENDER
        self.env = Environment(loader=BaseLoader())
        self.env.globals['now'] = datetime.utcnow

    def send_email(self, to_email: str, subject: str, html_content: str):
        if not all([self.MAIL_SERVER, self.MAIL_PORT, self.MAIL_USERNAME, self.MAIL_PASSWORD, self.MAIL_DEFAULT_SENDER]):
            logger.error("Email service is not configured.")
            raise ConnectionError("Email service is not configured.")

        msg = MIMEMultipart()
        msg['From'] = self.MAIL_DEFAULT_SENDER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        try:
            with smtplib.SMTP(self.MAIL_SERVER, self.MAIL_PORT) as server:
                server.starttls()
                server.login(self.MAIL_USERNAME, self.MAIL_PASSWORD)
                server.send_message(msg)
                logger.info(f"Email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            raise

    def send_missed_call_email(self, lead_name: str, lead_email: str):
        try:
            template = self.env.from_string(self.MISSED_CALL_TEMPLATE)
            html_content = template.render(
                name=lead_name,
                schedule_url="https://calendar.app.google/uNprcEzBUTtwvx8q7"
            )
            self.send_email(
                to_email=lead_email,
                subject="Sorry we missed you - SaaSquatch Leads",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Could not send missed call email to {lead_email}: {e}")
            raise
