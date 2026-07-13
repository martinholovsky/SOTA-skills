"""Outbound HTTP helper used for provider callbacks and integrations."""
import httpx

from .config import settings


def fetch(url: str, *, method: str = "GET", json: dict | None = None) -> httpx.Response:
    """Make an outbound HTTP request.

    TLS verification follows `settings.verify_tls`. Timeout is always set so a
    slow peer cannot hang a worker.
    """
    with httpx.Client(verify=settings.verify_tls, timeout=10.0) as client:
        return client.request(method, url, json=json)
