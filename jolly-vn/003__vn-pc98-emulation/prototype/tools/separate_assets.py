"""Separate UI from screens: clean backgrounds + standalone Jolly sprite.

Why: the 001 wave-v2 scene WebPs are finished screenshots. Each one has
the dialogue box, name plate, Japanese text, floating choice/menu, and
the Jolly bust baked into the pixels. Rendering engine UI over them
(the old prototype) double-overlays everything.

Correct layering for Suika3 (and any VN engine):
  background image (scene only)  <- this script, assets-clean/bg/
  character sprite (transparent) <- this script, assets-clean/ch/
  message box / name plate /     <- drawn by suika-98.exe at runtime
  choice buttons                    from system/ + config.ini

Salvage method (no image model needed): crop the scene above the
dialogue box, drop the bust side, resize to 640x400, quantize to the
fixed 16-color PC-98 palette. The occluded strip behind the bust is
unrecoverable locally; production quality needs regeneration with
the no-UI prompts in game/CLEAN-ASSET-PROMPTS.md.

Usage: python3 tools/separate_assets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT.parent.parent / "001__stylized-pc98-jolly-visual-novel-concept" / "outputs" / "scenes" / "v2"
SHEET = ROOT.parent.parent / "000__find-jolley-assets" / "outputs" / "jolly-character-sheet-v4.webp"
OUT_BG = ROOT / "assets-clean" / "bg"
OUT_CH = ROOT / "assets-clean" / "ch"

# scene file -> (short name, bust side, dialogue-top y in 1920x1280 source)
SCENES = [
    ("pc98-jolly-vn-s01-matsuri.webp", "matsuri", "left", 923),
    ("pc98-jolly-vn-s02-shrine.webp", "shrine", "left", 974),
    ("pc98-jolly-vn-s03-rooftop.webp", "rooftop", "left", 956),
    ("pc98-jolly-vn-s04-ramen.webp", "ramen", "right", 960),
    ("pc98-jolly-vn-s05-lake.webp", "lake", "left", 958),
]
BUST_W = 640  # bust occupies roughly this many source px on its side

PC98_PALETTE = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]


def palette_image() -> Image.Image:
    pal = Image.new("P", (1, 1))
    flat: list[int] = []
    for r, g, b in PC98_PALETTE:
        flat.extend([r, g, b])
    flat.extend([0] * (768 - len(flat)))
    pal.putpalette(flat)
    return pal


# Baked floating UI that survives the dialogue crop, in 640x400 output
# coordinates: (x0, y0, x1, y1). Covered with a mirrored neighbour strip.
FLOATING_UI = {
    "matsuri": [(385, 280, 640, 400), (0, 25, 115, 185)],
    "ramen": [(0, 150, 210, 400)],
}


def cover_ui(img: Image.Image, boxes: list[tuple[int, int, int, int]]) -> Image.Image:
    img = img.copy()
    for x0, y0, x1, y1 in boxes:
        w = x1 - x0
        sx0 = max(0, x0 - w) if x1 >= img.width else x0
        if x1 >= img.width and x0 - w >= 0:
            patch = img.crop((x0 - w, y0, x0, y1)).transpose(Image.FLIP_LEFT_RIGHT)
        else:
            patch = img.crop((x1, y0, min(img.width, x1 + w), y1)).transpose(Image.FLIP_LEFT_RIGHT)
            patch = patch.resize((w, y1 - y0))
        img.paste(patch, (x0, y0))
    return img


def clean_background(name: str, short: str, side: str, dlg_top: int) -> Path:
    img = Image.open(SRC / name).convert("RGB")
    w, _ = img.size
    scene = img.crop((0, 0, w, dlg_top))  # drop dialogue box + baked text
    if side == "left":
        scene = scene.crop((BUST_W, 0, w, dlg_top))  # drop baked bust
    else:
        scene = scene.crop((0, 0, w - BUST_W, dlg_top))
    scene = scene.resize((640, 400), Image.LANCZOS)
    scene = cover_ui(scene, FLOATING_UI.get(short, []))  # drop floating choice/menu
    out = OUT_BG / f"{short}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.quantize(palette=palette_image(), dither=Image.FLOYDSTEINBERG).convert("RGB").save(out, optimize=True)
    return out


def jolly_sprite() -> Path:
    sheet = Image.open(SHEET).convert("RGB")
    w, h = sheet.size
    print(f"character sheet: {w}x{h}")
    # Front pose estimate from the v4 sheet layout (verified visually in 000).
    crop = sheet.crop((int(w * 0.17), int(h * 0.08), int(w * 0.39), int(h * 0.53)))
    rgba = crop.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, _ = px[x, y]
            whiteness = min(r, g, b)
            alpha = 0 if whiteness > 235 else (255 if whiteness < 180 else int((235 - whiteness) * 255 / 55))
            px[x, y] = (r, g, b, alpha)
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    rgba.thumbnail((360, 380), Image.LANCZOS)
    out = OUT_CH / "jolly.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out, optimize=True)
    return out


def main() -> int:
    for name, short, side, top in SCENES:
        out = clean_background(name, short, side, top)
        print(f"clean bg {short}: {out} ({out.stat().st_size} B) [scene only, no UI/bust/text]")
    out = jolly_sprite()
    print(f"sprite jolly: {out} ({out.stat().st_size} B) [transparent PNG, engine-drawn separately]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
