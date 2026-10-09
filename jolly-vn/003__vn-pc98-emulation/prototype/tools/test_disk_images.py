"""Regression checks for the real PC-98 disk images.

Run: python3 tools/test_disk_images.py
Covers the boot-chain failures hit in the browser:
- boot FD must contain KERNEL.SYS, COMMAND.COM, AUTOEXEC.BAT
- AUTOEXEC must launch SUIKA-98.EXE
- game HDD must contain SUIKA-98.EXE *and* DOS4GW.EXE side by side
  (the DOS/4GW stub in suika-98.exe fails with
  "stub exec failed: no such file or directory for dos4gw.exe"
  when the extender is missing)
- game HDD must NOT contain Chapter 2 (chapter boundary is a disk
  boundary); reboot images must contain exactly their branch file.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def root_names(img: bytes, off: int) -> list[str]:
    bps = struct.unpack_from("<H", img, off + 11)[0]
    reserved = struct.unpack_from("<H", img, off + 14)[0]
    nfats = img[off + 16]
    root_entries = struct.unpack_from("<H", img, off + 17)[0]
    spf = struct.unpack_from("<H", img, off + 22)[0]
    root_off = off + (reserved + nfats * spf) * bps
    names = []
    for i in range(root_entries):
        o = root_off + i * 32
        if img[o] == 0:
            break
        if img[o] == 0xE5:
            continue
        names.append(img[o:o + 11].decode("ascii", "replace").strip())
    return names


def read_root_file(img: bytes, off: int, want_raw: bytes) -> bytes:
    bps = struct.unpack_from("<H", img, off + 11)[0]
    spc = img[off + 13]
    reserved = struct.unpack_from("<H", img, off + 14)[0]
    nfats = img[off + 16]
    root_entries = struct.unpack_from("<H", img, off + 17)[0]
    spf = struct.unpack_from("<H", img, off + 22)[0]
    fat_off = off + reserved * bps
    root_off = fat_off + nfats * spf * bps
    data_off = root_off + root_entries * 32
    fat16 = bps > 512 and root_entries >= 512

    def fat_get(cl: int) -> int:
        if fat16:
            return struct.unpack_from("<H", img, fat_off + cl * 2)[0]
        pos = fat_off + cl + cl // 2
        val = struct.unpack_from("<H", img, pos)[0]
        return (val >> 4) & 0xFFF if cl % 2 else val & 0xFFF

    for i in range(root_entries):
        o = root_off + i * 32
        if img[o] == 0:
            break
        if bytes(img[o:o + 11]) == want_raw:
            cl = struct.unpack_from("<H", img, o + 26)[0]
            size = struct.unpack_from("<I", img, o + 28)[0]
            out = bytearray()
            while 2 <= cl < (0xFFF8 if fat16 else 0xFF8):
                start = data_off + (cl - 2) * bps * spc
                out += img[start:start + bps * spc]
                cl = fat_get(cl)
            return bytes(out[:size])
    raise AssertionError(f"file {want_raw!r} not found")


def main() -> int:
    failures = []
    import re as _re
    _shell = (ROOT / "index.html").read_text()
    _m = _re.search(r"fd1=/disks-real/([^&\"']+)", _shell)
    boot_name = _m.group(1) if _m else "boot-fd.xdf"
    if not (ROOT / "disks-real" / boot_name).exists():
        failures.append(f"shell fd1 names missing file disks-real/{boot_name}")
        boot_name = "boot-fd.xdf"
    boot = (ROOT / "disks-real" / boot_name).read_bytes()
    names = root_names(boot, 0)
    for need in ("KERNEL  SYS", "COMMAND COM", "AUTOEXECBAT"):
        if need not in names:
            failures.append(f"boot FD missing {need} (root: {names})")
    autoexec = read_root_file(boot, 0, b"AUTOEXECBAT").decode("ascii", "replace")
    if "SUIKA-98.EXE" not in autoexec:
        failures.append(f"AUTOEXEC does not launch SUIKA-98.EXE: {autoexec!r}")
    # The DOS/4GW stub looks for DOS4GW.EXE in the root of the *current*
    # drive, not beside the .exe. AUTOEXEC must switch drive + CD to root
    # before launching, or the stub fails even with DOS4GW.EXE present.
    upper = autoexec.upper()
    launch_at = upper.find("SUIKA-98.EXE")
    head = upper[:launch_at] if launch_at >= 0 else ""
    if "C:" not in head or ("CD \\" not in head and "CD\\" not in head):
        failures.append(f"AUTOEXEC must CD to the game drive root before launching: {autoexec!r}")

    # The shell's hdd URL must name a real .thd file: WebNP2 classifies
    # the image by the URL's final path segment, so a cache-busting
    # query string (game.thd?v=...) silently breaks HDD mounting and
    # DOS then cannot find SUIKA-98.EXE. Version the filename instead.
    import re
    shell = (ROOT / "index.html").read_text()
    m = re.search(r"hdd=/disks-real/([^&\"']+)", shell)
    if not m:
        failures.append("index.html has no hdd=/disks-real/... URL")
        hdd_name = "game.thd"
    else:
        hdd_name = m.group(1)
        if not hdd_name.endswith(".thd"):
            failures.append(f"hdd URL filename must end in .thd, got {hdd_name!r}")
        if not (ROOT / "disks-real" / hdd_name).exists():
            failures.append(f"hdd URL names missing file disks-real/{hdd_name}")

    hdd_off = 256 + 8 * 33 * 256
    hdd_path = ROOT / "disks-real" / hdd_name
    if not hdd_path.exists():
        hdd_path = ROOT / "disks-real" / "game.thd"
    hdd = hdd_path.read_bytes()
    names = root_names(hdd, hdd_off)
    for need in ("SUIKA-98EXE", "DOS4GW  EXE", "START   NOV", "MAIN    RAY", "CONFIG  INI"):
        if need not in names:
            failures.append(f"game HDD missing {need} (root: {names})")
    for forbidden in ("CH02-RINNOV", "CH02-WATNOV"):
        if forbidden in names:
            failures.append(f"game HDD must not contain {forbidden} (chapter boundary)")

    for branch, dos in (("ringo", "CH02-RINNOV"), ("wataame", "CH02-WATNOV")):
        gen = sorted((ROOT / "disks-real" / "generated").glob(f"reboot-ch02-{branch}-*.thd"))
        if not gen:
            failures.append(f"no generated reboot image for {branch} (run the chapter API first)")
            continue
        names = root_names(gen[-1].read_bytes(), hdd_off)
        if dos not in names:
            failures.append(f"reboot image for {branch} missing {dos} (root: {names})")
        if "DOS4GW  EXE" not in names:
            failures.append(f"reboot image for {branch} missing DOS4GW.EXE (root: {names})")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("OK: boot FD, game HDD (with DOS4GW.EXE), and reboot images satisfy the boot chain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
