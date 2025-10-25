
#!/usr/bin/env python3
"""
Script to check and restore expired pause subscriptions.
This should be run daily via cron job or similar scheduling mechanism.
"""

import os
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from controllers.subscription_controller import SubscriptionController

def main():
    """Main function to restore expired pause subscriptions"""
    app = create_app()
    
    with app.app_context():
        print("Checking for expired pause subscriptions...")
        SubscriptionController.check_and_restore_paused_subscriptions()
        print("Completed checking expired pause subscriptions.")

if __name__ == '__main__':
    main()
