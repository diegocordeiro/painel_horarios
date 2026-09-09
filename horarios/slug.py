"""Geração de slugs no mesmo formato do gerador original (underscore, sem acentos).

Porta fiel de functions.createURL / safeFileStem do scripts/fet-csv-to-mdx.mjs.
"""
from __future__ import annotations

import hashlib
import re

# Transliteration manual (NFD sem diacríticos via unicode normalize).
def url_slug(value: str) -> str:
    """Converte um texto em slug com underscores (a forma usada fora de acentos)."""
    normalized = (
        str(value)
        .replace("ç", "c")
        .replace("Ç", "c")
    )
    # Remove acentos usando Unicode NFD.
    import unicodedata

    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"^_+|_+$", "", normalized)
    return normalized or "item"


def safe_file_stem(value: str) -> str:
    """Mantém o stem curto e acrescenta um hash quando for longo (como no JS)."""
    normalized = url_slug(value)
    if len(normalized) <= 80:
        return normalized or "item"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"{normalized[:60]}_{digest}"


def versao_slug(value: str) -> str:
    """Slug simples para versões (ex.: '2026.2.v4')."""
    return re.sub(r"[^a-z0-9._-]+", "_", str(value).strip().lower())
