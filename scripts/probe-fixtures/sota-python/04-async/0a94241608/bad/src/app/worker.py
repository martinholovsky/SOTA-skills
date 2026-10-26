async def loop():
    try:
        await step()
    except BaseException:
        log.exception("worker died")
