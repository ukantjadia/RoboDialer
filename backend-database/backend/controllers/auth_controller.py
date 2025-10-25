from models.user_model import User, db
from flask_login import login_user, logout_user
from models.plan_model import Plan
from models.user_subscription_model import UserSubscription
from datetime import datetime, timedelta
from utils.token_utils import generate_token, confirm_token
from utils.email_utils import send_email
from utils.sandbox_auth import SandboxAuthChecker, SandboxAccessDenied
from flask import url_for, render_template, current_app, redirect, request
# from controllers.student_verification_controller import is_student_email, set_user_as_student


class AuthController:
    @staticmethod
    def register(username, email, password, role='user', company='', linkedin_url=''):
        """Register a new user"""
        current_app.logger.info(f"Registration attempt - Username: {username}, Email: {email}, Role: {role}, Domain: {request.host}")

        # Check sandbox registration before creating user
        try:
            SandboxAuthChecker.check_sandbox_registration_allowed(role)
            current_app.logger.info(f"Sandbox registration check passed - Role: {role}, Domain: {request.host}")
        except SandboxAccessDenied as e:
            current_app.logger.error(f"Sandbox registration denied - Username: {username}, Role: {role}, Domain: {request.host}, Message: {e.message}")
            return False, e.message

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            current_app.logger.warning(f"Registration failed - Username already exists: {username}, Domain: {request.host}")
            return False, "Username already exists"

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            current_app.logger.warning(f"Registration failed - Email already registered: {email}, Domain: {request.host}")
            return False, "Email already registered"

        # Validate role
        valid_roles = ['admin', 'developer', 'user', 'company_member', 'student', 'tester']
        if role not in valid_roles:
            current_app.logger.warning(f"Registration failed - Invalid role: {role}, Domain: {request.host}")
            return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"

        try:
            current_app.logger.info(f"Creating new user - Username: {username}, Email: {email}, Role: {role}, Domain: {request.host}")

            # Create new user
            user = User(username=username, email=email, role=role, company=company, linkedin_url=linkedin_url)
            user.set_password(password)

            # Add to database (commit early to get user_id if autoincremented, or ensure user exists for FK)
            # Note: This might need adjustment based on how user_id is generated (if it's UUID, may not need early commit)
            db.session.add(user)
            db.session.flush() # Use flush to make user_id available without committing

            # Assign default 'free' tier in User model (for quick access)
            user.tier = 'free'

            # Fetch the 'Free' plan
            free_plan = Plan.query.filter_by(plan_name='Free').first()
            current_app.logger.info(f"Fetched free plan: {free_plan}")
            if free_plan:
                # Calculate expiration date (30 days from start timestamp)
                tier_start = datetime.utcnow()
                tier_expiration = tier_start + timedelta(days=30)

                # Create a new UserSubscription entry for the user, setting all relevant columns
                user_subscription = UserSubscription(
                    user_id=user.user_id, # Use the newly created user's ID
                    plan_id=free_plan.plan_id,
                    plan_name=free_plan.plan_name, # Set plan_name
                    payment_frequency=free_plan.credit_reset_frequency if free_plan.credit_reset_frequency else 'monthly', # Use credit_reset_frequency from Plan
                    credits_remaining=free_plan.initial_credits if free_plan.initial_credits is not None else 0,
                    tier_start_timestamp=tier_start, # Set the start timestamp
                    plan_expiration_timestamp=tier_expiration, # Set the calculated expiration timestamp
                    username=user.username
                )
                db.session.add(user_subscription)
                current_app.logger.info(f"Created user subscription - User: {username}, Plan: {free_plan.plan_name}")
            else:
                current_app.logger.warning("'Free' plan not found in database. Cannot create initial user subscription.")
                # Decide how to handle this - maybe raise an error or create user without subscription?
                # For now, user is created without subscription, which might cause issues later.

            # Commit both user and subscription (if created) in a single transaction
            db.session.commit()
            current_app.logger.info(f"User '{username}' registered successfully. Sending verification email...")
            AuthController.send_verification_email(user)

            current_app.logger.info(f"Registration successful - Username: {username}, Email: {email}, Role: {role}, Domain: {request.host}")
            return True, "Registration successful"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration failed for user '{username}': {str(e)}, Domain: {request.host}")
            return False, f"Registration failed: {str(e)}"

    @staticmethod
    def login(username, password):
        """Login a user"""
        current_app.logger.info(f"Login attempt - Username: {username}, Domain: {request.host}")

        try:
            # Find user by username
            user = User.query.filter_by(username=username).first()

            if not user:
                current_app.logger.warning(f"Login failed - User not found: {username}, Domain: {request.host}")
                return False, "Invalid username or password"

            current_app.logger.info(f"User found - Username: {username}, Role: {user.role}, Domain: {request.host}")

            # Check if user exists and password is correct
            if user.check_password(password):
                current_app.logger.info(f"Password valid - Username: {username}, Role: {user.role}, Domain: {request.host}")

                # Check sandbox access before creating session
                try:
                    SandboxAuthChecker.check_sandbox_login_allowed(user)
                    current_app.logger.info(f"Sandbox access granted - Username: {username}, Role: {user.role}, Domain: {request.host}")
                except SandboxAccessDenied as e:
                    current_app.logger.error(f"Sandbox login denied - Username: {username}, Role: {user.role}, Domain: {request.host}, Message: {e.message}")
                    return False, e.message

                login_user(user)

                # Update last login timestamp
                user.update_last_login()

                current_app.logger.info(f"Login successful - Username: {username}, Role: {user.role}, Domain: {request.host}")
                return True, "Login successful"
            else:
                current_app.logger.warning(f"Login failed - Invalid password for user: {username}, Domain: {request.host}")
                return False, "Invalid username or password"
        except Exception as e:
            current_app.logger.error(f"Login exception - Username: {username}, Domain: {request.host}, Error: {str(e)}")
            return False, f"Login failed: {str(e)}"

    @staticmethod
    def login_by_email(email, password):
        """Login a user by email"""
        current_app.logger.info(f"Login attempt by email - Email: {email}, Domain: {request.host}")

        try:
            # Find user by email
            user = User.query.filter_by(email=email).first()

            if not user:
                current_app.logger.warning(f"Login failed - User not found by email: {email}, Domain: {request.host}")
                return False, "Invalid email or password"

            current_app.logger.info(f"User found by email - Email: {email}, Username: {user.username}, Role: {user.role}, Domain: {request.host}")

            # Check if password is correct
            if user.check_password(password):
                current_app.logger.info(f"Password valid - Email: {email}, Username: {user.username}, Role: {user.role}, Domain: {request.host}")

                # Check sandbox access before creating session
                try:
                    SandboxAuthChecker.check_sandbox_login_allowed(user)
                    current_app.logger.info(f"Sandbox access granted - Email: {email}, Username: {user.username}, Role: {user.role}, Domain: {request.host}")
                except SandboxAccessDenied as e:
                    current_app.logger.error(f"Sandbox login denied - Email: {email}, Username: {user.username}, Role: {user.role}, Domain: {request.host}, Message: {e.message}")
                    return False, e.message

                login_user(user)

                # Update last login timestamp
                user.update_last_login()

                current_app.logger.info(f"Login successful - Email: {email}, Username: {user.username}, Role: {user.role}, Domain: {request.host}")
                return True, "Login successful"
            else:
                current_app.logger.warning(f"Login failed - Invalid password for email: {email}, Domain: {request.host}")
                return False, "Invalid email or password"
        except Exception as e:
            current_app.logger.error(f"Login exception - Email: {email}, Domain: {request.host}, Error: {str(e)}")
            return False, f"Login failed: {str(e)}"

    @staticmethod
    def logout():
        """Logout current user"""
        try:
            logout_user()
            return True, "Logout successful"
        except Exception as e:
            return False, f"Logout failed: {str(e)}"

    @staticmethod
    def send_verification_email(user):
        try:
            token = generate_token(user.email, salt='email-verify')
            user.email_verification_sent_at = datetime.utcnow()
            db.session.commit()
            # Use frontend URL for verification
            if "sandbox-api.capraeleadseekers.site" in request.host:
                verify_url = f"https://sandboxdev.saasquatchleads.com/verify-email/{token}"
            elif "data.capraeleadseekers.site" in request.host:
                verify_url = f"https://app.saasquatchleads.com/verify-email/{token}"
            else:
                verify_url = f"https://app.saasquatchleads.com/verify-email/{token}"
            html = render_template('emails/verify_email.html', verify_url=verify_url, user=user, now=datetime.utcnow)
            send_email('Verify Your Email', [user.email], html)
            current_app.logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email to {user.email}: {str(e)}")

    @staticmethod
    def verify_email(token):
        try:
            email = confirm_token(token, salt='email-verify')
            if not email:
                current_app.logger.warning("Email verification failed: Invalid or expired token.")
                return False, "Invalid or expired token."
            user = User.query.filter_by(email=email).first()
            if not user:
                current_app.logger.warning(f"Email verification failed: No user found for email {email}.")
                return False, "Invalid user."
            if user.is_email_verified:
                current_app.logger.info(f"Email already verified for user {user.email}.")
                return True, "Email already verified."
            if user.email_verification_sent_at and datetime.utcnow() > user.email_verification_sent_at + timedelta(hours=1):
                current_app.logger.warning(f"Verification link expired for user {user.email}.")
                return False, "Verification link expired."
            user.is_email_verified = True
            db.session.commit()
            current_app.logger.info(f"Email verified for user {user.email}.")

            # Student domain check and role update (added, do not change existing logic)
            # if is_student_email(user.email):
            #     set_user_as_student(user)

            return True, "Success, Email verified!"
        except Exception as e:
            current_app.logger.error(f"Error during email verification: {str(e)}")
            return False, f"Verification failed: {str(e)}"

    @staticmethod
    def send_password_reset_email(user):
        try:
            token = generate_token(user.email, salt='password-reset')
            user.password_reset_sent_at = datetime.utcnow()
            db.session.commit()
            # Use frontend URL for reset
            if "sandbox-api.capraeleadseekers.site" in request.host:
                reset_url = f"https://sandboxdev.saasquatchleads.com/reset-password/{token}"
            elif "data.capraeleadseekers.site" in request.host:
                reset_url = f"https://app.saasquatchleads.com/reset-password/{token}"
            else:
                reset_url = f"https://app.saasquatchleads.com/reset-password/{token}"
            html = render_template('emails/reset_password.html', reset_url=reset_url, user=user, now=datetime.utcnow)
            send_email('Reset Your Password', [user.email], html)
            current_app.logger.info(f"Password reset email sent to {user.email} at {datetime.utcnow()}, username: {user.username}")
        except Exception as e:
            current_app.logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")

    @staticmethod
    def reset_password(token, new_password):
        try:
            email = confirm_token(token, salt='password-reset')
            if not email:
                current_app.logger.warning("Password reset failed: Invalid or expired token.")
                return False, "Invalid or expired token."
            user = User.query.filter_by(email=email).first()
            if not user:
                current_app.logger.warning(f"Password reset failed: No user found for email {email}.")
                return False, "User not found."
            if user.password_reset_sent_at and datetime.utcnow() > user.password_reset_sent_at + timedelta(hours=1):
                current_app.logger.warning(f"Password reset link expired for user {user.email}.")
                return False, "Reset link expired."
            user.set_password(new_password)
            db.session.commit()
            current_app.logger.info(f"Password reset successful for user {user.email}.")
            return True, "Password reset successful."
        except Exception as e:
            current_app.logger.error(f"Error during password reset: {str(e)}")
            return False, f"Password reset failed: {str(e)}"