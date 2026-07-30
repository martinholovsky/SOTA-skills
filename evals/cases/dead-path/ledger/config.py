"""Deployment configuration."""

# Dotted path to the exporter used for everything except the legacy batch feed.
EXPORTER = "ledger.exporters.csv_export"

# Maximum amount a single entry may post.
AMOUNT_LIMIT = 1_000_000
