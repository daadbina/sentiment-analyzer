"""JWT token handling for authentication."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging

from src.config import config
from src.exceptions import AuthError
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTHandler:
    """Handle JWT token generation and validation."""

    def __init__(self):
        """Initialize JWT handler with configuration."""
        self.secret_key = config.jwt.secret_key
        self.algorithm = config.jwt.algorithm
        self.expiration_hours = config.jwt.expiration_hours

    def create_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT token.

        Args:
            data: Data to encode in token
            expires_delta: Custom expiration time

        Returns:
            JWT token string

        Raises:
            AuthError: If token creation fails
        """
        try:
            to_encode = data.copy()

            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    hours=self.expiration_hours
                )

            to_encode.update({"exp": expire})

            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm,
            )

            logger.info(
                "JWT token created",
                extra={
                    "extra_fields": {
                        "user_id": data.get("sub"),
                        "expires_at": expire.isoformat(),
                    }
                },
            )

            return encoded_jwt

        except Exception as e:
            logger.error(f"Failed to create JWT token: {str(e)}")
            raise AuthError(
                message="Failed to create authentication token",
                details={"error": str(e)},
            )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            AuthError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            user_id: str = payload.get("sub")
            if user_id is None:
                raise AuthError(
                    message="Invalid token: missing user ID",
                    details={"error": "Missing 'sub' claim"},
                )

            logger.info(
                "JWT token verified",
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                    }
                },
            )

            return payload

        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            raise AuthError(
                message="Invalid or expired token",
                details={"error": str(e)},
            )

    def refresh_token(self, token: str) -> str:
        """Refresh JWT token.

        Args:
            token: Current JWT token

        Returns:
            New JWT token

        Raises:
            AuthError: If token is invalid
        """
        try:
            payload = self.verify_token(token)

            # Remove expiration from payload
            payload.pop("exp", None)

            # Create new token
            new_token = self.create_token(payload)

            logger.info(
                "JWT token refreshed",
                extra={
                    "extra_fields": {
                        "user_id": payload.get("sub"),
                    }
                },
            )

            return new_token

        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            raise AuthError(
                message="Failed to refresh token",
                details={"error": str(e)},
            )

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password

        Raises:
            AuthError: If hashing fails
        """
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Failed to hash password: {str(e)}")
            raise AuthError(
                message="Failed to hash password",
                details={"error": str(e)},
            )

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Failed to verify password: {str(e)}")
            return False

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """Get token expiration time.

        Args:
            token: JWT token

        Returns:
            Expiration datetime or None if invalid

        Raises:
            AuthError: If token is invalid
        """
        try:
            payload = self.verify_token(token)
            exp_timestamp = payload.get("exp")

            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)

            return None

        except AuthError:
            raise

