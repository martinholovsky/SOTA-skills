import logging

log = logging.getLogger(__name__)


def run():
    try:
        step()
    except Exception:
        log.exception("step failed")
        raise
