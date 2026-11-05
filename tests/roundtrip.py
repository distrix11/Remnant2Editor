"""Byte-exact round-trip test: decompress -> parse -> write must equal the original stream.

usage: python tests/roundtrip.py <file.sav> [<file.sav> ...]
Files are only read, never modified.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from r2save.core import SaveFile, decompress  # noqa: E402


def check(path):
    t = time.time()
    with open(path, "rb") as f:
        raw = f.read()
    buf = decompress(raw)
    sf = SaveFile.from_buffer(buf)
    t_parse = time.time() - t
    out = sf.to_buffer()
    if out != buf:
        n = min(len(out), len(buf))
        diff = next((i for i in range(n) if out[i] != buf[i]), n)
        print("FAIL %s: len %d vs %d, first diff at %d" % (path, len(buf), len(out), diff))
        return False
    # compress -> decompress -> parse again
    again = decompress(sf.to_bytes())
    ok = again == buf
    print("%s %s: %d bytes, %d objects, parse %.2fs" % (
        "OK  " if ok else "FAIL", os.path.basename(path), len(buf), len(sf.data.objects), t_parse))
    return ok


if __name__ == "__main__":
    res = [check(p) for p in sys.argv[1:]]
    sys.exit(0 if all(res) else 1)
