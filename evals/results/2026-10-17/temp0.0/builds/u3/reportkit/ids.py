"""Tiny UUID-based ID generator."""

import uuid


def new_id() -> str:
    return str(uuid.uuid4())
