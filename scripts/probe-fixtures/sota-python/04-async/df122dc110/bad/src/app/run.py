import subprocess


async def convert(path):
    subprocess.run(["convert", path], check=True)
