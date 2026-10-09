"""Re-encode all game PNGs as plain 8-bit RGBA PNGs.

The DOS build's libpng rejects some stock PNGs that carry iCCP/zTXt
ancillary chunks ("Cannot load an image"). Stripping every PNG to a
bare IHDR/IDAT/IEND RGBA stream removes that failure class.
Run: python3 tools/strip_pngs.py [dir ...]   (default: game/images game/system)
"""
import sys
from pathlib import Path
from PIL import Image

roots = [Path(p) for p in sys.argv[1:]] or [Path("game/images"), Path("game/system")]
n = 0
for root in roots:
    for p in sorted(root.rglob("*.png")):
        im = Image.open(p)
        im.convert("RGBA").save(p)
        n += 1
print(f"re-encoded {n} PNGs")
