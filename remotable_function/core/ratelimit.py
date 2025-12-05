"""
Rate limiting for Remotable.

Provides rate limiting mechanisms to prevent abuse and DoS attacks.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_window: int = 100  # Max requests per time window
    window_seconds: int = 60  # Time window in seconds
    burst_size: Optional[int] = None  # Max burst size (default: requests_per_window)

    def __post_init__(self):
        if self.burst_size is None:
            self.burst_size = self.requests_per_window


class RateLimiter(ABC):
    """Base rate limiter interface."""

    @abstractmethod
    async def check_rate_limit(self, key: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit.

        Args:
            key: Unique identifier (e.g., client_id, IP address)

        Returns:
            (allowed, error_message) tuple
            - allowed: True if request is allowed, False if rate limited
            - error_message: Error message if rate limited, None otherwise
        """
        pass

    @abstractmethod
    def reset(self, key: str):
        """Reset rate limit for a key."""
        pass


class SlidingWindowRateLimiter(RateLimiter):
    """
    Sliding window rate limiter.

    Uses a sliding window algorithm to track request timestamps.
    More accurate than fixed window but uses more memory.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize sliding window rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        # Store timestamps for each key
        self._windows: Dict[str, deque] = {}

    async def check_rate_limit(self, key: str) -> Tuple[bool, Optional[str]]:
        """Check rate limit using sliding window."""
        now = time.time()

        # Get or create window for this key
        if key not in self._windows:
            self._windows[key] = deque()

        window = self._windows[key]

        # Remove expired timestamps
        cutoff = now - self.config.window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        # Check if under limit
        if len(window) >= self.config.requests_per_window:
            # Rate limited
            oldest = window[0]
            retry_after = int(oldest + self.config.window_seconds - now) + 1
            error_message = (
                f"Rate limit exceeded. "
                f"Max {self.config.requests_per_window} requests per "
                f"{self.config.window_seconds}s. Retry after {retry_after}s."
            )
            logger.warning(f"Rate limit exceeded for {key}: {len(window)} requests")
            return False, error_message

        # Add current timestamp
        window.append(now)
        return True, None

    def reset(self, key: str):
        """Reset rate limit for a key."""
        if key in self._windows:
            del self._windows[key]
            logger.info(f"Rate limit reset for {key}")


class TokenBucketRateLimiter(RateLimiter):
    """
    Token bucket rate limiter.

    More efficient than sliding window, allows controlled bursts.
    Each key has a bucket that refills at a constant rate.
    """

    @dataclass
    class Bucket:
        """Token bucket state."""

        tokens: float
        last_refill: float

    def __init__(self, config: RateLimitConfig):
        """
        Initialize token bucket rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        # Calculate refill rate (tokens per second)
        self.refill_rate = config.requests_per_window / config.window_seconds
        # Store buckets for each key
        self._buckets: Dict[str, "TokenBucketRateLimiter.Bucket"] = {}

    async def check_rate_limit(self, key: str) -> Tuple[bool, Optional[str]]:
        """Check rate limit using token bucket."""
        now = time.time()

        # Get or create bucket for this key
        if key not in self._buckets:
            self._buckets[key] = self.Bucket(tokens=float(self.config.burst_size), last_refill=now)

        bucket = self._buckets[key]

        # Refill tokens based on time elapsed
        time_elapsed = now - bucket.last_refill
        tokens_to_add = time_elapsed * self.refill_rate
        bucket.tokens = min(self.config.burst_size, bucket.tokens + tokens_to_add)
        bucket.last_refill = now

        # Check if we have tokens available
        if bucket.tokens < 1.0:
            # Rate limited
            tokens_needed = 1.0 - bucket.tokens
            retry_after = int(tokens_needed / self.refill_rate) + 1
            error_message = (
                f"Rate limit exceeded. "
                f"Max {self.config.requests_per_window} requests per "
                f"{self.config.window_seconds}s. Retry after {retry_after}s."
            )
            logger.warning(f"Rate limit exceeded for {key}: {bucket.tokens:.2f} tokens")
            return False, error_message

        # Consume one token
        bucket.tokens -= 1.0
        return True, None

    def reset(self, key: str):
        """Reset rate limit for a key."""
        if key in self._buckets:
            del self._buckets[key]
            logger.info(f"Rate limit reset for {key}")


class CompositeRateLimiter(RateLimiter):
    """
    Composite rate limiter that applies multiple limiters.

    Useful for applying different limits (e.g., per-client and global).
    """

    def __init__(self, limiters: list[RateLimiter]):
        """
        Initialize composite rate limiter.

        Args:
            limiters: List of rate limiters to apply
        """
        self.limiters = limiters

    async def check_rate_limit(self, key: str) -> Tuple[bool, Optional[str]]:
        """Check all rate limiters."""
        for limiter in self.limiters:
            allowed, error = await limiter.check_rate_limit(key)
            if not allowed:
                return False, error
        return True, None

    def reset(self, key: str):
        """Reset all rate limiters for a key."""
        for limiter in self.limiters:
            limiter.reset(key)


# Factory functions
def create_rate_limiter(
    requests_per_minute: int = 100,
    burst_multiplier: float = 1.5,
    algorithm: str = "token_bucket",
) -> RateLimiter:
    """
    Create a rate limiter with sensible defaults.

    Args:
        requests_per_minute: Maximum requests per minute
        burst_multiplier: Burst size as multiplier of rate (1.0 = no burst)
        algorithm: Algorithm to use ("token_bucket" or "sliding_window")

    Returns:
        Configured RateLimiter instance
    """
    config = RateLimitConfig(
        requests_per_window=requests_per_minute,
        window_seconds=60,
        burst_size=int(requests_per_minute * burst_multiplier),
    )

    if algorithm == "sliding_window":
        return SlidingWindowRateLimiter(config)
    elif algorithm == "token_bucket":
        return TokenBucketRateLimiter(config)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
