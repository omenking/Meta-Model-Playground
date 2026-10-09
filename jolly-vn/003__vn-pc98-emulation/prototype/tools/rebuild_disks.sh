#!/bin/sh
# Rebuild the shipping disk images from committed sources.
#
# Disk images are intentionally NOT stored in Git (they are
# fixed-size 41.5 MB files; see ../DISK-IMAGES.md). Everything
# this script needs is committed: the engine binary, the game
# tree, the tools, and the FreeDOS template in vendor/player/.
set -e
cd "$(dirname "$0")/.."

echo "== Packing game/assets.arc =="
python3 tools/pack_assets.py --out game/assets.arc --root game \
  config.ini start.novel main.ray images system
python3 tools/pack_assets.py --verify game/assets.arc --root game

echo "== Building disks-real/game-ch1.thd (Chapter 1 hard disk) =="
python3 tools/build_disk.py thd --out disks-real/game-ch1.thd \
  --add engine/SUIKA3-98.EXE=SUIKA-98.EXE \
  --add game/assets.arc=ASSETS.ARC \
  --add game/config.ini=CONFIG.INI \
  --add game/main.ray=MAIN.RAY \
  --add game/start.novel=START.NOV \
  --add vendor/DOS4GW.EXE=DOS4GW.EXE

echo "== Building disks-real/boot-fd-retry.xdf (FreeDOS boot floppy) =="
python3 tools/build_disk.py fd --out disks-real/boot-fd-retry.xdf \
  --boot-freedos vendor/player/freedos/fd98_2hd.xdf \
  --add build/autoexec-retry.bat=AUTOEXEC.BAT \
  --add build/FDCONFIG.SYS=FDCONFIG.SYS \
  --add build/HIMEMX.EXE=HIMEMX.EXE

echo
echo "Done. Chapter 2 disks are generated per run by the server:"
echo "  node server.mjs"
echo "  curl -X POST http://127.0.0.1:4173/api/chapter \\"
echo "    -H 'Content-Type: application/json' -d '{\"choiceId\":\"ringo\"}'"
echo "Then open http://localhost:4173/ and play."
