"""Normalize counterparty identifiers so they group across artifacts."""

from __future__ import annotations

import re

_OPTIONAL_RE = re.compile(r"^Optional\((.*)\)$")
_WHATSAPP_PREFIX_RE = re.compile(r"(?i)^whatsapp:")
_NON_DIGIT_RE = re.compile(r"\D")

# JID domains that wrap a phone number rather than an email host.
_PHONE_JID_DOMAINS = {"s.whatsapp.net", "g.us", "c.us"}


def _unwrap(raw: str) -> str:
    s = raw.strip()
    match = _OPTIONAL_RE.match(s)
    if match:
        s = match.group(1).strip().strip('"').strip("'")
    s = _WHATSAPP_PREFIX_RE.sub("", s).strip()
    return s


def normalize_identifier(raw: str | None) -> tuple[str, str] | None:
    """Return ``(kind, key)`` for an identifier, or ``None`` if unusable.

    ``kind`` is ``"phone"``, ``"email"``, or ``"handle"``. The key is the
    comparable form: phones collapse to their last 10 digits (so a number with
    and without its country code match), emails lowercase, and anything else
    becomes a lowercased opaque handle.
    """
    if raw is None:
        return None
    s = _unwrap(str(raw))
    if not s:
        return None

    local, sep, domain = s.partition("@")
    if sep and domain:
        domain_lower = domain.lower()
        looks_like_phone_jid = domain_lower in _PHONE_JID_DOMAINS or local.lstrip("+").isdigit()
        if not looks_like_phone_jid and "." in domain_lower:
            return ("email", s.lower())
        s = local  # phone JID — keep only the number part

    digits = _NON_DIGIT_RE.sub("", s)
    if len(digits) >= 7:
        key = digits[-10:] if len(digits) >= 10 else digits
        return ("phone", key)

    cleaned = s.strip().lower()
    if cleaned:
        return ("handle", cleaned)
    return None


def identity_key(raw: str | None) -> str | None:
    """``normalize_identifier`` flattened to a single ``kind:key`` string."""
    norm = normalize_identifier(raw)
    if norm is None:
        return None
    return f"{norm[0]}:{norm[1]}"
