from flask import request, current_app
from models.user_model import User
from werkzeug.security import check_password_hash
import logging


class SandboxAccessDenied(Exception):
    """Custom exception for sandbox access denied"""
    def __init__(self, message, role, username, domain):
        self.message = message
        self.role = role
        self.username = username
        self.domain = domain
        super().__init__(self.message)


class SandboxAuthChecker:
    """Utility class for sandbox environment authentication checks"""

    @staticmethod
    def is_sandbox_environment():
        """Check if current request is from sandbox environment"""
        current_domain = request.host.lower()
        sandbox_domains = current_app.config.get('SANDBOX_DOMAINS', [])
        is_sandbox = any(domain in current_domain for domain in sandbox_domains)

        current_app.logger.info(
            f"Sandbox environment check - Domain: {current_domain}, "
            f"Sandbox domains: {sandbox_domains}, Is sandbox: {is_sandbox}"
        )

        return is_sandbox

    @staticmethod
    def check_sandbox_login_allowed(user):
        """Check if user can login to sandbox environment (after user validation)"""
        current_app.logger.info(
            f"Checking sandbox login access for user: {user.username if user else 'None'}, "
            f"Domain: {request.host}"
        )

        if not SandboxAuthChecker.is_sandbox_environment():
            current_app.logger.info(
                f"Not sandbox environment - allowing login for user: {user.username if user else 'None'}"
            )
            return  # Not sandbox, allow login

        if not user:
            current_app.logger.warning(
                f"No user provided for sandbox login check - Domain: {request.host}"
            )
            return  # No user, let normal login handle this

        # Check role for sandbox access
        allowed_roles = current_app.config.get('SANDBOX_ALLOWED_ROLES', [])

        current_app.logger.info(
            f"Sandbox login check - User: {user.username}, Role: {user.role}, "
            f"Allowed roles: {allowed_roles}, Domain: {request.host}"
        )

        if user.role not in allowed_roles:
            # Log the failed attempt
            current_app.logger.error(
                f"Sandbox login denied - User: {user.username}, Role: {user.role}, "
                f"Domain: {request.host}, Allowed roles: {allowed_roles}"
            )

            raise SandboxAccessDenied(
                message="You are not allowed to login",
                role=user.role,
                username=user.username,
                domain=request.host
            )

        current_app.logger.info(
            f"Sandbox login allowed - User: {user.username}, Role: {user.role}, "
            f"Domain: {request.host}"
        )



    @staticmethod
    def check_sandbox_registration_allowed(role):
        """Check if user can register with given role in sandbox environment"""
        current_app.logger.info(
            f"Checking sandbox registration access for role: {role}, "
            f"Domain: {request.host}"
        )

        if not SandboxAuthChecker.is_sandbox_environment():
            current_app.logger.info(
                f"Not sandbox environment - allowing registration for role: {role}"
            )
            return  # Not sandbox, allow registration

        allowed_roles = current_app.config.get('SANDBOX_ALLOWED_ROLES', [])

        current_app.logger.info(
            f"Sandbox registration check - Role: {role}, "
            f"Allowed roles: {allowed_roles}, Domain: {request.host}"
        )

        if role not in allowed_roles:
            # Log the failed registration attempt
            current_app.logger.error(
                f"Sandbox registration denied - Role: {role}, "
                f"Domain: {request.host}, Allowed roles: {allowed_roles}"
            )

            raise SandboxAccessDenied(
                message="Registration not allowed for your role",
                role=role,
                username="registration_attempt",
                domain=request.host
            )

        current_app.logger.info(
            f"Sandbox registration allowed - Role: {role}, "
            f"Domain: {request.host}"
        )