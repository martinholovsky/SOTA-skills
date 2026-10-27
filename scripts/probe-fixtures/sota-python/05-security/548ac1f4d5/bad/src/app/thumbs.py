from PIL import Image


def size(path: str) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size
