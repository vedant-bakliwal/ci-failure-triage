"""Turn an error into a stable fingerprint so the same root cause groups together across tests."""
from __future__ import annotations

import hashlib
import re

_VOLATILE = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<uuid>"),
    (re.compile(r"\b0x[0-9a-f]+\b", re.I), "<hex>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}:\d{2}(\.\d+)?z?", re.I), "<time>"),
    (re.compile(r"\b\d+(\.\d+)?\b"), "<n>"),
]


def normalize(text: str) -> str:
    out = text.lower()
    for pattern, token in _VOLATILE:
        out = pattern.sub(token, out)
    return re.sub(r"\s+", " ", out).strip()


def top_frames(trace: str, n: int = 2) -> list[str]:
    """First stack frames outside the JDK and test frameworks: where the failure happened in user code."""
    frames = re.findall(r"at ([\w$.]+)\(", trace)
    skip = ("java.", "javax.", "jdk.", "sun.", "org.testng.", "org.junit.", "io.restassured.", "org.openqa.",
            "org.postgresql.", "com.mysql.", "org.apache.", "org.springframework.", "com.zaxxer.")
    return [f for f in frames if not f.startswith(skip)][:n]


def fingerprint(error_type: str, message: str) -> str:
    """Error type plus normalized message. Test-method frames are left out on purpose, so the
    same product bug hit by several tests lands in one group."""
    key = f"{error_type}|{normalize(message)}"
    return hashlib.sha1(key.encode()).hexdigest()[:10]


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z<>]+", normalize(text)))


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0
