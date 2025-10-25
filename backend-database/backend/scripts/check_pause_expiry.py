#!/usr/bin/env python3
"""
Script to check and restore expired pause subscriptions.
This should be run daily via cron job or similar scheduling mechanism.
"""

import os
import sys
import logging

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Main function to restore expired pause subscriptions"""
    try:
        from app import create_app
        from controllers.subscription_controller import SubscriptionController

        app = create_app()

        with app.app_context():
            print("Checking for expired pause subscriptions...")
            app.logger.info("Starting automatic pause expiry check")

            success = SubscriptionController.check_and_restore_paused_subscriptions(
            )

            if success:
                print(
                    "Completed checking expired pause subscriptions successfully."
                )
                app.logger.info(
                    "Completed automatic pause expiry check successfully")
            else:
                print("Error occurred during pause expiry check.")
                app.logger.error(
                    "Error occurred during automatic pause expiry check")

    except Exception as e:
        print(f"Error running pause expiry check: {str(e)}")
        logging.error(f"Error running pause expiry check: {str(e)}")


if __name__ == '__main__':
    main()
