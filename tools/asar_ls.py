#!/usr/bin/env python3
"""Minimal ASAR header reader: list entries, filter, and report 'unpacked' flags.

Usage:
  python asar_ls.py <app.asar> [substring-filter]
"""
import json
import struct
import sys


def read_header(path):
    with open(path, "rb") as f:
        f.read(4)  # uint32 == 4 (size of the next field)
        header_pickle_size = struct.unpack("<I", f.read(4))[0]
        blob = f.read(header_pickle_size)
    # pickle layout: [payloadSize][stringByteLength][utf8 json]
    json_size = struct.unpack("<I", blob[4:8])[0]
    return json.loads(blob[8:8 + json_size].decode("utf-8")), 8 + header_pickle_size


def walk(node, prefix="", out=None):
    out = [] if out is None else out
    for name, meta in node.get("files", {}).items():
        path = f"{prefix}/{name}" if prefix else name
        if "files" in meta:
            walk(meta, path, out)
        else:
            out.append((path, bool(meta.get("unpacked")), int(meta.get("size", 0))))
    return out


def main():
    asar = sys.argv[1]
    needle = sys.argv[2] if len(sys.argv) > 2 else ""
    root, data_off = read_header(asar)
    entries = walk(root)
    hits = [e for e in entries if needle.lower() in e[0].lower()]
    print(f"# asar entries: {len(entries)}  data offset: {data_off}")
    print(f"# filter: {needle!r}  hits: {len(hits)}")
    for path, unpacked, size in sorted(hits):
        flag = "UNPACKED" if unpacked else "in-archive"
        print(f"{flag:10s} {size:9d}  {path}")


if __name__ == "__main__":
    main()
