import subprocess


def build():
    subprocess.run(["make", "dist"], check=True)
    publish("dist/")
