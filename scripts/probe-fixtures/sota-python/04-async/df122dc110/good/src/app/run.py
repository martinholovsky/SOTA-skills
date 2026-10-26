import asyncio


async def convert(path):
    proc = await asyncio.create_subprocess_exec("convert", path)
    await proc.wait()
