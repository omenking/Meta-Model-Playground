# Real PC-98 emulation build (replaces the fake renderer)

The first prototype in this folder was a JavaScript imitation: it
parsed Suika-like tags itself and used JSON files as fake disks.
That was wrong against `../PROTOTYPE.md`. This build follows the
document literally: a genuine PC-98 program runs inside a browser
tab, and finishing Chapter 1 produces a Chapter 2 generated on the
host from the player's choice.

## What is real now

- **Emulator:** WebNP2 (Neko Project II kai compiled to WASM),
  self-hosted in `player/`, built from upstream source
  (`vendor/webnp2-src`). The NP2kai core is **unmodified**; the
  only local changes are URL/config plumbing in the player shell
  (drive-type pairing so an HDD image mounts, and `mem`/`clk`
  parameters). No emulator source behavior is changed.
- **Guest program:** `SUIKA-98.EXE` — the Suika3 engine compiled
  from upstream source with the `pc98` preset (OpenWatcom), with
  a small set of documented reliability patches described below.
  It runs under the DOS/32A extender (`vendor/DOS4GW.EXE`, see
  Licensing). The official prebuilt `vendor/suika-98.exe` is kept
  for reference but is **not** what boots: see "Why the engine is
  rebuilt" below.
- **Disks:** real FAT images built by `tools/build_disk.py`:
  `disks-real/boot-fd-retry.xdf` (FreeDOS(98) kernel + FreeCOM
  lifted from the bundled GPLv2+ `fd98_2hd.xdf`; its AUTOEXEC
  switches to `C:\`, sets `DOS32A=/DOSBUF:64`, and launches
  `SUIKA-98.EXE -4` up to three times), and
  `disks-real/game-ch1.thd` (T98 HDD: `SUIKA-98.EXE`,
  `ASSETS.ARC`, `CONFIG.INI`, `MAIN.RAY`, `START.NOV`,
  `DOS4GW.EXE` — deliberately no Chapter 2 on it).
- **Boot:** ROM-less. NP2kai's built-in BIOS-compatible routine
  plus the bundled font replaces real BIOS/font ROMs; no ROMs
  are distributed. Boot is from FD with the HDD as data drive C:.
- **Display:** the engine's GDC driver (`-4`) renders 640x400 in
  4 planar bitplanes. Colors are quantized by fixed thresholds,
  so art takes on a dithered 16-color look; that is the PC-98
  driver's real output, not a filter applied by the shell. The
  emulator is run at `clk=32` (CPU clock multiplier): at lower
  multipliers the same software is simply too slow to play.
- **Input:** the PC-98 HAL reads the keyboard only (a mouse is
  never polled), so play is: **Enter** advances text; at a
  choice, **← / →** points at an option and **Enter** confirms.
- **Shell UI separation:** `index.html` puts every control
  (generation buttons, links, run log) outside the emulator
  frame. Inside the frame, the engine alone draws background,
  sprite, message box, name plate, and choice buttons. The
  backgrounds contain no UI (see the salvage note below).

## Why the engine is rebuilt (and what is patched)

The official prebuilt engine cannot be used unattended in this
emulator: the DOS/DPMI path corrupts loads nondeterministically.
Observed across identical boots of the same disk: DOS/32A
sometimes applies LE fixups and sometimes dies with
`DOS/32A fatal (4005): unrecognized fixup data` (an anchored
RAM diff showed partially-applied `+0x10` fixup deltas);
config lines arrive garbled (e.g. a `0x00` byte replacing a `.`
inside a key — proven by hex dump, not inference), which the
stock parser reports as unknown/missing keys; the `assets.arc`
entry table gets poisoned so existing files "cannot open"; and
corrupted PNG bytes can spin libpng's inflate indefinitely.
DOS-side `COPY` + download-compare proved the disk images and
FAT writes are byte-identical, so the corruption is in the
read/load path, not in our images.

The fix strategy is retry-and-verify at every layer, in
`engine/SUIKA3-98.EXE` (source: upstream Suika3 `pc98` preset):

1. Boot floppy AUTOEXEC launches the engine up to 3 times
   (absorbs the DOS32A load lottery).
2. `hal_main` retries script bootstrap up to 8 times (a fresh
   Noct VM re-reads `main.ray` each attempt).
3. Config load requires two consecutive byte-identical reads
   before parsing, tolerates unknown/duplicate keys, and
   retries the whole load up to 8 times.
4. The `assets.arc` entry table is validated after decoding
   (printable NUL-terminated names, in-bounds size/offset) and
   re-read up to 8 times.
5. File loads loop short reads and retry whole files up to
   8 times; PNG buffers are checked chunk-by-chunk (CRC32)
   *before* libpng sees them, and failed decodes reload and
   retry up to 8 times.
6. VM tag/API registration is retried until it reads back
   (lost registrations previously surfaced as
   `Tag "config" not found` after the first frame).
7. PC-98 cursor keys are mapped from the codes the BIOS
   actually delivers (`0x0B/0x0A/0x08/0x0C`); upstream compared
   against `0x100|scancode`, which a byte-wise `getch()` can
   never produce, so arrow-key choice selection was dead.

No emulator code is patched anywhere. The tradeoff is boot
time: a clean boot takes roughly one to three minutes, most of
it decoding the first background at emulated speed.

## UI / screen separation (the double-overlay fix)

Source scenes were finished screenshots with the dialogue box,
name plate, text, choice list, and Jolly bust baked in, and the
old player drew the same UI again. Fixed in layers:

- `tools/separate_assets.py` produces clean scene-only
  backgrounds (`game/images/bg/*.png`, 640x400, no UI/bust/text)
  and a separate transparent Jolly sprite (`game/images/ch/`).
  The salvaged backgrounds are salvage quality: art occluded by
  the baked bust is unrecoverable without regeneration
  (prompts in `game/CLEAN-ASSET-PROMPTS.md`).
- The game (`game/start.novel`, `game/ch02-*.novel`) is written
  in the real Suika3 NovelML dialect (`[bg file=]`,
  `[ch left=]`, `[text name= text=]`,
  `[choose name= text1= value1=]`, `[if]`/`[goto]`/`[label]`,
  `[load file=]`), with 8.3 DOS names (`CH02-RIN.NOV`).
- Because DOS cannot open paths that break 8.3 limits
  (`system/message/msgbox-hide.anime`), game files ship inside
  `assets.arc` (the engine's own package format, packed by
  `tools/pack_assets.py`); loose `CONFIG.INI`/`MAIN.RAY`/
  `START.NOV` also sit on the HDD root.

## Chapter flow (demonstrated, not assumed)

1. Open http://localhost:4173/ and play Chapter 1 in the
   emulator. It ends at a choice (apple candy / cotton candy),
   plays the matching branch text, then shows the end card.
2. Generate the matching Chapter 2 in the side panel.
   `POST /api/chapter` stamps the branch script with the run id
   and packs two real images (logged in `data/run-log.jsonl`):
   a data floppy `.xdf` holding `CH02-RIN.NOV`/`CH02-WAT.NOV`,
   and a reboot `.thd` whose `assets.arc` has that chapter as
   `start.novel`.
3. **Hot swap (verified):** mount the floppy in the emulator's
   FDD2 slot and press Enter. Chapter 1's
   `[load file="B:/CH02-RIN.NOV"]` resolves from drive B: in the
   running session — no reboot — and Chapter 2 starts.
4. **Reboot (verified):** open the generated reboot link; the
   emulator boots a hard disk that starts directly in
   Chapter 2, and the chapter plays to its
   "Chapter 2 complete" text.

## Verified vs unproven

Verified headlessly in a real browser driving this exact
player and these exact disk images (screenshots + on-screen
text reads, this session):

- Chapter 1 boots unattended to the matsuri background with
  Jolly sprite, name plate, message box, and all four texts;
  the choice UI appears and both branches (apple / cotton
  candy) play to the Chapter 2 end card.
- The generated apple-candy Chapter 2 boots directly from its
  reboot disk and completes (shrine → wish → rooftop →
  "Chapter 2 complete - apple-candy branch").
- The generated cotton-candy Chapter 2 likewise boots from
  its reboot disk and completes (lake → skip a stone → ramen
  shop → "Chapter 2 complete - cotton-candy branch").
- The hot swap works: with Chapter 1 at the end card, inserting
  the generated floppy into FDD2 and pressing Enter loads
  Chapter 2 (shrine scene) in the same session.
- `python3 tools/test_disk_images.py` passes (boot chain,
  DOS4GW.EXE placement, chapter-boundary rules).

Known limitations:

- Boot is slow (1–3 minutes) and relies on the retry layers;
  an individual attempt can still fail and be absorbed.
- When a chapter's script ends, the engine exits to the DOS
  prompt (the boot floppy then spends its remaining retries
  relaunching the game). This is serviceable for a prototype
  but is not a polished end screen.
- Sprite/background colors are heavily posterized by the GDC
  driver's thresholds; Jolly reads much redder than her source
  art. Legibility is good; fidelity is 16-color-authentic.
- Save/load, audio, and mobile layout are non-goals per
  `../PROTOTYPE.md` and are not implemented.

## Licensing

- No BIOS or font ROMs are distributed; the player boots
  ROM-less on NP2kai's BIOS-compatible routine.
- FreeDOS(98) kernel/FreeCOM: GPLv2+ (bundled upstream image).
- `vendor/DOS4GW.EXE` is the open-source SUNSYS DOS/32A
  extender renamed to DOS4GW.EXE (a documented drop-in for
  DOS/4GW programs; license in `vendor/DOS32A-LICENSE.txt`).
  The engine's stub requires an extender by that name; every
  game disk packs it. Redistribution follows the DOS/32A
  license terms.
- Suika3 engine: upstream source, zlib-style license (see the
  source tree); this build adds the reliability patches listed
  above. WebNP2/NP2kai: upstream terms (see `vendor/`).

> **Missing files?** A fresh clone runs as-is. Two build-time
> items (the 197 MB Suika3 SDK archive and the upstream WebNP2
> source checkout) are intentionally not in Git; see
> [`vendor/EXTERNAL-FILES.md`](vendor/EXTERNAL-FILES.md) for
> exactly what they are, their SHA-256, and how to fetch them.

## Rebuild commands

Disk images are not stored in Git (see
[`DISK-IMAGES.md`](DISK-IMAGES.md) for the full list of what
was removed and why). Rebuild the shipping images from
committed sources with:

```
sh tools/rebuild_disks.sh   # assets.arc + boot floppy + Chapter 1 HDD

# Regression check + run:
python3 tools/test_disk_images.py
node server.mjs   # http://localhost:4173/
```

To rebuild the engine itself (OpenWatcom + CMake pc98 preset,
then stub graft):

```
cmake --preset pc98 && cmake --build build-pc98
python3 /tmp/graftfix.py build-pc98/suika3.exe engine/SUIKA3-98.EXE
```
