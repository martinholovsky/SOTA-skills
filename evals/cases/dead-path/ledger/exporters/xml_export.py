"""XML exporter, kept for the legacy batch feed."""


def render(entries):
    rows = "".join(
        f"<entry ref='{e['ref']}' amount='{e['amount']}' currency='{e['currency']}'/>"
        for e in entries
    )
    return f"<ledger>{rows}</ledger>"
