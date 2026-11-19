import zipfile

MAX = 100 * 2**20


def unpack(path, dest):
    with zipfile.ZipFile(path) as zf:
        if sum(i.file_size for i in zf.infolist()) > MAX:
            raise ValueError("archive too large")
        for info in zf.infolist():
            zf.extract(info, dest)
