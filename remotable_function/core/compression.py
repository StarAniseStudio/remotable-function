"""
Message Compression for Remotable

Automatic compression/decompression for large messages to reduce network overhead.

Features:
- Automatic compression for messages > threshold
- zlib compression with configurable level
- Transparent compression/decompression
- Compression statistics
"""

import zlib
import json
import logging
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class CompressionStats:
    """Compression statistics"""

    compressed_count: int = 0
    decompressed_count: int = 0
    bytes_before: int = 0
    bytes_after: int = 0

    @property
    def compression_ratio(self) -> float:
        """Calculate average compression ratio"""
        if self.bytes_before == 0:
            return 1.0
        return self.bytes_after / self.bytes_before

    @property
    def space_saved(self) -> int:
        """Calculate bytes saved"""
        return self.bytes_before - self.bytes_after


class MessageCompressor:
    """
    Message compressor with automatic compression for large messages.

    Uses zlib compression for messages exceeding a size threshold.

    Example:
        compressor = MessageCompressor(threshold=1024, level=6)

        # Compress message
        data, compressed = compressor.compress({"large": "data" * 1000})
        # Returns (compressed_bytes, True) if compressed
        # Returns (original_json_bytes, False) if not compressed

        # Decompress message
        result = compressor.decompress(data, compressed=compressed)
        # Returns original dict

        # Check stats
        stats = compressor.get_stats()
        print(f"Compression ratio: {stats.compression_ratio:.2%}")
    """

    def __init__(
        self,
        threshold: int = 1024,
        level: int = 6,
        enable_compression: bool = True,
    ):
        """
        Initialize message compressor.

        Args:
            threshold: Minimum message size in bytes to trigger compression
            level: zlib compression level (0-9, higher = better compression but slower)
            enable_compression: Enable/disable compression globally
        """
        self.threshold = threshold
        self.level = level
        self.enable_compression = enable_compression
        self._stats = CompressionStats()

        logger.info(
            f"MessageCompressor initialized (threshold={threshold}, level={level}, "
            f"enabled={enable_compression})"
        )

    def compress(self, data: Any) -> Tuple[bytes, bool]:
        """
        Compress data if it exceeds threshold.

        Args:
            data: Data to compress (will be JSON serialized)

        Returns:
            Tuple of (data_bytes, was_compressed)
            - data_bytes: Compressed or original JSON bytes
            - was_compressed: True if compressed, False otherwise
        """
        # Serialize to JSON
        try:
            json_bytes = json.dumps(data).encode("utf-8")
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize data for compression: {e}")
            raise

        original_size = len(json_bytes)

        # Check if compression is needed
        if not self.enable_compression or original_size < self.threshold:
            logger.debug(f"Skip compression (size={original_size}, threshold={self.threshold})")
            return json_bytes, False

        # Compress
        try:
            compressed_bytes = zlib.compress(json_bytes, level=self.level)
            compressed_size = len(compressed_bytes)

            # Only use compression if it actually saves space
            if compressed_size < original_size:
                self._stats.compressed_count += 1
                self._stats.bytes_before += original_size
                self._stats.bytes_after += compressed_size

                saved = original_size - compressed_size
                ratio = compressed_size / original_size
                logger.debug(
                    f"Compressed message: {original_size} -> {compressed_size} bytes "
                    f"({ratio:.1%}, saved {saved} bytes)"
                )

                return compressed_bytes, True
            else:
                # Compression didn't help, use original
                logger.debug(f"Compression ineffective: {original_size} -> {compressed_size} bytes")
                return json_bytes, False

        except zlib.error as e:
            logger.error(f"Compression failed: {e}")
            return json_bytes, False

    def decompress(self, data: bytes, compressed: bool = False) -> Any:
        """
        Decompress data if it was compressed.

        Args:
            data: Data bytes (compressed or JSON)
            compressed: Whether data is compressed

        Returns:
            Deserialized data

        Raises:
            ValueError: If decompression or deserialization fails
        """
        try:
            if compressed:
                # Decompress
                json_bytes = zlib.decompress(data)
                self._stats.decompressed_count += 1
                logger.debug(f"Decompressed message: {len(data)} -> {len(json_bytes)} bytes")
            else:
                json_bytes = data

            # Deserialize JSON
            result = json.loads(json_bytes.decode("utf-8"))
            return result

        except zlib.error as e:
            logger.error(f"Decompression failed: {e}")
            raise ValueError(f"Failed to decompress data: {e}")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Deserialization failed: {e}")
            raise ValueError(f"Failed to deserialize data: {e}")

    def get_stats(self) -> CompressionStats:
        """Get compression statistics"""
        return self._stats

    def reset_stats(self) -> None:
        """Reset statistics"""
        self._stats = CompressionStats()
        logger.debug("Compression stats reset")

    async def compress_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress message for WebSocket transmission.

        Args:
            message: Message dictionary to compress

        Returns:
            Dictionary with compressed data if compression was beneficial,
            otherwise returns original message
        """
        # Try to compress the message
        data_bytes, was_compressed = self.compress(message)

        if was_compressed:
            # Return compressed message with metadata
            import base64

            return {
                "compressed": True,
                "data": base64.b64encode(data_bytes).decode("utf-8"),
                "original_size": len(json.dumps(message).encode("utf-8")),
                "compressed_size": len(data_bytes),
            }
        else:
            # Return original message
            return message

    async def decompress_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decompress message received from WebSocket.

        Args:
            message: Message dictionary that may be compressed

        Returns:
            Original decompressed message
        """
        if isinstance(message, dict) and message.get("compressed"):
            # Decompress the message
            import base64

            data_bytes = base64.b64decode(message["data"])
            return self.decompress(data_bytes, compressed=True)
        else:
            # Return as-is if not compressed
            return message


