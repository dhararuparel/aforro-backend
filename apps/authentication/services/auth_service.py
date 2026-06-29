import logging
from typing import Any

from django.db import transaction

from apps.authentication.models import User
from apps.common.exceptions import AforroBaseException

logger = logging.getLogger(__name__)


class UserRegistrationError(AforroBaseException):
    """Raised when user registration fails due to business rule validation."""
    status_code = 400
    default_detail = "Registration failed."
    default_code = "registration_failed"


class AuthService:
    """Service layer managing user authentication lifecycle and role assignments."""

    @classmethod
    @transaction.atomic
    def register_user(cls, data: dict[str, Any]) -> User:
        """
        Register a new system user with standard USER role.
        
        Validates username and email uniqueness, then hashes the password.
        """
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if not username or not password or not email:
            raise UserRegistrationError("Username, email, and password are required.")

        # Business validations
        if User.objects.filter(username__iexact=username).exists():
            raise UserRegistrationError("Username is already taken.")

        if User.objects.filter(email__iexact=email).exists():
            raise UserRegistrationError("Email is already registered.")

        try:
            logger.info("Registering new user: %s", username)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=User.Role.USER,  # Default role for self-registration
            )
            return user
        except Exception as exc:
            logger.error("Failed to register user %s: %s", username, str(exc), exc_info=True)
            raise UserRegistrationError("An unexpected error occurred during registration.")
