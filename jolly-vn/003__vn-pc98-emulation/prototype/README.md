> SUPERSEDED: this describes the first (fake) JS renderer. The real-emulation build is documented in README-EMULATION.md and is what index.html now serves.

# Jolly VN — PC-98 Prototype

A playable prototype of the chapter-per-chapter loop from
`../PROTOTYPE.md`: a Jolly visual novel presented as a PC-98 program
(640x400, 16 colors) in a desktop browser tab, where finishing
Chapter 1 produces a Chapter 2 generated on the host from the
player's choices. Two different Chapter 1 choices produce two
different, both completable Chapter 2s.

No emulator source is modified. All generation and packing happen on
the host (`server.mjs`, `tools/`). The guest contract mirrors Suika3:
`suika-98.exe` (Suika3 `pc98` preset, OpenWatcom) plus one NovelML
file per chapter on disk images. This browser build renders those
same NovelML scripts so the loop can be played and verified today
without BIOS ROMs (see BIOS story below).

## Run it

```
cd jolly-vn/003__vn-game-design/prototype
node server.mjs
```

Then open http://localhost:4173/ in a desktop browser. Click the
screen or press Space to advance. At the Chapter 1 treat choice,
pick either treat; the end card requests a generated Chapter 2,
shows the preview/save interstitial, and hot-swaps the new floppy
into FD1 without reloading the page. Play Chapter 2 to THE END,
then use Restart Chapter 1 and pick the other treat to see the
second Chapter 2. Port override: `PORT=8080 node server.mjs`.

Static fallback (no generation): `python3 -m http.server 8000` in
this folder also plays Chapter 1 and the stub chapters; only the
chapter server provides generated Chapter 2s.

## Success criteria mapping

1. **Chapter 1 completable in a browser tab with background art,
   Jolly sprite, text, and a working choice.** `index.html` renders
   at PC-98 aspect (640x400 scaled), backgrounds from
   `assets/bg-pc98/` (16-color dithered PNGs), an on-model Jolly
   sprite (cream yeti, round black eyes, pink blush, closed-mouth
   smile, glowing orb; no eyebrows, no open mouth), typewriter
   dialogue in the black box with pink trim, and one `[choose]`
   with two options (`ringo` / `wataame`) in `chapters/ch01.novel`.
2. **Chapter end delivers a Chapter 2 built from the Chapter 1
   choice; two choices give two different completable Chapter 2s.**
   `POST /api/chapter {choiceId, runLog}` in `server.mjs` generates
   branch NovelML (`ch02-ringo` at the shrine, `ch02-wataame` at
   the lake), packs it into a fresh `.fdi`, and returns its URL.
   Each branch has its own backgrounds, second choice, and two
   endings. Every generation is traced in `data/run-log.jsonl`.
