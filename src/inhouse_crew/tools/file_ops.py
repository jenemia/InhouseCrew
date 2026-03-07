from __future__ import annotations

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import Field


class FileReadTool(BaseTool):
    name: str = "file_read"
    description: str = "Read a UTF-8 text file from the project workspace using a relative path."
    root: Path = Field(default_factory=Path.cwd, exclude=True)

    def _run(self, path: str) -> str:
        target = self._resolve_path(path)
        return target.read_text(encoding="utf-8")

    def _resolve_path(self, raw_path: str) -> Path:
        target = (self.root / raw_path).resolve()
        # 상대 경로가 프로젝트 루트를 벗어나면 relative_to에서 예외가 나도록 둔다.
        target.relative_to(self.root.resolve())
        return target


class FileWriteTool(BaseTool):
    name: str = "file_write"
    description: str = "Write UTF-8 text content to a file in the project workspace."
    root: Path = Field(default_factory=Path.cwd, exclude=True)

    def _run(self, path: str, content: str) -> str:
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def _resolve_path(self, raw_path: str) -> Path:
        target = (self.root / raw_path).resolve()
        # 쓰기 도구도 같은 경로 검증을 적용해 임의 경로 쓰기를 막는다.
        target.relative_to(self.root.resolve())
        return target


class WorkspaceWriteTool(BaseTool):
    name: str = "workspace_write"
    description: str = "Write Markdown artifacts into the configured workspace directory."
    workspace_root: Path = Field(default_factory=Path.cwd, exclude=True)

    def _run(self, relative_path: str, content: str) -> str:
        target = (self.workspace_root / relative_path).resolve()
        # workspace 전용 쓰기는 실행 산출물만 다루도록 루트를 별도로 제한한다.
        target.relative_to(self.workspace_root.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)
