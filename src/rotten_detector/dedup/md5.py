import hashlib
from io import BufferedIOBase


def md5_of(stream: BufferedIOBase) -> str:
    return hashlib.file_digest(stream, "md5").hexdigest()
