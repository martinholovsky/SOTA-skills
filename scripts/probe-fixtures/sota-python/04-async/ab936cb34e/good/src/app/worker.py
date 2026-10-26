import asyncio


async def loop():
    try:
        await step()
    except asyncio.CancelledError:
        log.info("stopping")
        raise
