"""
Filesystem Tools - Built-in tools for file operations with security.

Uses aiofiles for async file I/O operations.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import aiofiles
    import aiofiles.os

    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    logging.warning(
        "aiofiles not installed. File operations will use synchronous I/O. "
        "Install aiofiles for better async performance: pip install aiofiles"
    )

from ...core.types import ToolContext, ParameterSchema, ParameterType
from ..tool import Tool

logger = logging.getLogger(__name__)


class SecureFileSystemTool(Tool):
    """
    Base class for filesystem tools with security features.

    Provides common path validation logic.
    """

    # Default sensitive paths to block
    DEFAULT_DENY_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "~/.ssh",
        "~/.aws",
        "~/.kube",
        "/proc",
        "/sys",
    ]

    # Default file size limits
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB for reading
    DEFAULT_MAX_WRITE_SIZE = 5 * 1024 * 1024  # 5MB for writing

    def __init__(
        self,
        allowed_roots: Optional[List[str]] = None,
        deny_paths: Optional[List[str]] = None,
        follow_symlinks: bool = False,
        max_file_size: Optional[int] = None,
        max_write_size: Optional[int] = None,
    ):
        """
        Initialize secure filesystem tool.

        Args:
            allowed_roots: List of allowed root directories.
                          - None: allows all paths (default, backward compatible)
                          - ["*"]: explicitly allows all paths
                          - ["/path1", "/path2"]: only allow these specific paths
            deny_paths: List of denied path patterns. Default: sensitive system files
            follow_symlinks: Whether to follow symbolic links (default: False for security)
            max_file_size: Maximum file size to read in bytes (default: 10MB)
            max_write_size: Maximum file size to write in bytes (default: 5MB)
        """
        super().__init__()

        # Check for wildcard
        if allowed_roots and "*" in allowed_roots:
            self.allowed_roots = None  # Wildcard means allow all
            logger.info("Allowed roots set to wildcard (*) - all paths allowed")
        elif allowed_roots:
            self.allowed_roots = [Path(r).resolve() for r in allowed_roots]
        else:
            self.allowed_roots = None

        self.deny_paths = deny_paths if deny_paths is not None else self.DEFAULT_DENY_PATHS
        self.follow_symlinks = follow_symlinks
        self.max_file_size = (
            max_file_size if max_file_size is not None else self.DEFAULT_MAX_FILE_SIZE
        )
        self.max_write_size = (
            max_write_size if max_write_size is not None else self.DEFAULT_MAX_WRITE_SIZE
        )

    def _validate_path(self, path: str) -> Path:
        """
        Validate and resolve path with security checks.

        Args:
            path: Path to validate

        Returns:
            Resolved Path object

        Raises:
            PermissionError: If path violates security policy
        """
        # Expand user home directory
        expanded = os.path.expanduser(path)
        path_obj = Path(expanded)

        # Resolve to absolute path
        try:
            if self.follow_symlinks:
                resolved = path_obj.resolve()
            else:
                # Check if it's a symlink first
                if path_obj.is_symlink():
                    raise PermissionError(f"Symbolic links not allowed: {path}")
                resolved = path_obj.resolve()
        except (OSError, RuntimeError) as e:
            raise PermissionError(f"Cannot resolve path: {e}")

        # Check against deny patterns
        for deny_pattern in self.deny_paths:
            deny_expanded = os.path.expanduser(deny_pattern)
            deny_path = Path(deny_expanded)

            # Check if path matches or is under denied path
            try:
                if resolved == deny_path.resolve() or resolved.is_relative_to(deny_path.resolve()):
                    raise PermissionError(f"Access denied to sensitive path: {path}")
            except (ValueError, OSError):
                # On some systems, is_relative_to may not work across drives
                if str(resolved).startswith(str(deny_path)):
                    raise PermissionError(f"Access denied to sensitive path: {path}")

        # Check against allowed roots if specified
        if self.allowed_roots is not None:
            is_allowed = False
            for allowed_root in self.allowed_roots:
                try:
                    if resolved.is_relative_to(allowed_root):
                        is_allowed = True
                        break
                except (ValueError, OSError):
                    # Fallback for older Python or cross-drive scenarios
                    if str(resolved).startswith(str(allowed_root)):
                        is_allowed = True
                        break

            if not is_allowed:
                raise PermissionError(
                    f"Path outside allowed roots: {path}. "
                    f"Allowed: {[str(r) for r in self.allowed_roots]}"
                )

        logger.debug(f"Path validated: {resolved}")
        return resolved


class ReadFileTool(SecureFileSystemTool):
    """
    Read file contents with path validation.

    Security features:
    - Path traversal protection
    - Allowed roots restriction (supports "*" wildcard)
    - Symlink following control
    - Sensitive file blocking
    """

    name = "read_file"
    description = "Read the contents of a file (with security restrictions)"
    namespace = "filesystem"
    permissions = ["filesystem.read"]
    tags = ["filesystem", "io"]

    parameters = [
        ParameterSchema(
            name="path",
            type=ParameterType.STRING,
            description="Path to the file to read",
            required=True,
        ),
        ParameterSchema(
            name="encoding",
            type=ParameterType.STRING,
            description="File encoding (default: utf-8)",
            required=False,
        ),
    ]

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute read file operation with security validation.

        Args:
            path: File path
            encoding: File encoding (default: utf-8)

        Returns:
            {
                "content": str,
                "size": int,
                "path": str
            }

        Raises:
            PermissionError: If path violates security policy
        """
        path = kwargs["path"]
        encoding = kwargs.get("encoding", "utf-8")

        # Validate path
        validated_path = self._validate_path(path)

        # Check file size before reading
        try:
            file_size = validated_path.stat().st_size
            if file_size > self.max_file_size:
                raise ValueError(
                    f"File too large: {file_size} bytes (max: {self.max_file_size} bytes). "
                    f"Set max_file_size parameter to increase limit."
                )
        except OSError as e:
            raise ValueError(f"Cannot access file: {e}")

        # Read file asynchronously
        try:
            if AIOFILES_AVAILABLE:
                # Use aiofiles for async I/O
                async with aiofiles.open(validated_path, "r", encoding=encoding) as f:
                    content = await f.read()
            else:
                # Fallback to synchronous I/O
                with open(validated_path, "r", encoding=encoding) as f:
                    content = f.read()

            return {"content": content, "size": len(content), "path": str(validated_path)}

        except FileNotFoundError:
            raise ValueError(f"File not found: {validated_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {validated_path}")
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")


