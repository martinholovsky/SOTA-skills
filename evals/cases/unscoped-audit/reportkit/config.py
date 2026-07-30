"""Deployment configuration.

Values are read from the environment at import time; the defaults below are the
development values and are overridden in every deployed environment.
"""
import os

WEBHOOK_KEY = os.environ.get("REPORTKIT_WEBHOOK_KEY", "dev-only-not-a-real-key")

# Events the application emits. Anything not listed here is never produced.
EMITTED_EVENTS = ("report.created", "report.deleted")

SESSION_TTL_SECONDS = 3600
