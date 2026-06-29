from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAdminUserRole(permissions.BasePermission):
    """
    Permission class that only allows users with the ADMIN role to access the endpoint.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "ADMIN"
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows Admins to perform any operation, 
    but restricts standard users to editing/deleting only their own objects.
    """

    def has_object_permission(self, request: Request, view: APIView, obj: any) -> bool:
        # Admins can do anything
        if request.user and getattr(request.user, "role", None) == "ADMIN":
            return True

        # Check if the object has an owner attribute
        owner = None
        for attr in ["created_by", "uploaded_by", "user", "owner"]:
            if hasattr(obj, attr):
                owner = getattr(obj, attr)
                break

        # Standard user must be the owner
        return bool(request.user and request.user.is_authenticated and owner == request.user)
