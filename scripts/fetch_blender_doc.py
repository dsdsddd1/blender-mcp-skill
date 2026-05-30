#!/usr/bin/env python3
"""Fetch a Blender docs page and print a compact text summary."""

from __future__ import annotations

import argparse
import html
import re
import urllib.request


def html_to_text(markup: str) -> str:
    markup = re.sub(r"<script[\s\S]*?</script>", " ", markup)
    markup = re.sub(r"<style[\s\S]*?</style>", " ", markup)
    markup = re.sub(r"<[^>]+>", " ", markup)
    text = html.unescape(markup)
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--chars", type=int, default=2500)
    args = parser.parse_args()

    req = urllib.request.Request(args.url, headers={"User-Agent": "Codex Blender Manual Skill"})
    with urllib.request.urlopen(req, timeout=20) as response:
        markup = response.read().decode("utf-8", errors="replace")

    title_match = re.search(r"<title>(.*?)</title>", markup, re.S | re.I)
    title = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else args.url
    text = html_to_text(markup)
    print(f"TITLE: {title}")
    print(f"URL: {args.url}")
    print()
    print(text[: args.chars])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