3. **No emulator source modified; generation/packing on the host.**
   The player only fetches disk images by URL. Conversion
   (`tools/convert_pc98.py`) and packing (`tools/pack_disk.py`,
   plus the server's on-demand packer) are host tools.
4. **Transition mechanism demonstrated, not assumed.** See next
   section.

## Chapter transition: hot swap vs reboot (demonstrated)

Both mechanisms are implemented and clickable in the player:

- **Hot floppy swap (primary, works).** At the Chapter 1 end card
  the player fetches the generated `.fdi` URL, parses it, and loads
  its NovelML into the running session with no page reload. The
  FD1 LED flashes amber during the swap and the run log records
  `HOT SWAP: FD1 inserted mid-session`. This works because the
  engine contract is one NovelML file per chapter, re-read on
  transition — nothing chapter-specific is cached at boot.
- **Reboot with a new image URL (fallback, works).** After
  generation the DISK DRIVES panel shows a reboot link of the
  WebNP2 form `/?hdd=disks/boot.hdi.json&fd1=<generated .fdi>&run=1`.
  Opening it reloads the page and boots directly into Chapter 2
  from the FD1 image. This is the shareable-link form and the
  recovery path if a future guest build caches at boot.

Verdict for the prototype: **hot swap is the chapter-boundary
mechanism; reboot-with-URL is retained as fallback and link
format.** On real WebNP2 the equivalent is mounting the new
`.fdi` through the player's disk UI (or a fresh `fd1=` URL); the
game-side requirement is identical — re-read per chapter.

URL parameters (WebNP2 link form): `hdd=<url>`, `fd1=<url>`,
`fd2=<url>`, `run=1`. Example:
`http://localhost:4173/?hdd=disks/boot.hdi.json&run=1`.

## Disk images

Prototype images are JSON so the browser can fetch and inspect
them without DOS tooling; the contract (volume label, file table,
boot chapter) matches the production `.hdi`/`.fdi` layout, where
loose game files plus `suika-98.exe` are packed with DOS tooling
and `suika3-pack` produces `assets.arc` for the Wasm build.

- `disks/boot.hdi.json` — boot image, holds `chapters/ch01.novel`,
  boot chapter `ch01`. Rebuild:
  `python3 tools/pack_disk.py --kind hdi --label BOOT --out disks/boot.hdi.json --file chapters/ch01.novel=chapters/ch01.novel --boot-chapter ch01`
- `disks/ch02-ringo.fdi.json`, `disks/ch02-wataame.fdi.json` —
  Phase 3 stub floppies (same content as `chapters/stub-*.novel`).
- `disks/generated/*.fdi.json` — written by the chapter server on
  demand, one per generation run, named with the run id.

## Asset pipeline

```
generate_scenes.py (.webp) -> tools/convert_pc98.py -> assets/bg-pc98/*.png
  -> chapters/*.novel ([bg] tags) -> tools/pack_disk.py / server packer
  -> disks/*.json -> player (hdd=/fd1= fetch, hot swap or reboot)
```

Convert all scenes (byte sizes printed for ceiling records):

```
python3 tools/convert_pc98.py assets/source/*.webp --out-dir assets/bg-pc98
```

The converter resizes to 640x400 and quantizes to a fixed
16-color PC-9801-style palette with Floyd-Steinberg dithering.
Text stays ASCII-first until glyph safety on the `pc98` build is
proven (see `../research/`).

## Self-host file list (Phase 2 record)

Serve this whole `prototype/` folder. Required at runtime:
`index.html`, `server.mjs` (generation; optional for stubs),
`chapters/`, `disks/` (including `disks/generated/`), `assets/`.
No other files are needed to play. The player is a self-hosted
WebNP2-*style* shell: it reproduces WebNP2's URL-loadable image
contract (`hdd`/`fd1`/`fd2`/`run`) and hot-swap interaction
without bundling the upstream WASM emulator.

## BIOS / user-supplied files story (Phase 2 record)

Expected for the production WebNP2 + `suika-98.exe` path: **the
user supplies their own PC-98 BIOS/font ROM dump**; ROMs are never
redistributed, and WebNP2's ROM-less FreeDOS(98) boot covers DOS
but not every BIOS expectation. This browser prototype needs **no
BIOS and no user-supplied files** — the NovelML renderer stands in
for `suika-98.exe` so reviewers can verify the loop immediately.
Local authentic testing remains Neko Project 21/W with the user's
own ROMs (Phase 0).

## CORS notes (Phase 2 record)

Disk-image URLs are fetched cross-origin in production hosting, so
image hosts must send `Access-Control-Allow-Origin: *` (the
chapter server does this for every response). Same-origin hosting
(this prototype's default) needs no extra headers.

## Phase mapping

- Phase 0 (stock engine boots locally): specified, not executed
  here — needs the Suika3 SDK + OpenWatcom + Neko Project 21/W on
  a desktop with user ROMs. The loose-files-vs-`assets.arc` and
  memory-ceiling answers are recorded as open in `../PROTOTYPE.md`
  and do not block this loop prototype.
- Phase 1 (Jolly Chapter 1): done — converter, two-plus converted
  backgrounds in use, `ch01.novel` (backgrounds, sprite, `[text]`,
  one `[choose]`, end card), completable in the player.
- Phase 2 (same game in the browser): done in WebNP2-style form —
  play via `?hdd=...&run=1`; self-host list, BIOS story, and CORS
  notes are recorded above.
- Phase 3 (chapter swap): done — both stub Chapter 2 floppies are
  reachable (Stub FD buttons, FD2 fallback), hot swap and reboot
  both demonstrated; contract locked to one NovelML per chapter.
- Phase 4 (generated Chapter 2, full loop): done — chapter server
  generates, converts (pre-converted branch art), packs, serves;
  end card requests through the preview/save interstitial
  (`Save .fdi` downloads the image); two playthroughs with
  different choices yield different completable Chapter 2s, each
  traced in `data/run-log.jsonl`.

## Seams kept for post-prototype

Request API (`POST /api/chapter`), preview/save interstitial, and
the FD2 fallback slot exist as seams. Full model-backed generation
(replacing the host templates), lookahead pre-generation,
fallback-branch caching, audio, save/load across chapters, and
mobile layout are non-goals per `../PROTOTYPE.md`.

## Layout

```
index.html          player (screen, drives, interstitial, run log)
server.mjs          static host + POST /api/chapter generator/packer
chapters/           ch01.novel, stub-ch02-*.novel, generated-*.novel
tools/              convert_pc98.py, pack_disk.py
disks/              boot.hdi.json, stub .fdi.json, generated/
assets/source/      original .webp scenes (from 001, wave v2)
assets/bg-pc98/     converted 640x400 16-color PNGs
data/run-log.jsonl  one JSON line per generation run
```
