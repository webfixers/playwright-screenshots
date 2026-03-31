#!/usr/bin/env python3
"""Pack a small PNG iconset into a macOS .icns file."""

from __future__ import annotations

import struct
import sys
from pathlib import Path


ICON_CHUNKS = [
    ("icp4", "icon_16x16.png"),
    ("icp5", "icon_32x32.png"),
    ("icp6", "icon_32x32@2x.png"),
    ("ic07", "icon_128x128.png"),
    ("ic08", "icon_256x256.png"),
    ("ic09", "icon_512x512.png"),
    ("ic10", "icon_512x512@2x.png"),
]


def build_icns(iconset_dir: Path, output_path: Path) -> None:
    chunks: list[bytes] = []
    for chunk_type, filename in ICON_CHUNKS:
        png_path = iconset_dir / filename
        if not png_path.exists():
            raise FileNotFoundError(f"Missing icon file: {png_path}")
        data = png_path.read_bytes()
        chunks.append(chunk_type.encode("ascii") + struct.pack(">I", len(data) + 8) + data)

    body = b"".join(chunks)
    icns_data = b"icns" + struct.pack(">I", len(body) + 8) + body
    output_path.write_bytes(icns_data)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: build_icns.py <iconset-dir> <output.icns>", file=sys.stderr)
        return 1

    build_icns(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
