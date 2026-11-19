import zipfile


def unpack(path, dest):
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            zf.extract(info, dest)
