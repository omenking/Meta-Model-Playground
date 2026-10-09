# Prototype: PC-98 Jolly VN in the browser, one chapter at a time

## Goal

Prove the chapter-per-chapter loop end to end with real software: a Jolly visual novel that runs as a genuine PC-98 program inside a browser tab, where finishing Chapter 1 produces a Chapter 2 generated on the host from the player's choices.

## Success Criteria

1. Chapter 1 is completable in a desktop browser tab inside emulated PC-98 hardware, with background art, Jolly sprite, text, and at least one working choice.
2. Reaching the chapter end delivers a Chapter 2 built from the player's Chapter 1 choice; two different choices produce two different, both completable Chapter 2s.
3. No emulator source is modified; all generation and packing happen on the host.
4. The chapter-transition mechanism (hot floppy swap vs reboot with a new image URL) is demonstrated, not assumed, and written down.

## Approach

Guest runs `suika-98.exe` (Suika3 `pc98` preset) plus game files on disk images. Host serves a self-hosted WebNP2 player page pointed at our images through URL parameters. The chapter boundary is a disk boundary: Chapter 1 ships on the boot image, later chapters arrive as floppy images. A small chapter server generates, converts, packs, and serves each new chapter on demand behind a preview/save interstitial.

## Key Decisions

- Engine is Suika3, `pc98` preset via OpenWatcom: the only VN engine found with a verified real PC-9801 target (`suika-98.exe`) plus a WebAssembly build from the same scripts. Raw C homebrew (gcc-ia16, direct GDC programming) is rejected for the prototype as needless risk.
- Browser shell is a self-hosted WebNP2 player: its README verifies URL-loadable images (`hdd`/`fd1`/`fd2`/`lib`), hot floppy swap while running, a browser-to-disk file-transfer dialog, ROM-less boot, and a bundled FreeDOS(98) floppy. Local testing uses Neko Project 21/W, verified as actively maintained.
- Chapter granularity, not per-decision generation: model latency plus the 16-color conversion step cannot fit inside a click response, so choices resolve from on-disk content and re-steering happens at chapter breaks.
- Asset flow reuses the existing pipeline: `generate_scenes.py` output converted to 640x400 dithered 16-color PNG, one NovelML file per chapter, packed onto `.hdi` (boot) and `.fdi` (chapters).

## Steps

### Phase 0 — stock engine boots locally

Fetch the Suika3 SDK release, build the sample game with the `pc98` preset, put `suika-98.exe` plus sample files on a bootable `.hdi`, and play the sample to its end in Neko Project 21/W. Settles the asset-loading question (loose files vs `assets.arc` on DOS) and real image/memory ceilings before anything Jolly-specific is built.

### Phase 1 — Jolly Chapter 1 on local PC-98

Build `convert_pc98.py` (webp in, 640x400 dithered 16-color PNG out), convert two existing scenes, write a minimal `ch01.novel` (two backgrounds, Jolly sprite, `[text]` lines, one `[choose]`, end card; ASCII-first text until glyph safety is proven), pack onto the Phase 0 image, and complete Chapter 1 including the choice locally.

### Phase 2 — same game in the browser

Self-host the WebNP2 player, serve the Phase 1 image over HTTP, and play Chapter 1 via an `hdd=<url>&run=1` link. Record the self-host file list, the user-supplied BIOS story (expected: none needed thanks to ROM-less boot), and any CORS headers cross-origin image URLs require. This page becomes the prototype frontend.

### Phase 3 — chapter swap without rebuilding the world

Author two stub Chapter 2 variants on `.fdi` floppies, attempt a hot swap at the end card through the player's disk UI, and fall back to reboot-with-new-URL if the game cannot re-read mid-session. Lock the contract: one NovelML file per chapter, loaded on transition, nothing fully cached at boot.

### Phase 4 — generated Chapter 2, the full loop

Build the chapter server (choice plus run log in; generated beats, converted art, packed `.fdi` URL out), wire the end card to request through it behind the preview/save interstitial, and play through twice with different Chapter 1 choices to confirm both Chapter 2s differ and complete.

## Validation Plan

- Phase 0: sample VN shows text, background, and a choice, and reaches its ending on local emulation.
- Phase 1: Chapter 1 completes locally; converter outputs and their byte sizes are recorded.
- Phase 2: Chapter 1 completes in the browser identically to local; self-host notes are written down.
- Phase 3: both stub Chapter 2 variants are reachable from a Chapter 1 playthrough; the swap-vs-reboot outcome is recorded.
- Phase 4: two playthroughs with different choices yield two different completable Chapter 2s; generation run is traceable in the run log.

## Risks / Open Questions

- How `suika-98.exe` loads game data on DOS and its image/memory ceilings (settled in Phase 0; blocks all later phases).
- Whether hot floppy swap works mid-session or reboot-with-URL is required (settled in Phase 3; reboot is an acceptable prototype answer).
- Glyph safety of generated text on the PC-98 build (ASCII-first until proven).
- CORS and hosting details for cross-origin disk-image URLs (settled in Phase 2).

## Non-goals

Lookahead pre-generation, fallback-branch caching, audio, save/load across chapters, and mobile layout. The request API, interstitial, and fallback slot must exist as seams, but their full behavior is post-prototype.

## Sources

- https://raw.githubusercontent.com/awemorris/suika3/main/README.md
- https://raw.githubusercontent.com/uraraworks/webnp2/master/README.md
- https://simk98.github.io/np21w/
- https://uraraworks.github.io/WebNP2/?lang=en
