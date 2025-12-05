"""
Simplified configuration for Remotable.

Provides clean configuration objects with sensible defaults.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ConnectionState(Enum):
    """Connection states for better state management."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class SecurityConfig:
    """Security configuration."""

    require_auth: bool = False
    auth_token: Optional[str] = None
    api_keys: Dict[str, str] = field(default_factory=dict)
    enable_rate_limit: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    max_message_size: int = 10 * 1024 * 1024  # 10MB
    allowed_commands: Optional[list] = None
    blocked_paths: list = field(default_factory=lambda: ["/etc", "/sys", "/proc"])


@dataclass
class PerformanceConfig:
    """Performance configuration."""

    enable_cache: bool = True
    cache_ttl: int = 300
    cache_max_size: int = 1000
    enable_compression: bool = True
    compression_threshold: int = 1024
    connection_pool_size: int = 10
    batch_size: int = 50
    batch_timeout: float = 0.1


@dataclass
class NetworkConfig:
    """Network configuration."""

    host: str = "localhost"
    port: int = 8000
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ping_interval: int = 30
    ping_timeout: int = 10

    # Reconnection settings (exponential backoff + jitter)
    reconnect_interval: int = 5  # Deprecated: use reconnect_base_delay
    reconnect_max_attempts: int = 10
    reconnect_base_delay: float = 1.0  # Base delay for exponential backoff (seconds)
    reconnect_max_delay: float = 60.0  # Maximum delay between retries (seconds)
    reconnect_multiplier: float = 2.0  # Exponential backoff multiplier
    reconnect_jitter: float = 0.3  # Jitter factor (0.0 - 1.0)


@dataclass
class GatewayConfig:
    """
    Gateway configuration with sensible defaults.

    Example:
        # Default config (works for most cases)
        gateway = Gateway(GatewayConfig())

        # Custom config
        config = GatewayConfig(
            network=NetworkConfig(port=9000),
            security=SecurityConfig(require_auth=True)
        )
        gateway = Gateway(config)
    """

    network: NetworkConfig = field(default_factory=NetworkConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    log_level: LogLevel = LogLevel.INFO
    name: str = "remotable-gateway"

    @classmethod
    def development(cls) -> "GatewayConfig":
        """Development configuration (insecure, verbose)."""
        return cls(
            security=SecurityConfig(require_auth=False),
            performance=PerformanceConfig(enable_cache=False),
            log_level=LogLevel.DEBUG,
        )

    @classmethod
    def production(cls) -> "GatewayConfig":
        """Production configuration (secure, optimized)."""
        return cls(
            network=NetworkConfig(host="0.0.0.0"),
            security=SecurityConfig(require_auth=True, enable_rate_limit=True),
            performance=PerformanceConfig(enable_cache=True, enable_compression=True),
            log_level=LogLevel.WARNING,
        )


@dataclass
class ClientConfig:
    """
    Client configuration with sensible defaults.

    Example:
        # Default config
        client = Client(ClientConfig())

        # Custom config
        config = ClientConfig(
            server_url="wss://api.example.com",
            security=SecurityConfig(auth_token="secret")
        )
        client = Client(config)
    """

    server_url: str = "ws://localhost:8000"
    client_id: Optional[str] = None
    security: SecurityConfig = field(default_factory=SecurityConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    log_level: LogLevel = LogLevel.INFO
    auto_reconnect: bool = True

    @classmethod
    def from_url(cls, url: str, **kwargs) -> "ClientConfig":
        """Create config from URL."""
        config = cls(server_url=url)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# Presets for common scenarios
PRESETS = {
    "local": GatewayConfig(),
    "development": GatewayConfig.development(),
    "production": GatewayConfig.production(),
    "testing": GatewayConfig(
        network=NetworkConfig(port=0),  # Random port
        security=SecurityConfig(require_auth=False),
        log_level=LogLevel.ERROR,
    ),
}


def load_config(preset: str = "local") -> GatewayConfig:
    """
    Load configuration preset.

    Args:
        preset: Preset name (local, development, production, testing)

    Returns:
        Configuration object
    """
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}. Choose from: {list(PRESETS.keys())}")
    return PRESETS[preset]
