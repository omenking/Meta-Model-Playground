"""Build REAL PC-98 disk images (no JSON fakes).

Formats follow WebNP2's own src/api/fat.ts (inspected locally):
- FD raw: PC-98 2HD, 1024 B/sector x 8 x 77 cyl x 2 heads, FAT12
  (BPB identical to WebNP2 createFormattedFd).
- .fdi: 4096-byte header, LE32 header size at +8, LE32 FDD size at +12,
  then the raw FD image (WebNP2 openDiskImage).
- .thd (T98 HDD): 256-byte header (LE16 cylinders at +0), 8 surfaces x
  33 sectors x 256 B, partition from cylinder 1, FAT16 with 2048-byte
  logical sectors (WebNP2 createFormattedHdd). IPL is signature-only:
  boot DOS from FD, use the HDD as data drive C:.

Includes a small FAT12 reader to lift KERNEL.SYS / COMMAND.COM out of
the bundled FreeDOS(98) fd98_2hd.xdf (GPLv2+, see WebNP2 repo).

Usage:
  python3 tools/build_disk.py fd  --out disks-real/boot-fd.fdi --boot-freedos vendor/webnp2-src/public/freedos/fd98_2hd.xdf --add AUTOEXEC.BAT=build/autoexec.bat
  python3 tools/build_disk.py thd --out disks-real/game.thd --add-dir game=.
  python3 tools/build_disk.py fdi --out disks-real/ch02.fdi --add ch02-ringo.novel=game/ch02-ringo.novel
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

FD_BYTES = 1024 * 8 * 77 * 2  # 1,261,568


def to83(name: str) -> bytes:
    if "." in name:
        base, ext = name.rsplit(".", 1)
    else:
        base, ext = name, ""
    raw = (base.upper()[:8].ljust(8) + ext.upper()[:3].ljust(3)).encode("ascii", "replace")
    assert len(raw) == 11
    return raw


class FatVol:
    def __init__(self, img: bytearray, off: int, bps: int, spc: int, reserved: int,
                 nfats: int, root_entries: int, spf: int, fat16: bool):
        self.img, self.off, self.bps, self.spc = img, off, bps, spc
        self.reserved, self.nfats, self.root_entries, self.spf = reserved, nfats, root_entries, spf
        self.fat16 = fat16
        self.bytes_per_cluster = bps * spc
        self.fat_off = off + reserved * bps
        self.root_off = self.fat_off + nfats * spf * bps
        self.root_bytes = root_entries * 32
        self.data_off = self.root_off + self.root_bytes
        self.next_free = 2

    def fat_get(self, cl: int) -> int:
        if self.fat16:
            return struct.unpack_from("<H", self.img, self.fat_off + cl * 2)[0]
        pos = self.fat_off + cl + cl // 2
        val = struct.unpack_from("<H", self.img, pos)[0]
        return (val >> 4) & 0xFFF if cl % 2 else val & 0xFFF

    def fat_set(self, cl: int, val: int) -> None:
        for f in range(self.nfats):
            base = self.fat_off + f * self.spf * self.bps
            if self.fat16:
                struct.pack_into("<H", self.img, base + cl * 2, val)
            else:
                pos = base + cl + cl // 2
                cur = struct.unpack_from("<H", self.img, pos)[0]
                cur = (cur & 0xF00F) | ((val & 0xFFF) << 4) if cl % 2 else (cur & 0xF000) | (val & 0xFFF)
                struct.pack_into("<H", self.img, pos, cur)

    def cluster_off(self, cl: int) -> int:
        return self.data_off + (cl - 2) * self.bytes_per_cluster

    def alloc_chain(self, nbytes: int) -> list[int]:
        n = max(1, (nbytes + self.bytes_per_cluster - 1) // self.bytes_per_cluster) if nbytes else 0
        if n == 0:
            return []
        chain = list(range(self.next_free, self.next_free + n))
        self.next_free += n
        for i, cl in enumerate(chain):
            self.fat_set(cl, chain[i + 1] if i + 1 < len(chain) else (0xFFFF if self.fat16 else 0xFFF))
        return chain

    def write_data(self, chain: list[int], data: bytes) -> None:
        for i, cl in enumerate(chain):
            chunk = data[i * self.bytes_per_cluster:(i + 1) * self.bytes_per_cluster]
            off = self.cluster_off(cl)
            self.img[off:off + len(chunk)] = chunk

    def dir_entries(self, cluster: int | None):
        """Yield (offset, raw11, attr, cluster, size) for a dir (None=root)."""
        if cluster is None:
            start, size = self.root_off, self.root_bytes
            region = [(start + i * 32) for i in range(size // 32)]
        else:
            region = []
            cl = cluster
            while 2 <= cl < (0xFFF8 if self.fat16 else 0xFF8):
                base = self.cluster_off(cl)
                region.extend(base + i * 32 for i in range(self.bytes_per_cluster // 32))
                cl = self.fat_get(cl)
        for off in region:
            first = self.img[off]
            if first == 0x00:
                yield ("free-end", off)
                return
            if first == 0xE5:
                continue
            yield ("entry", off)

    def find(self, cluster: int | None, raw11: bytes):
        for kind, off in self.dir_entries(cluster):
            if kind == "free-end":
                return None
            if bytes(self.img[off:off + 11]) == raw11:
                return off
        return None

    def free_slot(self, cluster: int | None) -> int:
        for kind, off in self.dir_entries(cluster):
            if kind == "free-end":
                return off
        raise RuntimeError("directory full")

    def ensure_dir(self, cluster: int | None, name: str) -> int:
        raw = to83(name)
        found = self.find(cluster, raw)
        if found is not None:
            return struct.unpack_from("<H", self.img, found + 26)[0]
        chain = self.alloc_chain(self.bytes_per_cluster)
        off = self.free_slot(cluster)
        self.img[off:off + 11] = raw
        self.img[off + 11] = 0x10
        struct.pack_into("<H", self.img, off + 26, chain[0])
        struct.pack_into("<I", self.img, off + 28, 0)
        # . and ..
        base = self.cluster_off(chain[0])
        self.img[base:base + 11] = b".          "
        self.img[base + 11] = 0x10
        struct.pack_into("<H", self.img, base + 26, chain[0])
        self.img[base + 32:base + 43] = b"..         "
        self.img[base + 43] = 0x10
        struct.pack_into("<H", self.img, base + 32 + 26, cluster or 0)
        return chain[0]

    def add_file(self, path: str, data: bytes) -> None:
        parts = [p for p in path.replace("\\", "/").split("/") if p and p != "."]
        cluster: int | None = None
        for part in parts[:-1]:
            cluster = self.ensure_dir(cluster, part)
        raw = to83(parts[-1])
        chain = self.alloc_chain(len(data))
        self.write_data(chain, data)
        off = self.free_slot(cluster)
        self.img[off:off + 11] = raw
        self.img[off + 11] = 0x20
        struct.pack_into("<H", self.img, off + 26, chain[0] if chain else 0)
        struct.pack_into("<I", self.img, off + 28, len(data))


def make_fd_blank(boot_sector: bytes | None = None) -> tuple[bytearray, FatVol]:
    img = bytearray(FD_BYTES)
    bps, spc, reserved, nfats, root_entries, spf, media, total = 1024, 1, 1, 2, 192, 2, 0xFE, 1232
    if boot_sector:
        img[0:1024] = boot_sector[:1024]
    else:
        img[0], img[1], img[2] = 0xEB, 0xFE, 0x90
    struct.pack_into("<H", img, 11, bps)
    img[13] = spc
    struct.pack_into("<H", img, 14, reserved)
    img[16] = nfats
    struct.pack_into("<H", img, 17, root_entries)
    struct.pack_into("<H", img, 19, total)
    img[21] = media
    struct.pack_into("<H", img, 22, spf)
    struct.pack_into("<H", img, 24, 8)
    struct.pack_into("<H", img, 26, 2)
    img[510], img[511] = 0x55, 0xAA
    vol = FatVol(img, 0, bps, spc, reserved, nfats, root_entries, spf, fat16=False)
    for f in range(nfats):
        base = vol.fat_off + f * spf * bps
        img[base], img[base + 1], img[base + 2] = media, 0xFF, 0xFF
    return img, vol


def make_thd_blank() -> tuple[bytearray, FatVol]:
    surfaces, spt, cyls, phys = 8, 33, 615, 256
    bpc = surfaces * spt * phys
    img = bytearray(256 + cyls * bpc)
    struct.pack_into("<H", img, 0, cyls)
    ipl = 256
    img[ipl:ipl + 4] = bytes([0xEB, 0x0A, 0x90, 0x90])
    img[ipl + 4:ipl + 8] = b"IPL1"
    img[ipl + phys - 2], img[ipl + phys - 1] = 0x55, 0xAA
    entry = 256 + phys
    img[entry], img[entry + 1] = 0xA1, 0x91
    struct.pack_into("<H", img, entry + 6, 1)
    struct.pack_into("<H", img, entry + 10, 1)
    struct.pack_into("<H", img, entry + 14, cyls - 1)
    img[entry + 16:entry + 32] = b"WebNP2          "
    lbps, spc, reserved, nfats, root_entries, media = 2048, 2, 1, 2, 512, 0xF8
    part_cyls = cyls - 1
    total = (part_cyls * bpc) // lbps
    root_secs = (root_entries * 32) // lbps
    spf = 1
    while True:
        data_secs = total - reserved - nfats * spf - root_secs
        need = -(-((data_secs // spc + 2) * 2) // lbps)
        if need <= spf:
            break
        spf = need
    p = 256 + bpc  # partition at cylinder 1
    img[p:p + 3] = bytes([0xEB, 0xFE, 0x90])
    img[p + 3:p + 11] = b"NEC  6.2"
    struct.pack_into("<H", img, p + 11, lbps)
    img[p + 13] = spc
    struct.pack_into("<H", img, p + 14, reserved)
    img[p + 16] = nfats
    struct.pack_into("<H", img, p + 17, root_entries)
    struct.pack_into("<H", img, p + 19, total)
    img[p + 21] = media
    struct.pack_into("<H", img, p + 22, spf)
    struct.pack_into("<H", img, p + 24, spt)
    struct.pack_into("<H", img, p + 26, surfaces)
    struct.pack_into("<I", img, p + 28, bpc // lbps)
    img[p + 38] = 0x29
    img[p + 43:p + 54] = b"NO NAME    "
    img[p + 54:p + 62] = b"FAT16   "
    img[p + 510], img[p + 511] = 0x55, 0xAA
    vol = FatVol(img, p, lbps, spc, reserved, nfats, root_entries, spf, fat16=True)
    for f in range(nfats):
        base = vol.fat_off + f * spf * lbps
        img[base:base + 4] = bytes([media, 0xFF, 0xFF, 0xFF])
    return img, vol


def read_fat12_root(img: bytes) -> dict[str, bytes]:
    bps = struct.unpack_from("<H", img, 11)[0]
    reserved = struct.unpack_from("<H", img, 14)[0]
    nfats = img[16]
    root_entries = struct.unpack_from("<H", img, 17)[0]
    spf = struct.unpack_from("<H", img, 22)[0]
    fat_off = reserved * bps
    root_off = fat_off + nfats * spf * bps
    data_off = root_off + root_entries * 32

    def chain(cl: int):
        out = []
        while 2 <= cl < 0xFF8:
            out.append(cl)
            pos = fat_off + cl + cl // 2
            val = struct.unpack_from("<H", img, pos)[0]
            cl = (val >> 4) & 0xFFF if cl % 2 else val & 0xFFF
        return out

    files = {}
    for i in range(root_entries):
        off = root_off + i * 32
        if img[off] == 0:
            break
        if img[off] == 0xE5 or img[off + 11] & 0x08:
            continue
        name = img[off:off + 11].decode("ascii", "replace")
        cl = struct.unpack_from("<H", img, off + 26)[0]
        size = struct.unpack_from("<I", img, off + 28)[0]
        data = b"".join(img[data_off + (c - 2) * bps: data_off + (c - 1) * bps] for c in chain(cl))
        files[name] = data[:size]
    return files


def add_specs(vol: FatVol, specs: list[str], add_dirs: list[str]) -> None:
    for spec in specs:
        src_raw, _, dst = spec.partition("=")
        src = Path(src_raw)
        vol.add_file(dst or src.name, src.read_bytes())
        print(f"  + {dst or src.name} ({src.stat().st_size} B)")
    for spec in add_dirs:
        src_raw, _, dst_prefix = spec.partition("=")
        base = Path(src_raw)
        for f in sorted(base.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(base))
                vol.add_file(f"{dst_prefix}/{rel}" if dst_prefix and dst_prefix != "." else rel, f.read_bytes())
                print(f"  + {rel} ({f.stat().st_size} B)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build real PC-98 .fdi/.thd images.")
    ap.add_argument("kind", choices=["fd", "thd", "fdi"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--add", action="append", default=[], metavar="SRC=DST")
    ap.add_argument("--add-dir", action="append", default=[], metavar="SRC=DSTPREFIX")
    ap.add_argument("--boot-freedos", default=None, help="fd98_2hd.xdf to lift kernel/command/boot sector from.")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.kind == "thd":
        img, vol = make_thd_blank()
        add_specs(vol, args.add, args.add_dir)
        out.write_bytes(bytes(img))
    else:
        boot_sector, boot_files = None, []
        if args.boot_freedos:
            raw = Path(args.boot_freedos).read_bytes()
            boot_sector = raw[:1024]
            files = read_fat12_root(raw)
            print(f"FreeDOS image files: {sorted(files)}")
            for want, dos_name in (("KERNEL  SYS", "KERNEL.SYS"), ("COMMAND COM", "COMMAND.COM")):
                if want not in files:
                    print(f"error: {want} not in FreeDOS image", file=sys.stderr)
                    return 1
                boot_files.append((dos_name, files[want]))
        img, vol = make_fd_blank(boot_sector)
        for name, data in boot_files:  # kernel first, as DOS loaders expect
            vol.add_file(name, data)
            print(f"  + {name} ({len(data)} B) [FreeDOS, GPLv2+]")
        add_specs(vol, args.add, args.add_dir)
        if args.kind == "fdi":
            header = bytearray(4096)
            struct.pack_into("<I", header, 8, 4096)
            struct.pack_into("<I", header, 12, len(img))
            out.write_bytes(bytes(header) + bytes(img))
        else:
            out.write_bytes(bytes(img))
    print(f"wrote {out} ({out.stat().st_size} B, kind={args.kind})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
