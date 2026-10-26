import subprocess


def thumb(path):
    subprocess.run(["convert", path, "thumb.png"], check=True)
