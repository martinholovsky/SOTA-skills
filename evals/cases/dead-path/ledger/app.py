"""Ledger ingest and export.

Entries arrive from one of two sources. The batch feed was retired when the
upstream provider moved to the JSON API, but the XML rendering path is kept for
the legacy batch feed.
"""
from ledger import config
from ledger.controls import RejectedEntry, check_currency, validate_amount
from ledger.exporters import load
from ledger.exporters import xml_export


class Source:
    API = "api"
    LEGACY_BATCH = "legacy_batch"


def parse(payload):
    """Build an entry from an inbound API payload.

    The API is the only inbound path; it always yields Source.API entries.
    """
    return {
        "ref": payload["ref"],
        "amount": payload["amount"],
        "currency": check_currency(payload["currency"]),
        "source": Source.API,
    }


def ingest(payload, limit=config.AMOUNT_LIMIT):
    """Validate an inbound payload and return the entry to post."""
    entry = parse(payload)
    validate_amount(entry["amount"], limit)
    return entry


def export(entries):
    """Render entries with the configured exporter.

    Legacy-batch entries render as XML; everything else uses the configured
    default exporter.
    """
    if entries and entries[0]["source"] == Source.LEGACY_BATCH:
        return xml_export.render(entries)
    render = load(config.EXPORTER)
    return render(entries)
