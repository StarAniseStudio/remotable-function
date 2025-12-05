"""
Optimized serialization for Remotable.

Provides fast and efficient serialization/deserialization.
"""

import json
import logging
import pickle
import struct
from typing import Any, Dict, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import msgpack
import base64
from io import BytesIO

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Serialization formats."""

    JSON = "json"
    MSGPACK = "msgpack"
    PICKLE = "pickle"
    CUSTOM = "custom"


@dataclass
class SerializationConfig:
    """Serialization configuration."""

    default_format: SerializationFormat = SerializationFormat.JSON
    enable_compression: bool = True
    compression_threshold: int = 1024  # Compress if larger than this
    max_message_size: int = 10 * 1024 * 1024  # 10MB
    use_message_pack: bool = True  # Use msgpack for binary data
    cache_serialized: bool = True  # Cache frequently serialized objects


class FastSerializer:
    """
    Fast serializer with multiple format support.

    Automatically selects the best format based on data.
    """

    def __init__(self, config: Optional[SerializationConfig] = None):
        """
        Initialize fast serializer.

        Args:
            config: Serialization configuration
        """
        self.config = config or SerializationConfig()

        # Serialization cache
        self._cache: Dict[int, bytes] = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Format handlers
        self._serializers = {
            SerializationFormat.JSON: self._serialize_json,
            SerializationFormat.MSGPACK: self._serialize_msgpack,
            SerializationFormat.PICKLE: self._serialize_pickle,
            SerializationFormat.CUSTOM: self._serialize_custom,
        }

        self._deserializers = {
            SerializationFormat.JSON: self._deserialize_json,
            SerializationFormat.MSGPACK: self._deserialize_msgpack,
            SerializationFormat.PICKLE: self._deserialize_pickle,
            SerializationFormat.CUSTOM: self._deserialize_custom,
        }

    def serialize(self, obj: Any, format: Optional[SerializationFormat] = None) -> bytes:
        """
        Serialize object to bytes.

        Args:
            obj: Object to serialize
            format: Serialization format (auto-detect if None)

        Returns:
            Serialized bytes
        """
        # Check cache
        if self.config.cache_serialized:
            obj_hash = self._hash_object(obj)
            if obj_hash in self._cache:
                self._cache_hits += 1
                return self._cache[obj_hash]
            self._cache_misses += 1

        # Auto-detect format if not specified
        if format is None:
            format = self._detect_format(obj)

        # Serialize
        serializer = self._serializers.get(format, self._serialize_json)
        data = serializer(obj)

        # Check size
        if len(data) > self.config.max_message_size:
            raise ValueError(f"Serialized data exceeds max size: {len(data)} bytes")

        # Compress if needed
        if self.config.enable_compression and len(data) > self.config.compression_threshold:
            import zlib

            data = b"C" + zlib.compress(data, level=6)  # Prefix with 'C' for compressed

        # Cache result
        if self.config.cache_serialized and obj_hash:
            self._cache[obj_hash] = data
            # Limit cache size
            if len(self._cache) > 1000:
                self._cache.pop(next(iter(self._cache)))

        return data

    def deserialize(self, data: bytes, format: Optional[SerializationFormat] = None) -> Any:
        """
        Deserialize bytes to object.

        Args:
            data: Serialized bytes
            format: Serialization format (auto-detect if None)

        Returns:
            Deserialized object
        """
        # Decompress if needed
        if data.startswith(b"C"):
            import zlib

            data = zlib.decompress(data[1:])

        # Auto-detect format if not specified
        if format is None:
            format = self._detect_format_from_bytes(data)

        # Deserialize
        deserializer = self._deserializers.get(format, self._deserialize_json)
        return deserializer(data)

    def _detect_format(self, obj: Any) -> SerializationFormat:
        """Auto-detect best format for object."""
        # Use msgpack for binary-friendly data
        if self.config.use_message_pack and self._is_msgpack_compatible(obj):
            return SerializationFormat.MSGPACK

        # Use JSON for simple data
        if self._is_json_compatible(obj):
            return SerializationFormat.JSON

        # Fall back to pickle for complex objects
        return SerializationFormat.PICKLE

    def _detect_format_from_bytes(self, data: bytes) -> SerializationFormat:
        """Detect format from serialized bytes."""
        # Check for JSON
        if data.startswith(b"{") or data.startswith(b"["):
            return SerializationFormat.JSON

        # Check for msgpack
        if len(data) > 0 and data[0] in (0x90, 0x91, 0x92, 0x93, 0xDC, 0xDD, 0xDE):
            return SerializationFormat.MSGPACK

        # Default to pickle
        return SerializationFormat.PICKLE

    def _is_json_compatible(self, obj: Any) -> bool:
        """Check if object is JSON-compatible."""
        try:
            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False

    def _is_msgpack_compatible(self, obj: Any) -> bool:
        """Check if object is msgpack-compatible."""
        # msgpack handles most Python types
        return isinstance(obj, (dict, list, tuple, str, int, float, bool, type(None), bytes))

    def _hash_object(self, obj: Any) -> Optional[int]:
        """Generate hash for object (for caching)."""
        try:
            if isinstance(obj, (dict, list)):
                return hash(json.dumps(obj, sort_keys=True))
            return hash(obj)
        except:
            return None

    def _serialize_json(self, obj: Any) -> bytes:
        """Serialize using JSON."""
        return json.dumps(obj, separators=(",", ":")).encode("utf-8")

    def _deserialize_json(self, data: bytes) -> Any:
        """Deserialize JSON."""
        return json.loads(data.decode("utf-8"))

    def _serialize_msgpack(self, obj: Any) -> bytes:
        """Serialize using msgpack."""
        return msgpack.packb(obj, use_bin_type=True)

    def _deserialize_msgpack(self, data: bytes) -> Any:
        """Deserialize msgpack."""
        return msgpack.unpackb(data, raw=False)

    def _serialize_pickle(self, obj: Any) -> bytes:
        """Serialize using pickle."""
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize_pickle(self, data: bytes) -> Any:
        """Deserialize pickle."""
        return pickle.loads(data)

    def _serialize_custom(self, obj: Any) -> bytes:
        """Custom serialization (override in subclass)."""
        return self._serialize_json(obj)

    def _deserialize_custom(self, data: bytes) -> Any:
        """Custom deserialization (override in subclass)."""
        return self._deserialize_json(data)

    def get_stats(self) -> Dict[str, Any]:
        """Get serialization statistics."""
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_size": len(self._cache),
            "hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0
                else 0.0
            ),
        }


class StreamSerializer:
    """
    Streaming serializer for large data.

    Serializes/deserializes in chunks to reduce memory usage.
    """

    def __init__(self, chunk_size: int = 8192):
        """
        Initialize stream serializer.

        Args:
            chunk_size: Chunk size in bytes
        """
        self.chunk_size = chunk_size

    def serialize_to_stream(
        self,
        obj: Any,
        stream: BytesIO,
        format: SerializationFormat = SerializationFormat.MSGPACK,
    ) -> None:
        """
        Serialize object to stream.

        Args:
            obj: Object to serialize
            stream: Output stream
            format: Serialization format
        """
        if format == SerializationFormat.MSGPACK:
            packer = msgpack.Packer(use_bin_type=True)
            packed = packer.pack(obj)
            stream.write(packed)
        elif format == SerializationFormat.JSON:
            json_str = json.dumps(obj)
            stream.write(json_str.encode("utf-8"))
        else:
            pickle.dump(obj, stream, protocol=pickle.HIGHEST_PROTOCOL)

    def deserialize_from_stream(
        self,
        stream: BytesIO,
        format: SerializationFormat = SerializationFormat.MSGPACK,
    ) -> Any:
        """
        Deserialize object from stream.

        Args:
            stream: Input stream
            format: Serialization format

        Returns:
            Deserialized object
        """
        if format == SerializationFormat.MSGPACK:
            unpacker = msgpack.Unpacker(stream, raw=False)
            return next(unpacker)
        elif format == SerializationFormat.JSON:
            data = stream.read().decode("utf-8")
            return json.loads(data)
        else:
            return pickle.load(stream)


class BinaryProtocol:
    """
    Binary protocol for efficient network communication.

    Uses fixed headers and optimized encoding.
    """

    # Header format: [version(1), format(1), flags(1), length(4)]
    HEADER_FORMAT = "!BBBi"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    VERSION = 1
    FLAG_COMPRESSED = 0x01
    FLAG_ENCRYPTED = 0x02

    def encode_message(
        self,
        data: Any,
        format: SerializationFormat = SerializationFormat.MSGPACK,
        compress: bool = True,
    ) -> bytes:
        """
        Encode message with binary protocol.

        Args:
            data: Data to encode
            format: Serialization format
            compress: Whether to compress

        Returns:
            Encoded message
        """
        # Serialize data
        serializer = FastSerializer()
        payload = serializer.serialize(data, format)

        # Compress if requested
        flags = 0
        if compress and len(payload) > 100:
            import zlib

            compressed = zlib.compress(payload, level=6)
            if len(compressed) < len(payload):
                payload = compressed
                flags |= self.FLAG_COMPRESSED

        # Create header
        header = struct.pack(
            self.HEADER_FORMAT,
            self.VERSION,
            format.value.encode("utf-8")[0],  # First char of format
            flags,
            len(payload),
        )

        return header + payload

    def decode_message(self, data: bytes) -> Tuple[Any, SerializationFormat]:
        """
        Decode message with binary protocol.

        Args:
            data: Encoded message

        Returns:
            Tuple of (decoded data, format used)
        """
        if len(data) < self.HEADER_SIZE:
            raise ValueError("Invalid message: too short")

        # Parse header
        header = data[: self.HEADER_SIZE]
        version, format_byte, flags, length = struct.unpack(self.HEADER_FORMAT, header)

        if version != self.VERSION:
            raise ValueError(f"Unsupported protocol version: {version}")

        # Extract payload
        payload = data[self.HEADER_SIZE : self.HEADER_SIZE + length]

        # Decompress if needed
        if flags & self.FLAG_COMPRESSED:
            import zlib

            payload = zlib.decompress(payload)

        # Detect format
        format_map = {
            ord("j"): SerializationFormat.JSON,
            ord("m"): SerializationFormat.MSGPACK,
            ord("p"): SerializationFormat.PICKLE,
        }
        format = format_map.get(format_byte, SerializationFormat.JSON)

        # Deserialize
        serializer = FastSerializer()
        result = serializer.deserialize(payload, format)

        return result, format


class LazySerializer:
    """
    Lazy serializer that defers serialization until needed.

    Useful for objects that may not need to be serialized.
    """

    def __init__(self, obj: Any, serializer: Optional[FastSerializer] = None):
        """
        Initialize lazy serializer.

        Args:
            obj: Object to serialize
            serializer: Serializer instance
        """
        self.obj = obj
        self.serializer = serializer or FastSerializer()
        self._serialized: Optional[bytes] = None

    def get_bytes(self) -> bytes:
        """Get serialized bytes (lazy)."""
        if self._serialized is None:
            self._serialized = self.serializer.serialize(self.obj)
        return self._serialized

    def get_object(self) -> Any:
        """Get original object."""
        return self.obj

    def __len__(self) -> int:
        """Get serialized size."""
        return len(self.get_bytes())


# Global serializer instance
default_serializer = FastSerializer()


def serialize(obj: Any, format: Optional[SerializationFormat] = None) -> bytes:
    """
    Serialize object using default serializer.

    Args:
        obj: Object to serialize
        format: Serialization format

    Returns:
        Serialized bytes
    """
    return default_serializer.serialize(obj, format)


def deserialize(data: bytes, format: Optional[SerializationFormat] = None) -> Any:
    """
    Deserialize bytes using default serializer.

    Args:
        data: Serialized bytes
        format: Serialization format

    Returns:
        Deserialized object
    """
    return default_serializer.deserialize(data, format)
