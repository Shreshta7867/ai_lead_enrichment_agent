from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse


RELEVANT_KEYWORDS = (
    "about",
    "company",
    "team",
    "leadership",
    "contact",
    "pricing",
    "management",
    "founders",
    "careers",
    "customers",
    "solutions",
)


def normalize_domain(domain: str) -> str:
    """Strip common noise and return the host without protocol or path."""
    value = domain.strip().lower().replace("https://", "").replace("http://", "")
    value = value.split("/")[0]
    value = value.split("?")[0]
    value = value.split("#")[0]
    return value.strip("./ ")


def is_internal_url(url: str, domain: str) -> bool:
    """Check whether a URL is on the target company's domain."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if not host:
            return False
        if host.startswith("www."):
            host = host[4:]
        return host == domain.lower() or host.endswith(f".{domain.lower()}")
    except Exception:
        return False


def safe_url_join(base_url: str, href: str) -> str:
    if not href:
        return ""
    return urljoin(base_url, href)


def should_skip_navigation_url(url: str) -> bool:
    if not url:
        return True
    lower = url.lower()
    skip_prefixes = ("mailto:", "tel:", "javascript:", "data:")
    if any(lower.startswith(prefix) for prefix in skip_prefixes):
        return True
    if "facebook.com" in lower or "linkedin.com" in lower or "x.com" in lower or "twitter.com" in lower:
        return True
    if any(lower.endswith(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip", ".css")):
        return True
    return False


def is_relevant_internal_path(path: str) -> bool:
    normalized = path.lower()
    if not normalized or normalized == "/":
        return False
    for keyword in RELEVANT_KEYWORDS:
        if keyword in normalized:
            return True
    return False


def clean_text(raw_text: str) -> str:
    """Normalize text for LLM use by collapsing whitespace and removing obvious noise."""
    if not raw_text:
        return ""
    cleaned = re.sub(r"\s+", " ", raw_text)
    return cleaned.strip()


def deduplicate_text(chunks: list[str], max_length: int = 20000) -> list[str]:
    """Remove duplicate chunks while preserving order."""
    seen: set[str] = set()
    deduped: list[str] = []
    for chunk in chunks:
        normalized = clean_text(chunk)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
        if sum(len(item) for item in deduped) >= max_length:
            break
    return deduped
