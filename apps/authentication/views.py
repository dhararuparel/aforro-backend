import logging
from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.serializers import RegisterSerializer, UserSerializer
from apps.authentication.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    POST /api/auth/register
    
    Registers a new system user. Self-registered users are assigned the standard USER role.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Register a new user",
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "validation_error",
                        "message": "Invalid registration data.",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = AuthService.register_user(serializer.validated_data)
        response_serializer = UserSerializer(user)
        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "user": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout
    
    Logs out the user by blacklisting their refresh token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Logout user (blacklist refresh token)",
        request=None,
        responses={
            200: {"description": "Successfully logged out."},
            400: {"description": "Invalid or missing refresh token."},
        },
    )
    def post(self, request: Request) -> Response:
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "code": "missing_token",
                            "message": "Refresh token is required.",
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info("User %s successfully logged out.", request.user.username)
            return Response(
                {"success": True, "message": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.warning("Logout failed for user %s: %s", request.user.username, str(exc))
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "invalid_token",
                        "message": "Invalid or expired refresh token.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserProfileView(APIView):
    """
    GET /api/auth/me
    
    Returns the authenticated user's profile details.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Get current user profile",
        responses={200: UserSerializer},
    )
    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user)
        return Response(
            {
                "success": True,
                "user": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
