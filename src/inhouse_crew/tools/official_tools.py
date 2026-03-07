from __future__ import annotations

from pathlib import Path

from crewai.tools import BaseTool

from .file_ops import FileReadTool, FileWriteTool, WorkspaceWriteTool


class ToolRegistryError(ValueError):
    """Raised when a requested tool cannot be resolved."""


def build_tool_registry(project_root: Path, workspace_root: Path) -> dict[str, BaseTool]:
    return {
        "file_read": FileReadTool(root=project_root),
        "file_write": FileWriteTool(root=project_root),
        "workspace_write": WorkspaceWriteTool(workspace_root=workspace_root),
    }
