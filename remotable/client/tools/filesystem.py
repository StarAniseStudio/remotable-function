"""
Filesystem Tools - Built-in tools for file operations.
"""

import os
import logging
from typing import Dict, Any, List
from pathlib import Path

from ...core.types import ToolContext, ParameterSchema, ParameterType
from ..tool import Tool

logger = logging.getLogger(__name__)


class ReadFileTool(Tool):
    """Read file contents."""

    name = "read_file"
    description = "Read the contents of a file"
    namespace = "filesystem"
    permissions = ["filesystem.read"]
    tags = ["filesystem", "io"]

    parameters = [
        ParameterSchema(
            name="path",
            type=ParameterType.STRING,
            description="Path to the file to read",
            required=True
        ),
        ParameterSchema(
            name="encoding",
            type=ParameterType.STRING,
            description="File encoding (default: utf-8)",
            required=False
        ),
    ]

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute read file operation.

        Args:
            path: File path
            encoding: File encoding (default: utf-8)

        Returns:
            {
                "content": str,
                "size": int,
                "path": str
            }
        """
        path = kwargs["path"]
        encoding = kwargs.get("encoding", "utf-8")

        # Normalize and validate path
        normalized_path = os.path.normpath(path)

        # Read file
        try:
            with open(normalized_path, "r", encoding=encoding) as f:
                content = f.read()

            return {
                "content": content,
                "size": len(content),
                "path": normalized_path
            }

        except FileNotFoundError:
            raise ValueError(f"File not found: {normalized_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {normalized_path}")
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")


class WriteFileTool(Tool):
    """Write contents to a file."""

    name = "write_file"
    description = "Write contents to a file"
    namespace = "filesystem"
    permissions = ["filesystem.write"]
    tags = ["filesystem", "io"]

    parameters = [
        ParameterSchema(
            name="path",
            type=ParameterType.STRING,
            description="Path to the file to write",
            required=True
        ),
        ParameterSchema(
            name="content",
            type=ParameterType.STRING,
            description="Content to write",
            required=True
        ),
        ParameterSchema(
            name="encoding",
            type=ParameterType.STRING,
            description="File encoding (default: utf-8)",
            required=False
        ),
        ParameterSchema(
            name="append",
            type=ParameterType.BOOLEAN,
            description="Append to file instead of overwriting (default: false)",
            required=False
        ),
    ]

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute write file operation.

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
        """
        path = kwargs["path"]
        content = kwargs["content"]
        encoding = kwargs.get("encoding", "utf-8")
        append = kwargs.get("append", False)

        # Normalize path
        normalized_path = os.path.normpath(path)

        # Create parent directory if needed
        parent_dir = os.path.dirname(normalized_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        # Write file
        mode = "a" if append else "w"
        try:
            with open(normalized_path, mode, encoding=encoding) as f:
                f.write(content)

            return {
                "path": normalized_path,
                "size": len(content),
                "appended": append
            }

        except PermissionError:
            raise PermissionError(f"Permission denied: {normalized_path}")
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
            required=True
        ),
        ParameterSchema(
            name="recursive",
            type=ParameterType.BOOLEAN,
            description="List recursively (default: false)",
            required=False
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

        # List directory
        try:
            files = []
            directories = []

            if recursive:
                for root, dirs, filenames in os.walk(normalized_path):
                    for dirname in dirs:
                        dir_path = os.path.join(root, dirname)
                        directories.append({
                            "name": dirname,
                            "path": dir_path
                        })
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        files.append({
                            "name": filename,
                            "path": file_path,
                            "size": os.path.getsize(file_path)
                        })
            else:
                for item in os.listdir(normalized_path):
                    item_path = os.path.join(normalized_path, item)
                    if os.path.isdir(item_path):
                        directories.append({
                            "name": item,
                            "path": item_path
                        })
                    else:
                        files.append({
                            "name": item,
                            "path": item_path,
                            "size": os.path.getsize(item_path)
                        })

            return {
                "path": normalized_path,
                "files": files,
                "directories": directories,
                "count": len(files) + len(directories)
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
            required=True
        ),
        ParameterSchema(
            name="recursive",
            type=ParameterType.BOOLEAN,
            description="Delete directory recursively (default: false)",
            required=False
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

        # Delete
        try:
            if os.path.isdir(normalized_path):
                if recursive:
                    import shutil
                    shutil.rmtree(normalized_path)
                    item_type = "directory"
                else:
                    os.rmdir(normalized_path)
                    item_type = "directory"
            else:
                os.remove(normalized_path)
                item_type = "file"

            return {
                "path": normalized_path,
                "deleted": True,
                "type": item_type
            }

        except PermissionError:
            raise PermissionError(f"Permission denied: {normalized_path}")
        except OSError as e:
            if "Directory not empty" in str(e):
                raise ValueError(f"Directory not empty (use recursive=true): {normalized_path}")
            raise Exception(f"Failed to delete: {e}")
        except Exception as e:
            raise Exception(f"Failed to delete: {e}")