class WriteFileTool(SecureFileSystemTool):
    """
    Write contents to a file with security restrictions.

    Security features:
    - Path traversal protection
    - Allowed roots restriction (supports "*" wildcard)
    - Symlink following control
    - Sensitive file blocking
    """

    name = "write_file"
    description = "Write contents to a file (with security restrictions)"
    namespace = "filesystem"
    permissions = ["filesystem.write"]
    tags = ["filesystem", "io"]

    parameters = [
        ParameterSchema(
            name="path",
            type=ParameterType.STRING,
            description="Path to the file to write",
            required=True,
        ),
        ParameterSchema(
            name="content", type=ParameterType.STRING, description="Content to write", required=True
        ),
        ParameterSchema(
            name="encoding",
            type=ParameterType.STRING,
            description="File encoding (default: utf-8)",
            required=False,
        ),
        ParameterSchema(
            name="append",
            type=ParameterType.BOOLEAN,
            description="Append to file instead of overwriting (default: false)",
            required=False,
        ),
    ]

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute write file operation with security validation.

        Args:
            path: File path
            content: Content to write
            encoding: File encoding (default: utf-8)
            append: Append mode (default: False)

        Returns:
            {
                "path": str,
                "size": int,
                "appended": bool
            }

        Raises:
            PermissionError: If path violates security policy
        """
        path = kwargs["path"]
        content = kwargs["content"]
        encoding = kwargs.get("encoding", "utf-8")
        append = kwargs.get("append", False)

        # Validate path
        validated_path = self._validate_path(path)

        # Check content size before writing
        content_size = len(content.encode(encoding))
        if content_size > self.max_write_size:
            raise ValueError(
                f"Content too large: {content_size} bytes (max: {self.max_write_size} bytes). "
                f"Set max_write_size parameter to increase limit."
            )

        # Create parent directory if needed
        parent_dir = validated_path.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        # Write file asynchronously
        mode = "a" if append else "w"
        try:
            if AIOFILES_AVAILABLE:
                # Use aiofiles for async I/O
                async with aiofiles.open(validated_path, mode, encoding=encoding) as f:
                    await f.write(content)
            else:
                # Fallback to synchronous I/O
                with open(validated_path, mode, encoding=encoding) as f:
                    f.write(content)

            return {"path": str(validated_path), "size": len(content), "appended": append}

        except PermissionError:
            raise PermissionError(f"Permission denied: {validated_path}")
        except Exception as e:
            raise Exception(f"Failed to write file: {e}")


class ListDirectoryTool(Tool):
    """List directory contents."""

    name = "list_directory"
    description = "List the contents of a directory"
    namespace = "filesystem"
    permissions = ["filesystem.read"]
    tags = ["filesystem", "directory"]

    parameters = [
        ParameterSchema(
            name="path",
            type=ParameterType.STRING,
            description="Path to the directory to list",
            required=True,
        ),
        ParameterSchema(
            name="recursive",
            type=ParameterType.BOOLEAN,
            description="List recursively (default: false)",
            required=False,
        ),
    ]

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute list directory operation.

        Args:
            path: Directory path
            recursive: List recursively (default: False)

        Returns:
            {
                "path": str,
                "files": List[str],
                "directories": List[str],
                "count": int
            }
        """
        path = kwargs["path"]
        recursive = kwargs.get("recursive", False)

        # Normalize path
        normalized_path = os.path.normpath(path)

        if not os.path.exists(normalized_path):
            raise ValueError(f"Directory not found: {normalized_path}")

        if not os.path.isdir(normalized_path):
            raise ValueError(f"Not a directory: {normalized_path}")

        # List directory asynchronously
        try:
            files = []
            directories = []

            if recursive:
                # For recursive listing, os.walk is still synchronous
                # (aiofiles.os doesn't have a walk equivalent)
                for root, dirs, filenames in os.walk(normalized_path):
                    for dirname in dirs:
                        dir_path = os.path.join(root, dirname)
                        directories.append({"name": dirname, "path": dir_path})
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        if AIOFILES_AVAILABLE:
                            file_stat = await aiofiles.os.stat(file_path)
                            file_size = file_stat.st_size
                        else:
                            file_size = os.path.getsize(file_path)
                        files.append(
                            {
                                "name": filename,
                                "path": file_path,
                                "size": file_size,
                            }
                        )
            else:
                if AIOFILES_AVAILABLE:
                    # Use aiofiles.os for async directory listing
                    items = await aiofiles.os.listdir(normalized_path)
                else:
                    items = os.listdir(normalized_path)

                for item in items:
                    item_path = os.path.join(normalized_path, item)
                    if os.path.isdir(item_path):
                        directories.append({"name": item, "path": item_path})
                    else:
                        if AIOFILES_AVAILABLE:
                            file_stat = await aiofiles.os.stat(item_path)
                            file_size = file_stat.st_size
                        else:
                            file_size = os.path.getsize(item_path)
                        files.append({"name": item, "path": item_path, "size": file_size})

            return {
                "path": normalized_path,
                "files": files,
                "directories": directories,
                "count": len(files) + len(directories),
            }

        except PermissionError:
            raise PermissionError(f"Permission denied: {normalized_path}")
        except Exception as e:
            raise Exception(f"Failed to list directory: {e}")


