from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify(value: str, fallback: str = "default") -> str:
    text = unicodedata.normalize("NFKD", value.strip().lower())
    text = re.sub(r"[^\w\s.-]+", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip(".-")
    return text or fallback


def compact_text(value: str, limit: int = 2000) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？.!?])\s+|\n+", text)
    return [part.strip() for part in parts if part.strip()]


def line_numbered(text: str) -> str:
    return "\n".join(f"{idx + 1}: {line}" for idx, line in enumerate(text.splitlines()))


def money_mentions(text: str) -> list[str]:
    pattern = r"(?:预算|报价|费用|金额|价格|合同|cost|budget)?[^。\n]{0,12}?(?:¥|￥)?\d+(?:\.\d+)?\s*(?:万|万元|元|k|K|w|W|million|m)?"
    hits = re.findall(pattern, text)
    cleaned: list[str] = []
    for hit in hits:
        normalized = re.sub(r"\s+", "", hit)
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned[:20]
