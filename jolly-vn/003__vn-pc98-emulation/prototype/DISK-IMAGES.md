# Disk images: what is not in Git, and how to rebuild it

The emulator disk images are **build outputs** and are no
longer stored in Git. Each `.thd` hard-disk image is a
fixed-size 41,564,416-byte file no matter how little data it
holds, and the feasibility work accumulated dozens of them
(about 2.4 GB of the repository). Removing them takes the
branch from roughly 2.4 GB to roughly 60 MB. Nothing needed
to rebuild them was removed: the engine binary, the game
tree, the packing tools, the FreeDOS template, and every
boot script are committed sources.

## What you need, and the one command that builds it

From the `prototype/` folder:

```
sh tools/rebuild_disks.sh
```

That produces the two shipping images from committed sources
and verifies the asset package while doing so:

| Image | Contents | Built from |
|---|---|---|
| `disks-real/boot-fd-retry.xdf` | FreeDOS(98) boot floppy; AUTOEXEC launches the game from `C:\` up to three times | `vendor/player/freedos/fd98_2hd.xdf` (template) + `build/autoexec-retry.bat`, `build/FDCONFIG.SYS`, `build/HIMEMX.EXE` |
| `disks-real/game-ch1.thd` | Chapter 1 hard disk: `SUIKA-98.EXE`, `ASSETS.ARC`, `CONFIG.INI`, `MAIN.RAY`, `START.NOV`, `DOS4GW.EXE` | `engine/SUIKA3-98.EXE`, `game/` (packed into `assets.arc` by the same script), `vendor/DOS4GW.EXE` |

The rebuilt boot floppy has been checked file-for-file
against the image it replaces. After rebuilding, this
regression check should pass:

```
python3 tools/test_disk_images.py
```

## Chapter 2 images (generated, never committed)

The Chapter 2 floppy and reboot hard disk are per-run outputs
of the chapter server, stamped with a run id, and were never
meant to be archived. Generate fresh ones with:

```
node server.mjs
curl -X POST http://127.0.0.1:4173/api/chapter \
  -H 'Content-Type: application/json' -d '{"choiceId":"ringo"}'
```

(`"wataame"` for the other branch.) Outputs land in
`disks-real/generated/`, and each run is logged in
`data/run-log.jsonl`. The staging trees under `build/gen-*/`
are likewise regenerated on every run.

## Historical images (deleted, not needed)

The dozens of `game-v*.thd`, `boot-fd-v*.xdf`, `sample*.thd`,
and similar images that used to sit in `disks-real/` were
one-off snapshots from boot debugging iterations. They have
no archival value: each was produced by the same
`tools/build_disk.py` invocations shown in
`tools/rebuild_disks.sh`, with a different engine build or
file set substituted. If a specific historical configuration
is ever needed again, rebuild the equivalent from the
commands in that script rather than storing the image.

## Rule for the future

Do not commit disk images. If a new image becomes a shipping
artifact, add its rebuild command to `tools/rebuild_disks.sh`
and describe it in the table above in the same change. Large
upstream archives follow the rule in
`vendor/EXTERNAL-FILES.md` instead.
