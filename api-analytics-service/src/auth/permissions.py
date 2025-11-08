"""Permission and role definitions for RBAC."""

from enum import Enum
from typing import Set


class Permission(str, Enum):
    """API permissions."""

    # Read permissions
    READ_GROUPS = "read:groups"
    READ_PREDICTIONS = "read:predictions"
    READ_ENTITIES = "read:entities"
    READ_ANALYTICS = "read:analytics"
    READ_GRAPH = "read:graph"

    # Write permissions
    WRITE_GROUPS = "write:groups"
    WRITE_PREDICTIONS = "write:predictions"
    WRITE_ENTITIES = "write:entities"

    # Export permissions
    EXPORT_DATA = "export:data"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_ROLES = "admin:roles"
    ADMIN_AUDIT = "admin:audit"


class Role(str, Enum):
    """User roles."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_GROUPS,
        Permission.READ_PREDICTIONS,
        Permission.READ_ENTITIES,
        Permission.READ_ANALYTICS,
        Permission.READ_GRAPH,
    },
    Role.ANALYST: {
        Permission.READ_GROUPS,
        Permission.READ_PREDICTIONS,
        Permission.READ_ENTITIES,
        Permission.READ_ANALYTICS,
        Permission.READ_GRAPH,
        Permission.WRITE_GROUPS,
        Permission.WRITE_PREDICTIONS,
        Permission.WRITE_ENTITIES,
        Permission.EXPORT_DATA,
    },
    Role.ADMIN: {
        Permission.READ_GROUPS,
        Permission.READ_PREDICTIONS,
        Permission.READ_ENTITIES,
        Permission.READ_ANALYTICS,
        Permission.READ_GRAPH,
        Permission.WRITE_GROUPS,
        Permission.WRITE_PREDICTIONS,
        Permission.WRITE_ENTITIES,
        Permission.EXPORT_DATA,
        Permission.ADMIN_USERS,
        Permission.ADMIN_ROLES,
        Permission.ADMIN_AUDIT,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get permissions for a role.

    Args:
        role: User role

    Returns:
        Set of permissions for the role
    """
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if role has permission.

    Args:
        role: User role
        permission: Required permission

    Returns:
        True if role has permission, False otherwise
    """
    return permission in get_role_permissions(role)

