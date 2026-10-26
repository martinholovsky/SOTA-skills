import os


def thumb(path):
    os.system("convert " + path + " thumb.png")
