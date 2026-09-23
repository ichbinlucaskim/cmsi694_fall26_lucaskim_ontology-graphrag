"""Download the 2WikiMultiHopQA dev split into data/raw/2wiki/.

Source: the authors' data_ids_april7.zip, linked from
https://github.com/Alab-NII/2wikimultihop (README, "New Update (April 7, 2021)").

The zip holds every split (~259 MB). Dropbox serves it with HTTP range
support, so this script reads the zip's central directory and pulls out only
the members we need (dev.json, and id_aliases.json if present) instead of
downloading the whole archive. Standard library only.

Usage:
    python scripts/download_2wiki.py --list   # list zip contents, extract nothing
    python scripts/download_2wiki.py          # list, check, extract, hash
"""

import argparse
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ZIP_URL = "https://www.dropbox.com/s/ms2m13252h6xubs/data_ids_april7.zip?dl=1"
WANTED = ["dev.json", "id_aliases.json"]
REQUIRED = {"dev.json"}
# Recorded from the first extraction on 2026-09-23; a mismatch means the
# upstream zip changed.
EXPECTED_SHA256 = {
    "dev.json": "79f77ae104088ea8e25b1a65dbece768d45771194663bc5660ec9a98070dadf5",
    "id_aliases.json": "f08ffcb6c2cefca9bdbe86b4248d6ad7a7743762d3f7264c14ff0bae85726fb6",
}
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "2wiki"
BLOCK = 4 * 1024 * 1024  # read-ahead size per range request


class HTTPRangeFile(io.RawIOBase):
    """Read-only, seekable view of a remote file, backed by HTTP range requests."""

    def __init__(self, url):
        # Dropbox redirects each request to a single-use content URL, so every
        # range request goes to the share URL and follows a fresh redirect.
        self.url = url
        self.requests = 0
        self.bytes_fetched = 0
        req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
        with urllib.request.urlopen(req) as r:
            if r.status != 206:
                sys.exit("Server did not honour a range request; refusing full download.")
            self.size = int(r.headers["Content-Range"].rsplit("/", 1)[1])
        self.pos = 0
        self.buf_start = 0
        self.buf = b""

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        return self.pos

    def _fetch(self, start, length):
        end = min(start + length, self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(req) as r:
            if r.status != 206:
                sys.exit(f"Expected HTTP 206 for range request, got {r.status}.")
            data = r.read()
        self.requests += 1
        self.bytes_fetched += len(data)
        return data

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        buf_end = self.buf_start + len(self.buf)
        if not (self.buf_start <= self.pos and self.pos + n <= buf_end):
            self.buf_start = self.pos
            self.buf = self._fetch(self.pos, max(n, BLOCK))
        off = self.pos - self.buf_start
        data = self.buf[off:off + n]
        self.pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="list zip contents and exit")
    args = parser.parse_args()

    print(f"Source: {ZIP_URL}")
    remote = HTTPRangeFile(ZIP_URL)
    print(f"Archive size: {remote.size:,} bytes")
    zf = zipfile.ZipFile(io.BufferedReader(remote, buffer_size=64 * 1024))

    print("\nZip contents:")
    print(f"  {'compressed':>12}  {'uncompressed':>12}  name")
    for info in zf.infolist():
        print(f"  {info.compress_size:>12,}  {info.file_size:>12,}  {info.filename}")
    if args.list:
        return

    by_base = {}
    for info in zf.infolist():
        base = info.filename.rsplit("/", 1)[-1]
        if base in WANTED and not base.startswith("._") and "__MACOSX" not in info.filename:
            by_base.setdefault(base, info)
    missing = [w for w in WANTED if w not in by_base]
    for name in missing:
        print(f"\nNot in this zip: {name}")
    if REQUIRED & set(missing):
        sys.exit("dev.json is missing from the zip; stopping.")

    # Quick check before a full extract: dev.json must carry evidences_id.
    with zf.open(by_base["dev.json"]) as f:
        head = f.read(2 * 1024 * 1024)
    if b'"evidences_id"' not in head:
        sys.exit("No evidences_id field in the first 2 MB of dev.json; stopping.")
    print('\nQuick check: "evidences_id" found in dev.json')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nExtracting to {OUT_DIR}")
    mismatched = []
    for base, info in by_base.items():
        dest = OUT_DIR / base
        with zf.open(info) as src, open(dest, "wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)
        digest = sha256_of(dest)
        ok = digest == EXPECTED_SHA256.get(base)
        print(f"  {base}  sha256={digest}  bytes={dest.stat().st_size:,}  "
              f"{'matches recorded hash' if ok else 'DOES NOT MATCH recorded hash'}")
        if not ok:
            mismatched.append(base)
    if mismatched:
        sys.exit(f"sha256 mismatch for {mismatched}; upstream data may have changed.")

    with open(OUT_DIR / "dev.json") as f:
        n = len(json.load(f))
    print(f"\ndev.json parses as JSON: {n:,} questions")
    print(f"Range requests: {remote.requests}, bytes fetched: {remote.bytes_fetched:,} "
          f"of {remote.size:,}")


if __name__ == "__main__":
    main()
