from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .utils import slugify


@dataclass(frozen=True)
class StoredObject:
    uri: str
    path: Path | None = None


class StorageProvider(ABC):
    @abstractmethod
    def save_raw(
        self,
        workspace_id: str,
        project_id: str,
        source_hash: str,
        filename: str,
        data: bytes,
    ) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def save_extracted_text(
        self,
        workspace_id: str,
        project_id: str,
        source_hash: str,
        text: str,
    ) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def write_wiki_page(
        self,
        workspace_id: str,
        project_id: str,
        page_key: str,
        content: str,
    ) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def read_wiki_page(self, workspace_id: str, project_id: str, page_key: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_wiki_pages(self, workspace_id: str, project_id: str) -> dict[str, str]:
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def project_root(self, workspace_id: str, project_id: str) -> Path:
        return self.root / slugify(workspace_id, "workspace") / slugify(project_id, "project")

    def save_raw(
        self,
        workspace_id: str,
        project_id: str,
        source_hash: str,
        filename: str,
        data: bytes,
    ) -> StoredObject:
        safe_name = slugify(filename.rsplit(".", 1)[0], "source")
        suffix = ""
        if "." in filename:
            suffix = "." + filename.rsplit(".", 1)[1].lower()
        path = self.project_root(workspace_id, project_id) / "raw" / f"{safe_name}-{source_hash[:10]}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredObject(uri=str(path), path=path)

    def save_extracted_text(
        self,
        workspace_id: str,
        project_id: str,
        source_hash: str,
        text: str,
    ) -> StoredObject:
        path = self.project_root(workspace_id, project_id) / "extracted" / f"{source_hash[:16]}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return StoredObject(uri=str(path), path=path)

    def write_wiki_page(
        self,
        workspace_id: str,
        project_id: str,
        page_key: str,
        content: str,
    ) -> StoredObject:
        path = self.project_root(workspace_id, project_id) / "wiki" / f"{page_key}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return StoredObject(uri=str(path), path=path)

    def read_wiki_page(self, workspace_id: str, project_id: str, page_key: str) -> str:
        path = self.project_root(workspace_id, project_id) / "wiki" / f"{page_key}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def list_wiki_pages(self, workspace_id: str, project_id: str) -> dict[str, str]:
        wiki_root = self.project_root(workspace_id, project_id) / "wiki"
        if not wiki_root.exists():
            return {}
        pages: dict[str, str] = {}
        for path in sorted(wiki_root.glob("*.md")):
            pages[path.stem] = path.read_text(encoding="utf-8")
        return pages


class FeishuDocsStorageProvider(LocalStorageProvider):
    """Feishu-first storage shape with local cache.

    The MVP keeps a local cache for validation and mirrors the provider boundary that
    a production Feishu deployment uses to write wiki pages into Feishu Docs/Wiki.
    This lets the platform adapter and engine stay stable while the actual Feishu
    document-write implementation is completed with tenant credentials.
    """

    def __init__(self, root: Path, docs_space_token: str = ""):
        super().__init__(root)
        self.docs_space_token = docs_space_token
