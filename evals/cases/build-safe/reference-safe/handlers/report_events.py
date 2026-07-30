"""Handlers for report lifecycle events."""
from reportkit.handlers import register


@register("report.created")
def on_created(payload):
    return {"indexed": payload["report_id"]}


@register("report.deleted")
def on_deleted(payload):
    return {"unindexed": payload["report_id"]}
