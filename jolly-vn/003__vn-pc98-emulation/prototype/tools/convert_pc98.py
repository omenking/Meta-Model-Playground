"""Convert modern scene art into PC-98-ready background PNGs.

Input : full-color .webp / .png / .jpg (e.g. generate_scenes.py output)
Output: 640x400 PNG quantized to a fixed 16-color PC-98-style palette
        with Floyd-Steinberg dithering.

The fixed palette mirrors the classic PC-9801 16-color GDC palette
(8 basic + 8 bright). Quantizing to a fixed palette (instead of an
adaptive one) keeps every chapter visually consistent and matches the
"16 colors, heavy dithering, 640x400" recipe from the 001 concept.
Byte sizes are printed so image/memory ceilings can be recorded
(Prototype Phase 1 validation).

Usage:
  python3 tools/convert_pc98.py assets/source/pc98-jolly-vn-s01-matsuri.webp
  python3 tools/convert_pc98.py assets/source/*.webp --out-dir assets/bg-pc98
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

TARGET_W, TARGET_H = 640, 400

# Classic 16-color palette (RGB). Order matters only for determinism.
PC98_PALETTE: list[tuple[int, int, int]] = [
    (0, 0, 0),        # black
    (0, 0, 170),      # blue
    (0, 170, 0),      # green
    (0, 170, 170),    # cyan
    (170, 0, 0),      # red
    (170, 0, 170),    # magenta
    (170, 85, 0),     # brown / dark yellow
    (170, 170, 170),  # light gray
    (85, 85, 85),     # dark gray
    (85, 85, 255),    # bright blue
    (85, 255, 85),    # bright green
    (85, 255, 255),   # bright cyan
    (255, 85, 85),    # bright red (festival lanterns)
    (255, 85, 255),   # bright magenta / pink trim
    (255, 255, 85),   # bright yellow
    (255, 255, 255),  # white
]

# Short scene names used by the NovelML [bg] tags.
SCENE_NAMES = {
    "pc98-jolly-vn-s01-matsuri": "matsuri",
    "pc98-jolly-vn-s02-shrine": "shrine",
    "pc98-jolly-vn-s03-rooftop": "rooftop",
    "pc98-jolly-vn-s04-ramen": "ramen",
    "pc98-jolly-vn-s05-lake": "lake",
}


def palette_image() -> Image.Image:
    pal = Image.new("P", (1, 1))
    flat: list[int] = []
    for r, g, b in PC98_PALETTE:
        flat.extend([r, g, b])
    flat.extend([0] * (768 - len(flat)))
    pal.putpalette(flat)
    return pal


def convert(src: Path, dst: Path) -> dict:
    img = Image.open(src).convert("RGB")
    img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    quantized = img.quantize(palette=palette_image(), dither=Image.FLOYDSTEINBERG)
    dst.parent.mkdir(parents=True, exist_ok=True)
    quantized.save(dst, format="PNG", optimize=True)
    return {
        "src": str(src),
        "dst": str(dst),
        "size_in": src.stat().st_size,
        "size_out": dst.stat().st_size,
        "mode": f"{TARGET_W}x{TARGET_H} 16-color dithered PNG",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WebP/PNG -> 640x400 16-color PC-98 PNG.")
    parser.add_argument("inputs", nargs="+", help="Source images.")
    parser.add_argument("--out-dir", default="assets/bg-pc98", help="Output directory.")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    for raw in args.inputs:
        src = Path(raw)
        short = SCENE_NAMES.get(src.stem, src.stem)
        dst = out_dir / f"{short}.png"
        try:
            info = convert(src, dst)
        except FileNotFoundError:
            print(f"error: missing input {src}", file=sys.stderr)
            return 1
        print(f"{info['src']} ({info['size_in']} B) -> {info['dst']} ({info['size_out']} B) [{info['mode']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