def create_compressed_message(
    message: Dict[str, Any], compressor: Optional[MessageCompressor] = None
) -> Dict[str, Any]:
    """
    Create compressed message with metadata.

    Wraps the original message with compression metadata.

    Args:
        message: Original message
        compressor: MessageCompressor instance (creates default if None)

    Returns:
        Message dict with compression metadata:
        {
            "data": <bytes as base64 string>,
            "compressed": <bool>,
            "original_size": <int>  # Only if compressed
        }

    Example:
        msg = {"method": "call_tool", "params": {"large": "data" * 1000}}
        compressed_msg = create_compressed_message(msg)
        # Returns: {"data": "eJy...", "compressed": true, "original_size": 5000}
    """
    import base64

    if compressor is None:
        compressor = MessageCompressor()

    data_bytes, compressed = compressor.compress(message)

    # Encode as base64 for JSON compatibility
    data_b64 = base64.b64encode(data_bytes).decode("ascii")

    result = {
        "data": data_b64,
        "compressed": compressed,
    }

    if compressed:
        # Include original size for monitoring
        json_str = json.dumps(message)
        result["original_size"] = len(json_str.encode("utf-8"))

    return result


def extract_compressed_message(
    compressed_msg: Dict[str, Any], compressor: Optional[MessageCompressor] = None
) -> Dict[str, Any]:
    """
    Extract message from compressed format.

    Args:
        compressed_msg: Compressed message dict
        compressor: MessageCompressor instance (creates default if None)

    Returns:
        Original message dict

    Raises:
        ValueError: If decompression fails
    """
    import base64

    if compressor is None:
        compressor = MessageCompressor()

    try:
        data_b64 = compressed_msg["data"]
        compressed = compressed_msg.get("compressed", False)

        # Decode base64
        data_bytes = base64.b64decode(data_b64)

        # Decompress and deserialize
        message = compressor.decompress(data_bytes, compressed=compressed)

        return message

    except KeyError as e:
        raise ValueError(f"Invalid compressed message format: missing {e}")
    except Exception as e:
        raise ValueError(f"Failed to extract compressed message: {e}")
