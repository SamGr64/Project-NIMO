from __future__ import annotations

import hashlib


def child_seed(master_seed: int, namespace: str) -> int:
    """Derive a stable independent 64-bit seed for a named component."""
    payload = f"nimo:{master_seed}:{namespace}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")