class DeleteFileTool(Tool):
    """Delete a file or directory."""

    name = "delete"
    description = "Delete a file or directory"
    namespace = "filesystem"
    permissions = ["filesystem.delete"]
    tags = ["filesystem", "delete"]

    parameters = [
        ParameterSchema(
            name="path",
            type=ParameterType.STRING,
            description="Path to the file or directory to delete",
            required=True,
        ),
        ParameterSchema(
            name="recursive",
            type=ParameterType.BOOLEAN,
            description="Delete directory recursively (default: false)",
            required=False,
        ),
    ]

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute delete operation.

        Args:
            path: File or directory path
            recursive: Delete recursively for directories (default: False)

        Returns:
            {
                "path": str,
                "deleted": bool,
                "type": str (file or directory)
            }
        """
        path = kwargs["path"]
        recursive = kwargs.get("recursive", False)

        # Normalize path
        normalized_path = os.path.normpath(path)

        if not os.path.exists(normalized_path):
            raise ValueError(f"Path not found: {normalized_path}")

        # Delete asynchronously
        try:
            if os.path.isdir(normalized_path):
                if recursive:
                    # shutil.rmtree is synchronous, no async alternative in aiofiles
                    import shutil

                    shutil.rmtree(normalized_path)
                    item_type = "directory"
                else:
                    if AIOFILES_AVAILABLE:
                        await aiofiles.os.rmdir(normalized_path)
                    else:
                        os.rmdir(normalized_path)
                    item_type = "directory"
            else:
                if AIOFILES_AVAILABLE:
                    await aiofiles.os.remove(normalized_path)
                else:
                    os.remove(normalized_path)
                item_type = "file"

            return {"path": normalized_path, "deleted": True, "type": item_type}

        except PermissionError:
            raise PermissionError(f"Permission denied: {normalized_path}")
        except OSError as e:
            if "Directory not empty" in str(e):
                raise ValueError(f"Directory not empty (use recursive=true): {normalized_path}")
            raise Exception(f"Failed to delete: {e}")
        except Exception as e:
            raise Exception(f"Failed to delete: {e}")


# Alias for backward compatibility
FileSystemTool = SecureFileSystemTool
