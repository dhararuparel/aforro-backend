from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model supporting Role-Based Access Control (RBAC).
    
    Roles:
        ADMIN: Has full management permissions over collections, documents, and analytics.
        USER: Standard access to view and interact with authorized documents and chats.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        USER = "USER", "User"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["username"]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN
