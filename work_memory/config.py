from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str
    port: int
    public_base_url: str
    storage_provider: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str
    feishu_encrypt_key: str
    feishu_reply_enabled: bool
    feishu_docs_space_token: str


def load_settings() -> Settings:
    data_dir = Path(os.getenv("WORK_MEMORY_DATA_DIR", "data")).expanduser().resolve()
    return Settings(
        data_dir=data_dir,
        host=os.getenv("WORK_MEMORY_HOST", "127.0.0.1"),
        port=int(os.getenv("WORK_MEMORY_PORT", "8765")),
        public_base_url=os.getenv("WORK_MEMORY_PUBLIC_BASE_URL", ""),
        storage_provider=os.getenv("WORK_MEMORY_STORAGE", "local"),
        feishu_app_id=os.getenv("FEISHU_APP_ID", ""),
        feishu_app_secret=os.getenv("FEISHU_APP_SECRET", ""),
        feishu_verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", ""),
        feishu_encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY", ""),
        feishu_reply_enabled=os.getenv("FEISHU_REPLY_ENABLED", "true").lower() == "true",
        feishu_docs_space_token=os.getenv("FEISHU_DOCS_SPACE_TOKEN", ""),
    )
