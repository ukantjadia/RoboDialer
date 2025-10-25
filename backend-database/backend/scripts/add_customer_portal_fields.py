
"""
Database migration script to add customer portal related fields to user_subscriptions table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.lead_model import db
from sqlalchemy import text

def add_customer_portal_fields():
    """Add customer portal related fields to user_subscriptions table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if fields already exist
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'user_subscriptions' 
                AND COLUMN_NAME IN (
                    'stripe_customer_id', 
                    'billing_address_line1', 
                    'billing_address_line2',
                    'billing_address_city',
                    'billing_address_state',
                    'billing_address_postal_code',
                    'billing_address_country',
                    'phone_number',
                    'payment_method_id',
                    'payment_method_type',
                    'payment_method_last4',
                    'payment_method_brand',
                    'invoice_settings_default_payment_method',
                    'preferred_locales',
                    'currency',
                    'subscription_status',
                    'current_period_start',
                    'current_period_end',
                    'cancel_at_period_end',
                    'invoice_email_enabled',
                    'customer_portal_last_updated'
                )
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            # Add missing columns
            if 'stripe_customer_id' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN stripe_customer_id VARCHAR(255) NULL"))
                print("Added stripe_customer_id column")
            
            if 'billing_address_line1' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN billing_address_line1 VARCHAR(255) NULL"))
                print("Added billing_address_line1 column")
            
            if 'billing_address_line2' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN billing_address_line2 VARCHAR(255) NULL"))
                print("Added billing_address_line2 column")
            
            if 'billing_address_city' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN billing_address_city VARCHAR(255) NULL"))
                print("Added billing_address_city column")
            
            if 'billing_address_state' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN billing_address_state VARCHAR(255) NULL"))
                print("Added billing_address_state column")
            
            if 'billing_address_postal_code' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN billing_address_postal_code VARCHAR(255) NULL"))
                print("Added billing_address_postal_code column")
            
            if 'billing_address_country' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN billing_address_country VARCHAR(255) NULL"))
                print("Added billing_address_country column")
            
            if 'phone_number' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN phone_number VARCHAR(255) NULL"))
                print("Added phone_number column")
            
            if 'payment_method_id' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN payment_method_id VARCHAR(255) NULL"))
                print("Added payment_method_id column")
            
            if 'payment_method_type' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN payment_method_type VARCHAR(100) NULL"))
                print("Added payment_method_type column")
            
            if 'payment_method_last4' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN payment_method_last4 VARCHAR(4) NULL"))
                print("Added payment_method_last4 column")
            
            if 'payment_method_brand' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN payment_method_brand VARCHAR(50) NULL"))
                print("Added payment_method_brand column")
            
            if 'invoice_settings_default_payment_method' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN invoice_settings_default_payment_method VARCHAR(255) NULL"))
                print("Added invoice_settings_default_payment_method column")
            
            if 'preferred_locales' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN preferred_locales VARCHAR(255) NULL"))
                print("Added preferred_locales column")
            
            if 'currency' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN currency VARCHAR(3) NULL"))
                print("Added currency column")
            
            if 'subscription_status' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN subscription_status VARCHAR(50) NULL"))
                print("Added subscription_status column")
            
            if 'current_period_start' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN current_period_start TIMESTAMP NULL"))
                print("Added current_period_start column")
            
            if 'current_period_end' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN current_period_end TIMESTAMP NULL"))
                print("Added current_period_end column")
            
            if 'cancel_at_period_end' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN cancel_at_period_end BOOLEAN DEFAULT FALSE"))
                print("Added cancel_at_period_end column")
            
            if 'invoice_email_enabled' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN invoice_email_enabled BOOLEAN DEFAULT TRUE"))
                print("Added invoice_email_enabled column")
            
            if 'customer_portal_last_updated' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN customer_portal_last_updated TIMESTAMP NULL"))
                print("Added customer_portal_last_updated column")
            
            db.session.commit()
            print("Successfully added customer portal fields to user_subscriptions table")
            
        except Exception as e:
            print(f"Error adding customer portal fields: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_customer_portal_fields()
