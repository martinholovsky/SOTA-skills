import subprocess


def build():
    subprocess.run(["make", "dist"])
    publish("dist/")
