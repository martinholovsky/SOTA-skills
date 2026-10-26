import subprocess


def thumb(path):
    subprocess.run(f"convert {path} thumb.png", shell=True, check=True)
