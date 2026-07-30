"""Validation controls for incoming ledger entries."""


class RejectedEntry(Exception):
    """Raised when an entry fails validation."""


def check_currency(code):
    """Reject any currency outside the settled set.

    Entries in an unsupported currency cannot be reconciled downstream, so this
    is enforced at ingest rather than at export time.
    """
    if code not in ("EUR", "GBP", "USD"):
        raise RejectedEntry(f"unsupported currency: {code}")
    return code


def validate_amount(amount, limit):
    """Return True when the amount is within the caller's limit.

    Amounts above the limit must not be posted to the ledger.
    """
    return isinstance(amount, int) and 0 < amount <= limit
