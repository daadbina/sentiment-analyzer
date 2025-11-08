"""Tests for authentication and authorization."""

import pytest
from datetime import datetime, timedelta
from src.auth import JWTHandler, RBACManager, UserContext, Permission, Role


class TestJWTHandler:
    """Test JWT handler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = JWTHandler(
            secret_key="test-secret-key",
            algorithm="HS256",
            expiration_hours=24,
        )

    def test_create_token(self):
        """Test token creation."""
        token = self.handler.create_token(
            user_id="user123",
            username="testuser",
            roles=["VIEWER"],
        )

        assert token is not None
        assert isinstance(token, str)

    def test_verify_token(self):
        """Test token verification."""
        token = self.handler.create_token(
            user_id="user123",
            username="testuser",
            roles=["VIEWER"],
        )

        payload = self.handler.verify_token(token)

        assert payload["user_id"] == "user123"
        assert payload["username"] == "testuser"
        assert "VIEWER" in payload["roles"]

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        with pytest.raises(Exception):
            self.handler.verify_token("invalid-token")

    def test_refresh_token(self):
        """Test token refresh."""
        token = self.handler.create_token(
            user_id="user123",
            username="testuser",
            roles=["VIEWER"],
        )

        new_token = self.handler.refresh_token(token)

        assert new_token is not None
        assert new_token != token

        payload = self.handler.verify_token(new_token)
        assert payload["user_id"] == "user123"

    def test_hash_password(self):
        """Test password hashing."""
        password = "test-password-123"
        hashed = self.handler.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password(self):
        """Test password verification."""
        password = "test-password-123"
        hashed = self.handler.hash_password(password)

        assert self.handler.verify_password(password, hashed)
        assert not self.handler.verify_password("wrong-password", hashed)


class TestRBACManager:
    """Test RBAC manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rbac = RBACManager()

    def test_user_context_creation(self):
        """Test user context creation."""
        context = UserContext(
            user_id="user123",
            username="testuser",
            roles=[Role.VIEWER],
        )

        assert context.user_id == "user123"
        assert context.username == "testuser"
        assert Role.VIEWER in context.roles

    def test_has_permission_viewer(self):
        """Test permission check for VIEWER role."""
        context = UserContext(
            user_id="user123",
            username="testuser",
            roles=[Role.VIEWER],
        )

        assert context.has_permission(Permission.READ_GROUPS)
        assert context.has_permission(Permission.READ_PREDICTIONS)
        assert not context.has_permission(Permission.CREATE_GROUPS)

    def test_has_permission_analyst(self):
        """Test permission check for ANALYST role."""
        context = UserContext(
            user_id="user123",
            username="testuser",
            roles=[Role.ANALYST],
        )

        assert context.has_permission(Permission.READ_GROUPS)
        assert context.has_permission(Permission.CREATE_GROUPS)
        assert not context.has_permission(Permission.DELETE_GROUPS)

    def test_has_permission_admin(self):
        """Test permission check for ADMIN role."""
        context = UserContext(
            user_id="user123",
            username="testuser",
            roles=[Role.ADMIN],
        )

        assert context.has_permission(Permission.READ_GROUPS)
        assert context.has_permission(Permission.CREATE_GROUPS)
        assert context.has_permission(Permission.DELETE_GROUPS)

    def test_has_role(self):
        """Test role check."""
        context = UserContext(
            user_id="user123",
            username="testuser",
            roles=[Role.VIEWER, Role.ANALYST],
        )

        assert context.has_role(Role.VIEWER)
        assert context.has_role(Role.ANALYST)
        assert not context.has_role(Role.ADMIN)

    def test_multiple_roles(self):
        """Test multiple roles."""
        context = UserContext(
            user_id="user123",
            username="testuser",
            roles=[Role.VIEWER, Role.ANALYST],
        )

        # Should have permissions from both roles
        assert context.has_permission(Permission.READ_GROUPS)
        assert context.has_permission(Permission.CREATE_GROUPS)

