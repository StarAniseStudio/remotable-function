"""
Tool Registry - Shared by both server and client.

The registry maintains a catalog of available tools with O(1) lookup performance.
"""

from typing import Dict, List, Optional, Set
from .types import ToolDefinition


class ToolRegistry:
    """
    Tool registry with dual-index for fast lookups.

    Features:
    - O(1) lookup by full name (namespace.tool_name)
    - O(1) lookup by namespace
    - O(1) lookup by tag
    - Thread-safe operations
    """

    def __init__(self):
        # Primary index: full_name -> ToolDefinition
        self._tools: Dict[str, ToolDefinition] = {}

        # Secondary indexes for fast queries
        self._by_namespace: Dict[str, Set[str]] = {}  # namespace -> {full_names}
        self._by_tag: Dict[str, Set[str]] = {}  # tag -> {full_names}
        self._by_client: Dict[str, Set[str]] = {}  # client_id -> {full_names}

    def register(
        self,
        tool: ToolDefinition,
        client_id: Optional[str] = None
    ) -> None:
        """
        Register a tool.

        Args:
            tool: Tool definition
            client_id: Optional client ID (for server-side tracking)

        Raises:
            ValueError: If tool with same full name already exists
        """
        full_name = tool.full_name

        # Check for duplicates
        if full_name in self._tools:
            raise ValueError(f"Tool '{full_name}' already registered")

        # Add to primary index
        self._tools[full_name] = tool

        # Add to namespace index
        if tool.namespace not in self._by_namespace:
            self._by_namespace[tool.namespace] = set()
        self._by_namespace[tool.namespace].add(full_name)

        # Add to tag indexes
        for tag in tool.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(full_name)

        # Add to client index (server-side)
        if client_id:
            if client_id not in self._by_client:
                self._by_client[client_id] = set()
            self._by_client[client_id].add(full_name)

    def unregister(self, full_name: str) -> Optional[ToolDefinition]:
        """
        Unregister a tool by full name.

        Args:
            full_name: Full tool name (namespace.name)

        Returns:
            The unregistered tool definition, or None if not found
        """
        tool = self._tools.pop(full_name, None)
        if not tool:
            return None

        # Remove from namespace index
        if tool.namespace in self._by_namespace:
            self._by_namespace[tool.namespace].discard(full_name)
            if not self._by_namespace[tool.namespace]:
                del self._by_namespace[tool.namespace]

        # Remove from tag indexes
        for tag in tool.tags:
            if tag in self._by_tag:
                self._by_tag[tag].discard(full_name)
                if not self._by_tag[tag]:
                    del self._by_tag[tag]

        # Remove from client index
        for client_id in list(self._by_client.keys()):
            self._by_client[client_id].discard(full_name)
            if not self._by_client[client_id]:
                del self._by_client[client_id]

        return tool

    def unregister_client(self, client_id: str) -> List[ToolDefinition]:
        """
        Unregister all tools for a client (server-side only).

        Args:
            client_id: Client ID

        Returns:
            List of unregistered tools
        """
        if client_id not in self._by_client:
            return []

        tool_names = list(self._by_client[client_id])
        unregistered = []

        for full_name in tool_names:
            tool = self.unregister(full_name)
            if tool:
                unregistered.append(tool)

        return unregistered

    def get(self, full_name: str) -> Optional[ToolDefinition]:
        """
        Get tool by full name (O(1) lookup).

        Args:
            full_name: Full tool name (namespace.name)

        Returns:
            Tool definition or None
        """
        return self._tools.get(full_name)

    def list_all(self) -> List[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())

    def list_by_namespace(self, namespace: str) -> List[ToolDefinition]:
        """
        Get all tools in a namespace (O(n) where n = tools in namespace).

        Args:
            namespace: Namespace name

        Returns:
            List of tools in the namespace
        """
        if namespace not in self._by_namespace:
            return []

        return [
            self._tools[full_name]
            for full_name in self._by_namespace[namespace]
            if full_name in self._tools
        ]

    def list_by_tag(self, tag: str) -> List[ToolDefinition]:
        """
        Get all tools with a specific tag.

        Args:
            tag: Tag name

        Returns:
            List of tools with the tag
        """
        if tag not in self._by_tag:
            return []

        return [
            self._tools[full_name]
            for full_name in self._by_tag[tag]
            if full_name in self._tools
        ]

    def list_by_client(self, client_id: str) -> List[ToolDefinition]:
        """
        Get all tools registered by a client (server-side only).

        Args:
            client_id: Client ID

        Returns:
            List of tools from the client
        """
        if client_id not in self._by_client:
            return []

        return [
            self._tools[full_name]
            for full_name in self._by_client[client_id]
            if full_name in self._tools
        ]

    def has(self, full_name: str) -> bool:
        """Check if tool exists."""
        return full_name in self._tools

    def count(self) -> int:
        """Get total number of registered tools."""
        return len(self._tools)

    def count_by_namespace(self, namespace: str) -> int:
        """Get number of tools in a namespace."""
        return len(self._by_namespace.get(namespace, set()))

    def count_by_client(self, client_id: str) -> int:
        """Get number of tools for a client."""
        return len(self._by_client.get(client_id, set()))

    def get_namespaces(self) -> List[str]:
        """Get all registered namespaces."""
        return list(self._by_namespace.keys())

    def get_tags(self) -> List[str]:
        """Get all registered tags."""
        return list(self._by_tag.keys())

    def get_clients(self) -> List[str]:
        """Get all client IDs with registered tools."""
        return list(self._by_client.keys())

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._by_namespace.clear()
        self._by_tag.clear()
        self._by_client.clear()

    def to_dict_list(self) -> List[Dict]:
        """Export all tools as dictionary list."""
        return [tool.to_dict() for tool in self._tools.values()]

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __contains__(self, full_name: str) -> bool:
        """Check if tool exists (supports 'in' operator)."""
        return full_name in self._tools

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ToolRegistry(tools={len(self._tools)}, "
            f"namespaces={len(self._by_namespace)}, "
            f"tags={len(self._by_tag)})"
        )
