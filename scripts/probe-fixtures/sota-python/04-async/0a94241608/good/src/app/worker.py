async def loop():
    try:
        await step()
    except Exception:
        log.exception("worker died")
