## PC98 Procedural Hook

## Technical Goal
If we virtualize the PC-98 and build a real game for it, can procedural generation live outside the emulated machine and feed new images and data in? I.e. is there an interface between the host (modern pipeline, Meta models) and the virtualized environment?

## Technical Exploration

Verdict: yes, but the hook is the disk-image / asset boundary, not a live wire into the emulated CPU. The practical pattern is generate-outside, pack-into-image, boot-or-swap. A true runtime stream into a running 16-bit guest is possible in theory (serial port) but unverified and almost certainly not worth it.

### Pattern A — offline build-time packing (recommended)

This extends the pipeline we already have. Today `generate_scenes.py` outputs `.webp` scenes plus `run-log.jsonl`. The PC-98 step adds conversion and packing:

1. Generate scenes/dialogue on the host with Muse Image 1.0 + text model (existing scripts).
2. Convert each image for the target: resize to 640x400, quantize to 16 colors with dithering, save as PNG.
3. Emit game data as a Suika3 NovelML script (`start.novel`): `[bg file="bg/s01.png"]`, `[ch ...]`, `[text ...]`, `[choose ...]` tags per beat. Suika3's tutorial uses exactly this layout (`assets/bg/`, `assets/ch/`, PNG/JPEG/WebP supported).
4. Pack: `suika3-pack` produces `assets.arc` for the Wasm build; for the PC-98 build the game files go onto a bootable `.hdi` / `.fdi` disk image alongside `suika-98.exe`.
5. Boot the image in Neko Project 21/W locally, or serve it through the WebNP2 player page.

Why this is the right default: fully deterministic, auditable (extends the run-log pattern), no emulator modifications, and identical content ships to both the authentic PC-98 artifact and the modern Wasm fallback.

### Pattern B — warm file-swap into a running session (near-live)

For "new chapter arrives while the page is open", no reboot of the host page is needed if the game re-reads from disk:

- WebNP2 takes disk images as URL parameters (`hdd=<HDD image URL>&fd1=<FD1 image URL>&fd2=<FD2 image URL>&run=1`, per its README). A fresh chapter is just a new `.fdi` hosted at a URL: point the player at it, or use the emulator's disk-swap UI (NP2 menu / libretro Disk Control: eject, change index, re-insert) to mount it into a running session.
- DOSBox-X Emscripten builds expose an Emscripten filesystem (MEMFS for the session, IDBFS persisted in the browser database) and the classic `mount` command maps host folders to guest drives. New files dropped into the mounted folder are visible to DOS immediately.
- Requirement on our side: the game must re-read chapter data from disk on demand rather than caching everything at boot. In Suika3 terms that means one NovelML file per chapter plus per-chapter assets, loaded on transition. To be confirmed by spike.

This gives chapter-by-chapter procedural delivery with at most a disk swap, which preserves the "real PC-98" story end to end.

### Pattern C — live channel into the guest (not recommended)

The classical host-to-guest wire on real hardware is the RS-232C serial port, and NP2kai-family emulators have serial options that could in principle be mapped to a host TCP socket or pipe. Status: unverified for WebNP2, fiddly (baud-rate-era protocol, custom DOS receiver needed inside the game), and it buys nothing Pattern B does not already deliver.

The honest version of "live": run procedural generation against the Suika3 Wasm build, which fetches assets over plain HTTP like any web app. New content is just new files on the server. Keep the emulated PC-98 build as the authentic per-chapter artifact (Patterns A/B); do the streaming tricks outside emulation where the platform supports them.

### Conversion constraints (host-side work)

- Current generator output is full-color `.webp`; the PC-98 path needs 640x400, 16-color, dithered PNG. New step: a `convert_pc98.py` (resize, palette quantize, dither, size budget per floppy/HDD/memory limits TBD by spike).
- Text must stay glyph-safe: confirm what the PC-98 build renders (font ROM dependency, Shift-JIS vs ASCII) before generating Japanese UI strings per chapter.
- Keep the 001 recipe constraints on the generator side (anchor sheet on every turn, no emotion words unless the beat needs them) so converted sprites stay on-model before they ever reach the disk image.

### Proposed pipeline

`generate_scenes.py` (exists) -> `convert_pc98.py` (new: resize/quantize/dither) -> chapter `.novel` writer (new) -> pack `.hdi`/`.fdi` + `assets.arc` -> Neko Project 21/W (local check) -> WebNP2 URL (browser delivery).

## Open Questions / Next Steps

- Does `suika-98.exe` read loose game files or `assets.arc` on DOS, and what are its image size/format/memory ceilings? (Spike: build the sample game for `pc98`, inspect, boot.)
- WebNP2 self-hosting file list and whether cross-origin `hdd`/`fd1` URLs need CORS headers.
- Floppy-swap spike: generate two chapters as two `.fdi` files, swap mid-session, confirm the game picks up chapter 2.
- Serial-port spike only if Pattern B proves insufficient (expect it won't be needed).
