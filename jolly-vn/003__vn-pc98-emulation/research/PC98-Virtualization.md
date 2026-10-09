## PC98 Virtualization

## Technical Goal
Is it possible in a web browser to serve up a virtualized PC-98 environment, so we can build a real game for the PC-98?

## Technical Exploration

Verdict: yes. Both halves are solved upstream. Browser-side PC-98 emulation works today via WebAssembly ports of Neko Project II kai, and building a new visual-novel game that runs on real PC-98 hardware works today via the Suika3 engine (plus low-level homebrew toolchains as a fallback).

### 1. Virtualized PC-98 in the browser

- [WebNP2](https://uraraworks.github.io/WebNP2/?lang=en) is an online PC-98 emulator powered by Neko Project II kai, delivered as WebAssembly. Source at [uraraworks/webnp2](https://github.com/uraraworks/webnp2), described upstream as a web-based PC-98 emulator player powered by NP2kai (wasm). This is the fastest path to "serve up a virtualized PC-98": host the player, supply our own disk image, users play in the tab with no install.
- [Neko Project II kai](https://github.com/AZO234/NP2kai) is the reference emulator behind it. The libretro port ([docs](https://docs.libretro.com/library/neko_project_ii_kai/)) gives a local/RetroArch alternative using the same core, accepting user-supplied `.d98` / `.fdi` / `.hdi` images.
- [DOSBox-X on Emscripten](https://yksoft1.github.io/dosboxxem-demo/) is a second browser option: a DOSBox-X build for Emscripten with a PC-98 machine mode and fixed-cycle demos. Less turnkey than WebNP2 for PC-98, but useful as a fallback.
- Local dev/test emulator: [Neko Project 21/W](https://simk98.github.io/np21w/) is the actively maintained Windows fork most PC-98 releases target. Boot a game image with `-drive 0 game.hdi`-style CLI or via the GUI drive slots.

Constraint: emulators need PC-98 BIOS/font ROMs supplied by the user. We cannot redistribute those; the standard pattern (see WebNP2/RetroArch docs) is the player ships without firmware and each user provides their own dump.

### 2. Actually building a game for the PC-98

Recommended path: [Suika3 visual-novel engine](https://github.com/awemorris/suika3). It is a C89 VN/2D engine whose supported-platform list explicitly includes NEC PC-9801 ("really works") alongside WebAssembly. Verified from its README:

- `NEC PC-9801 MS-DOS` artifact: `suika-98.exe`, built with the `pc98` preset (`MS-DOS NEC PC-9801`, OpenWatcom, Executable).
- `Wasm (HTML)` artifact: `suika3-wasm.html` via Emscripten, with a live browser demo on the project site.
- Ships a PC-98 screenshot (80386/JIT, PCM sound) proving the target runs.

Why this fits: we write the Jolly VN once in Suika's script format and get both a genuine `suika-98.exe` (bootable in WebNP2 / Neko Project 21/W / real hardware with MS-DOS) and a modern Wasm build. No direct GDC/text-plane programming needed; asset pipeline is text + images + audio packed per the per-platform asset rules (Wasm wants `assets.arc` next to `index.html`).

Fallback path (raw homebrew, more work): C with [gcc-ia16](https://github.com/tkchia/gcc-ia16) or OpenWatcom targeting 16-bit real-mode DOS on the PC-9801, following the [PC-98 game-dev tutorial](https://github.com/swallace100/pc98-tutorial) (real-hardware + Neko Project 21/W workflow, written for the PC-98 game jam) and examples like the [naiz PC-98 real-mode engine](https://github.com/edouardlicn123/naiz). This means handling the dual µPD7220 text/graphics planes, 640x400 16-color modes, and PC-9801-86 sound directly. Only worth it if Suika3's constraints chafe.

PC-98 hardware realities that shape the design either way: 640x400, 16 colors (or 256 with later GDC/EGC), text plane separate from graphics plane, floppy/HDD image distribution (`.fdi`/`.hdi`), Japanese font ROM expectations, and FM/PCM audio rather than modern codecs. Our 001 recipe (large cropped portrait, full-width dialogue box, exact UI strings) maps cleanly onto this.

### 3. Proposed architecture for Jolly VN

1. Author the VN in Suika3 script + downscaled 001 assets (16-color-safe backgrounds, Jolly sprites from the v4 sheet).
2. Build `suika-98.exe` via the `pc98` OpenWatcom preset; package into an `.hdi`/`.fdi` with MS-DOS boot files.
3. Test locally in Neko Project 21/W.
4. Serve the same image through a self-hosted WebNP2 player page for one-click browser play. Ship the Wasm build as the accessible fallback for users without BIOS dumps.

### Open Questions / Next Steps

- Confirm WebNP2 self-hosting story: which files the player needs beside the disk image (wasm, BIOS loader, config) and its license.
- Confirm Suika3 PC-98 asset limits (image size/format, audio format, memory ceiling on 640KB-class machines).
- Decide distribution images: bootable `.hdi` with bundled DOS vs. game-disk-only `.fdi` requiring the user to supply DOS.
- Spike: build stock `suika-98.exe` + sample game, boot it in Neko Project 21/W, then in WebNP2, and record steps.
