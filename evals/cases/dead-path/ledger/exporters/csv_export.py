"""CSV exporter — the default output format."""


def render(entries):
    lines = ["ref,amount,currency"]
    for e in entries:
        lines.append(f"{e['ref']},{e['amount']},{e['currency']}")
    return "\n".join(lines)
