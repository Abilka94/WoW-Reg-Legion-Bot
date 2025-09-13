"""
Simple, fast validators for email, nickname, and password.
Design goals:
- Avoid catastrophic backtracking (ReDoS) and be fast on long strings.
- Keep ASCII-only policy for email/nickname; reject IDNs and unicode.
- Password: current tests require only rejecting Cyrillic characters.
"""
from __future__ import annotations

import re
from typing import Optional


ASCII_RE = re.compile(r"^[\x00-\x7F]+$")
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF\u0500-\u052F\u2DE0-\u2DFF\uA640-\uA69F]")


def _is_ascii(s: str) -> bool:
    return bool(ASCII_RE.fullmatch(s))


def validate_email(email: Optional[str]) -> bool:
    if not isinstance(email, str):
        return False
    email = email.strip()
    if not email or ' ' in email:
        return False
    if not _is_ascii(email):
        return False
    if len(email) > 254:
        return False
    if email.count('@') != 1:
        return False

    local, domain = email.split('@')
    if not (1 <= len(local) <= 64 and 1 <= len(domain) <= 255):
        return False

    # Local part rules
    if local.startswith('.') or local.endswith('.') or '..' in local:
        return False
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local):
        return False

    # Domain rules
    if '..' in domain or domain.startswith('.') or domain.endswith('.'):
        return False
    labels = domain.split('.')
    if len(labels) < 2:
        return False
    for label in labels:
        if not (1 <= len(label) <= 63):
            return False
        if label.startswith('-') or label.endswith('-'):
            return False
        if not re.fullmatch(r"[A-Za-z0-9-]+", label):
            return False

    return True


def validate_nickname(nick: Optional[str]) -> bool:
    if not isinstance(nick, str):
        return False
    nick = nick.strip()
    if not nick:
        return False
    if not _is_ascii(nick):
        return False
    # Length limits to avoid DoS on huge strings; enforce 3..16
    if not (3 <= len(nick) <= 16):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9]+", nick))


def validate_password(pwd: Optional[str]) -> bool:
    if not isinstance(pwd, str):
        return False
    # Reject empty; accept any non-Cyrillic password otherwise.
    if pwd == "":
        return False
    return CYRILLIC_RE.search(pwd) is None
