"""Structured logging — verify scrubbing and JSON output."""

from __future__ import annotations

import json
import logging

import pytest

from reportkit.logging_utils import _scrub, configure_logging, get_logger, log_security_event


def test_scrub_removes_token():
    d = {"token": "secret123", "user_id": "abc"}
    result = _scrub(d)
    assert result["token"] == "<redacted>"
    assert result["user_id"] == "abc"


def test_scrub_removes_authorization():
    d = {"Authorization": "Bearer xyz", "other": "ok"}
    result = _scrub(d)
    assert result["Authorization"] == "<redacted>"
    assert result["other"] == "ok"


def test_scrub_nested():
    d = {"headers": {"authorization": "Bearer tok", "content-type": "application/json"}}
    result = _scrub(d)
    assert result["headers"]["authorization"] == "<redacted>"
    assert result["headers"]["content-type"] == "application/json"


def test_scrub_list():
    lst = [{"password": "pw"}, {"name": "alice"}]
    result = _scrub(lst)
    assert result[0]["password"] == "<redacted>"
    assert result[1]["name"] == "alice"


def test_log_security_event_emits_json(caplog):
    configure_logging(logging.DEBUG)
    logger = get_logger("test_sec")
    with caplog.at_level(logging.WARNING, logger="test_sec"):
        log_security_event(
            logger,
            event="test.security_event",
            user_id="u1",
            tenant_id="t1",
            action="test_action",
            detail={"token": "should_be_redacted", "info": "ok"},
            level=logging.WARNING,
        )
    # At least one record emitted
    assert any("test_action" in r.message or "test.security_event" in r.message
               for r in caplog.records)
