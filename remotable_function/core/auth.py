"""
Authentication and Authorization for Remotable.

Provides authentication providers and authorization mechanisms.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Set, Any
import hashlib
import secrets
import time

logger = logging.getLogger(__name__)


@dataclass
class ClientIdentity:
    """Client identity information."""

    client_id: str
    authenticated: bool = False
    permissions: Set[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()
        if self.metadata is None:
            self.metadata = {}


class AuthProvider(ABC):
    """Base authentication provider interface."""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[ClientIdentity]:
        """
        Authenticate client credentials.

        Args:
            credentials: Authentication credentials (token, username/password, etc.)

        Returns:
            ClientIdentity if authentication succeeds, None otherwise
        """
        pass

    async def authorize(self, identity: ClientIdentity, action: str, resource: str) -> bool:
        """
        Check if client is authorized to perform action on resource.

        Args:
            identity: Client identity
            action: Action to perform (e.g., "tool.execute", "tool.register")
            resource: Resource to access (e.g., "filesystem.read_file")

        Returns:
            True if authorized, False otherwise
        """
        # Default: no authorization checks
        return True


class NoAuthProvider(AuthProvider):
    """No authentication provider (insecure - for development only)."""

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[ClientIdentity]:
        """Accept all connections without authentication."""
        client_id = credentials.get("client_id", "unknown")
        logger.warning(f"NoAuthProvider: Accepting client {client_id} without authentication!")
        return ClientIdentity(client_id=client_id, authenticated=False, permissions={"*"})


class TokenAuthProvider(AuthProvider):
    """Simple token-based authentication."""

    def __init__(self, valid_tokens: Optional[Dict[str, ClientIdentity]] = None, **kwargs):
        """
        Initialize token auth provider.

        Args:
            valid_tokens: Dictionary mapping tokens to ClientIdentity
                         If None, all tokens are rejected
        """
        self.valid_tokens = valid_tokens or {}

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[ClientIdentity]:
        """Authenticate using token."""
        token = credentials.get("token")
        if not token:
            logger.warning("Authentication failed: No token provided")
            return None

        identity = self.valid_tokens.get(token)
        if identity:
            logger.info(f"Token authentication succeeded for {identity.client_id}")
            return identity
        else:
            logger.warning(f"Authentication failed: Invalid token")
            return None

    def add_token(self, token: str, identity: ClientIdentity):
        """Add a valid token."""
        self.valid_tokens[token] = identity

    def remove_token(self, token: str):
        """Remove a token."""
        self.valid_tokens.pop(token, None)

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)


class APIKeyAuthProvider(AuthProvider):
    """API Key authentication with rate limiting."""

    def __init__(self, api_keys: Optional[Dict[str, ClientIdentity]] = None):
        """
        Initialize API key auth provider.

        Args:
            api_keys: Dictionary mapping API keys to ClientIdentity
        """
        self.api_keys = api_keys or {}

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[ClientIdentity]:
        """Authenticate using API key."""
        api_key = credentials.get("api_key")
        if not api_key:
            logger.warning("Authentication failed: No API key provided")
            return None

        identity = self.api_keys.get(api_key)
        if identity:
            logger.info(f"API key authentication succeeded for {identity.client_id}")
            return identity
        else:
            logger.warning("Authentication failed: Invalid API key")
            return None

    def add_api_key(self, api_key: str, identity: ClientIdentity):
        """Add a valid API key."""
        self.api_keys[api_key] = identity

    def remove_api_key(self, api_key: str):
        """Remove an API key."""
        self.api_keys.pop(api_key, None)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"rmt_{secrets.token_urlsafe(32)}"


class PermissionBasedAuthProvider(AuthProvider):
    """Permission-based authorization provider."""

    def __init__(self, auth_provider: AuthProvider):
        """
        Initialize permission-based auth provider.

        Args:
            auth_provider: Underlying authentication provider
        """
        self.auth_provider = auth_provider

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[ClientIdentity]:
        """Delegate to underlying auth provider."""
        return await self.auth_provider.authenticate(credentials)

    async def authorize(self, identity: ClientIdentity, action: str, resource: str) -> bool:
        """Check permissions."""
        if not identity.authenticated:
            return False

        # Wildcard permission grants all access
        if "*" in identity.permissions:
            return True

        # Check action permission (e.g., "tool.execute")
        if action in identity.permissions:
            return True

        # Check resource permission (e.g., "filesystem.read_file")
        if resource in identity.permissions:
            return True

        # Check action wildcard (e.g., "tool.*")
        action_prefix = action.split(".")[0] + ".*"
        if action_prefix in identity.permissions:
            return True

        # Check resource wildcard (e.g., "filesystem.*")
        resource_prefix = resource.split(".")[0] + ".*"
        if resource_prefix in identity.permissions:
            return True

        logger.warning(
            f"Authorization failed: {identity.client_id} "
            f"not permitted to {action} on {resource}"
        )
        return False


# Example usage and factory functions
def create_token_auth(tokens: Optional[Dict[str, str]] = None) -> TokenAuthProvider:
    """
    Create token auth provider with client_id -> token mapping.

    Args:
        tokens: Dictionary mapping client_id to token
                If None, creates empty provider

    Returns:
        TokenAuthProvider instance
    """
    provider = TokenAuthProvider()

    if tokens:
        for client_id, token in tokens.items():
            identity = ClientIdentity(client_id=client_id, authenticated=True, permissions={"*"})
            provider.add_token(token, identity)

    return provider


def create_api_key_auth(
    keys: Optional[Dict[str, str]] = None,
) -> APIKeyAuthProvider:
    """
    Create API key auth provider with client_id -> api_key mapping.

    Args:
        keys: Dictionary mapping client_id to api_key

    Returns:
        APIKeyAuthProvider instance
    """
    provider = APIKeyAuthProvider()

    if keys:
        for client_id, api_key in keys.items():
            identity = ClientIdentity(client_id=client_id, authenticated=True, permissions={"*"})
            provider.add_api_key(api_key, identity)

    return provider
