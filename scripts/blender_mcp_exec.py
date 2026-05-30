#!/usr/bin/env python3
"""Execute a small Python snippet through Blender's official MCP socket."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path


def read_code(args: argparse.Namespace) -> str:
    if args.code:
        return args.code
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--code", help="Python code to execute in Blender.")
    parser.add_argument("--file", help="Read Python code from this file.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--loose-json", action="store_true", help="Allow repr fallback for non-JSON values.")
    args = parser.parse_args()

    code = read_code(args)
    payload = {
        "type": "execute",
        "code": code,
        "strict_json": not args.loose_json,
    }

    with socket.create_connection((args.host, args.port), timeout=args.timeout) as sock:
        sock.settimeout(args.timeout)
        sock.sendall(json.dumps(payload).encode("utf-8") + b"\0")
        data = bytearray()
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            if b"\0" in chunk:
                data.extend(chunk[: chunk.index(b"\0")])
                break
            data.extend(chunk)

    print(json.dumps(json.loads(data.decode("utf-8")), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
