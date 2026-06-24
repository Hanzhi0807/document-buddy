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
    amount = r"(?:¥|￥)?\d+(?:\.\d+)?\s*(?:万元|万|元|k|K|w|W|million|m)"
    pattern = rf"(?:预算|报价|费用|金额|价格|合同|cost|budget|按|为|约)?[^。\n，,；;]{{0,12}}?{amount}"
    hits = re.findall(pattern, text)
    cleaned: list[str] = []
    seen_amounts: set[str] = set()
    for hit in hits:
        normalized = re.sub(r"\s+", "", hit)
        normalized = normalized.strip("：:，,；;。")
        amount_match = re.search(amount, normalized)
        amount_key = amount_match.group(0) if amount_match else normalized
        if normalized and amount_key not in seen_amounts:
            cleaned.append(normalized)
            seen_amounts.add(amount_key)
    return cleaned[:20]
