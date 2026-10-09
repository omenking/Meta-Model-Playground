"""Pack game assets into a Suika3 `assets.arc` package.

The MS-DOS (PC-98/PC-AT) builds of Suika3 cannot open loose files whose
paths exceed DOS 8.3 limits (e.g. `system/message/msgbox-hide.anime`),
so DOS distribution uses the engine's own package format: the HAL tries
`assets.arc` before the real file system for every read.

Format (from StratoHAL stdfile.c, the engine's own reader):
  uint64le  entry_count
  per entry: char name[256] (XOR-obfuscated), uint64le size, uint64le offset
  file data at absolute offsets (XOR-obfuscated)

Obfuscation stream (per entry index i, seeded independently for the
name field and for the file body):
  seed: next = KEY; repeat i times: next ^= MASK1; next = rotl64(next, 1)
  byte: ret = next & 0xff
        next = (((KEY & 0xff00) * next + (KEY & 0xff)) % KEY) ^ MASK2
  with KEY = 0xabadcafedeadbeef (the engine's published default key).

Usage:
  python3 tools/pack_assets.py --out game/assets.arc \
      --root game config.ini start.novel main.ray images system
  python3 tools/pack_assets.py --verify game/assets.arc --root game
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

KEY = 0xABADCAFEDEADBEEF
MASK1 = 0xAFCB8F2FF4FFF33F
MASK2 = 0xFCBFAFF8F2F4F3F0
U64 = 0xFFFFFFFFFFFFFFFF
NAME_SIZE = 256
ENTRY_SIZE = NAME_SIZE + 8 + 8
MAX_ENTRIES_PC98 = 1024


def _seed(index: int) -> int:
    nxt = KEY
    for _ in range(index):
        nxt ^= MASK1
        lsb = nxt >> 63
        nxt = ((nxt << 1) | lsb) & U64
    return nxt


class Stream:
    def __init__(self, index: int):
        self.next = _seed(index)

    def byte(self) -> int:
        ret = self.next & 0xFF
        nxt = (((KEY & 0xFF00) * self.next + (KEY & 0xFF)) & U64) % KEY
        self.next = (nxt ^ MASK2) & U64
        return ret

    def apply(self, data: bytes) -> bytes:
        return bytes(b ^ self.byte() for b in data)


def collect(root: Path, rels: list[str]) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for rel in rels:
        p = root / rel
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    out.append((f.relative_to(root).as_posix(), f))
        elif p.is_file():
            out.append((rel, p))
        else:
            raise SystemExit(f"missing input: {p}")
    out.sort(key=lambda t: t[0])
    return out


def pack(root: Path, rels: list[str], out_path: Path) -> None:
    files = collect(root, rels)
    if len(files) > MAX_ENTRIES_PC98:
        raise SystemExit(f"too many entries for PC-98 build: {len(files)} > {MAX_ENTRIES_PC98}")
    header_size = 8 + len(files) * ENTRY_SIZE
    entries = []
    blobs = []
    offset = header_size
    for idx, (name, path) in enumerate(files):
        data = path.read_bytes()
        name_raw = name.encode("utf-8")
        if len(name_raw) >= NAME_SIZE:
            raise SystemExit(f"entry name too long: {name}")
        name_field = name_raw + b"\0" * (NAME_SIZE - len(name_raw))
        entries.append((Stream(idx).apply(name_field), len(data), offset))
        blobs.append(Stream(idx).apply(data))
        offset += len(data)
    with out_path.open("wb") as fp:
        fp.write(struct.pack("<Q", len(files)))
        for name_field, size, off in entries:
            fp.write(name_field)
            fp.write(struct.pack("<Q", size))
            fp.write(struct.pack("<Q", off))
        for blob in blobs:
            fp.write(blob)
    print(f"wrote {out_path} ({offset} B, {len(files)} entries)")


def verify(arc: Path, root: Path) -> int:
    raw = arc.read_bytes()
    (count,) = struct.unpack_from("<Q", raw, 0)
    bad = 0
    for i in range(count):
        pos = 8 + i * ENTRY_SIZE
        name = Stream(i).apply(raw[pos:pos + NAME_SIZE]).split(b"\0")[0].decode("utf-8")
        size, off = struct.unpack_from("<QQ", raw, pos + NAME_SIZE)
        data = Stream(i).apply(raw[off:off + size])
        expect = (root / name).read_bytes() if (root / name).exists() else None
        if expect is None:
            print(f"  ? {name} (not under root, {size} B)")
        elif data != expect:
            print(f"  MISMATCH {name}")
            bad += 1
    print(f"verify: {count} entries, {bad} mismatches")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--root", default="game")
    ap.add_argument("--verify")
    ap.add_argument("inputs", nargs="*")
    args = ap.parse_args()
    root = Path(args.root)
    if args.verify:
        return verify(Path(args.verify), root)
    if not args.out or not args.inputs:
        ap.error("--out and at least one input are required")
    pack(root, args.inputs, Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
