import logging

log = logging.getLogger(__name__)


def charge(order):
    log.info("charging %s", order.id)
