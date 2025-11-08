"""Role-Based Access Control (RBAC) management."""

from typing import Optional, Dict, Any
from functools import wraps
import logging

from src.auth.permissions import Permission, Role, has_permission
from src.exceptions import AuthorizationError
from src.utils.logging import get_logger, get_user_id

logger = get_logger(__name__)


class UserContext:
    """User context with role and permissions."""

    def __init__(
        self,
        user_id: str,
        role: Role,
        permissions: Optional[set[Permission]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize user context.

        Args:
            user_id: User ID
            role: User role
            permissions: Custom permissions (overrides role defaults)
            metadata: Additional user metadata
        """
        self.user_id = user_id
        self.role = role
        self.permissions = permissions or set()
        self.metadata = metadata or {}

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission.

        Args:
            permission: Required permission

        Returns:
            True if user has permission, False otherwise
        """
        # Check custom permissions first
        if self.permissions and permission in self.permissions:
            return True

        # Check role-based permissions
        return has_permission(self.role, permission)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "metadata": self.metadata,
        }


class RBACManager:
    """Manage role-based access control."""

    def __init__(self):
        """Initialize RBAC manager."""
        self.user_contexts: Dict[str, UserContext] = {}

    def create_user_context(
        self,
        user_id: str,
        role: Role,
        permissions: Optional[set[Permission]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserContext:
        """Create user context.

        Args:
            user_id: User ID
            role: User role
            permissions: Custom permissions
            metadata: Additional metadata

        Returns:
            User context
        """
        context = UserContext(
            user_id=user_id,
            role=role,
            permissions=permissions,
            metadata=metadata,
        )

        self.user_contexts[user_id] = context

        logger.info(
            "User context created",
            extra={
                "extra_fields": {
                    "user_id": user_id,
                    "role": role.value,
                }
            },
        )

        return context

    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context.

        Args:
            user_id: User ID

        Returns:
            User context or None if not found
        """
        return self.user_contexts.get(user_id)

    def check_permission(
        self,
        user_id: str,
        permission: Permission,
    ) -> bool:
        """Check if user has permission.

        Args:
            user_id: User ID
            permission: Required permission

        Returns:
            True if user has permission, False otherwise
        """
        context = self.get_user_context(user_id)

        if not context:
            logger.warning(
                "User context not found for permission check",
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                        "permission": permission.value,
                    }
                },
            )
            return False

        has_perm = context.has_permission(permission)

        if not has_perm:
            logger.warning(
                "Permission denied",
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                        "permission": permission.value,
                        "role": context.role.value,
                    }
                },
            )

        return has_perm

    def require_permission(self, permission: Permission):
        """Decorator to require permission for endpoint.

        Args:
            permission: Required permission

        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user_id = get_user_id()

                if not user_id:
                    raise AuthorizationError(
                        message="User ID not found in context",
                    )

                if not self.check_permission(user_id, permission):
                    raise AuthorizationError(
                        message=f"Permission denied: {permission.value}",
                        details={
                            "required_permission": permission.value,
                            "user_id": user_id,
                        },
                    )

                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def require_role(self, role: Role):
        """Decorator to require role for endpoint.

        Args:
            role: Required role

        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user_id = get_user_id()

                if not user_id:
                    raise AuthorizationError(
                        message="User ID not found in context",
                    )

                context = self.get_user_context(user_id)

                if not context or context.role != role:
                    raise AuthorizationError(
                        message=f"Role required: {role.value}",
                        details={
                            "required_role": role.value,
                            "user_id": user_id,
                        },
                    )

                return await func(*args, **kwargs)

            return wrapper

        return decorator


# Global RBAC manager instance
rbac_manager = RBACManager()

