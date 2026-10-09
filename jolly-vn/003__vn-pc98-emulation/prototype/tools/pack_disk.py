"""Pack NovelML chapters into prototype PC-98 disk images.

Production (per PROTOTYPE.md) packs loose game files + suika-98.exe onto
a bootable .hdi (boot) and per-chapter .fdi floppies, built with the
Suika3 pc98 preset and DOS tooling. No emulator source is modified.

This prototype packer emits the same *contract* in a browser-loadable
form so the chapter-swap mechanics can be demonstrated today without
BIOS ROMs or OpenWatcom: a JSON disk image the WebNP2-style player can
fetch via hdd=/fd1= URL parameters, hot-swap, and reboot from.

Image format (prototype .hdi / .fdi):
  {
    "magic": "JOLLY-PC98-DISK",
    "kind": "hdi" | "fdi",
    "label": "...",
    "createdAt": "ISO-8601",
    "files": { "chapters/ch01.novel": "<file text>", ... },
    "boot": { "chapter": "ch01" }   // hdi only
  }

Usage:
  python3 tools/pack_disk.py --kind hdi --label BOOT --out disks/boot.hdi.json \
      --file chapters/ch01.novel=chapters/ch01.novel --boot-chapter ch01
  python3 tools/pack_disk.py --kind fdi --label CH02-RINGO --out disks/ch02-ringo.fdi.json \
      --file chapters/stub-ch02-ringo.novel=chapters/ch02-ringo.novel
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pack files into a prototype disk image.")
    parser.add_argument("--kind", choices=["hdi", "fdi"], required=True)
    parser.add_argument("--label", required=True, help="Volume label, e.g. BOOT or CH02-RINGO.")
    parser.add_argument("--out", required=True, help="Output image path (.json).")
    parser.add_argument("--file", action="append", default=[], metavar="SRC=DST",
                        help="File to store. Repeatable. DST is the in-disk path.")
    parser.add_argument("--boot-chapter", default=None, help="Chapter id to auto-boot (hdi).")
    args = parser.parse_args(argv)

    files: dict[str, str] = {}
    total = 0
    for spec in args.file:
        if "=" not in spec:
            print(f"error: --file expects SRC=DST, got {spec!r}", file=sys.stderr)
            return 1
        src_raw, dst = spec.split("=", 1)
        src = Path(src_raw)
        if not src.exists():
            print(f"error: missing file {src}", file=sys.stderr)
            return 1
        text = src.read_text(encoding="utf-8")
        files[dst] = text
        total += len(text.encode("utf-8"))
        print(f"  packed {src} -> {dst} ({len(text.encode('utf-8'))} B)")

    image = {
        "magic": "JOLLY-PC98-DISK",
        "kind": args.kind,
        "label": args.label,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    if args.boot_chapter:
        image["boot"] = {"chapter": args.boot_chapter}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(image, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} B on host, {total} B payload, kind={args.kind} label={args.label})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
