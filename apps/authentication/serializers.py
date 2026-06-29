from typing import Any
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.authentication.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for returning User profile information."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "date_joined"]
        read_only_fields = ["id", "role", "date_joined"]


class RegisterSerializer(serializers.Serializer):
    """Serializer for validating user registration input."""

    username = serializers.CharField(max_length=150, min_length=4, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    def validate_password(self, value: str) -> str:
        """Validate password strength using Django's configured validators."""
        # Using a dummy user to run validators (some require user instance context)
        validate_password(value)
        return value
