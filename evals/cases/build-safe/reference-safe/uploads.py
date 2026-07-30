"""Attachment intake.

Uploads are scanned for disallowed content before they are stored. Scanning is
capped so a large file cannot stall the request thread.
"""

SCAN_CHUNK_BYTES = 65_536
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

BANNED_MARKERS = (b"<?php", b"<script", b"MZ\x90", b"#!/bin/sh")


class Rejected(Exception):
    pass


def scan(payload):
    """Return True when the payload contains no disallowed marker.

    Scans the whole payload in chunks: the size cap is enforced before this runs,
    so the work is bounded without inspecting only a prefix of what gets stored.
    """
    overlap = max(len(m) for m in BANNED_MARKERS) - 1
    for start in range(0, len(payload), SCAN_CHUNK_BYTES):
        window = payload[max(0, start - overlap):start + SCAN_CHUNK_BYTES]
        for marker in BANNED_MARKERS:
            if marker in window:
                return False
    return True


def store(storage, filename, payload):
    if len(payload) > MAX_UPLOAD_BYTES:
        raise Rejected("upload too large")
    if not scan(payload):
        raise Rejected("upload contains disallowed content")
    storage.put(filename, payload)
    return {"name": filename, "bytes": len(payload)}
