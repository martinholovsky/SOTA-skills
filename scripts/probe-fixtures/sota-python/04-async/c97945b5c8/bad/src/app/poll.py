import time


async def poll():
    while True:
        time.sleep(1)
        await check()
