from PIL import Image

Image.MAX_IMAGE_PIXELS = 50_000_000


def size(path: str) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size
