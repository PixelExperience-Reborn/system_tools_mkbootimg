#!/usr/bin/env python3
"""Execute stock AOSP17 mkbootimg/unpack_bootimg v4 on harmless synthetic data.

This is a *host-format regression*, not a bootloader/AVB/Soong certification.
No signing keys, vendor blobs, real kernel images or device partitions are used.
"""
from pathlib import Path
import subprocess
import struct
import sys
import tempfile

OFFICIAL_TREE = "79c702136b6587fe4d2097a462c64db9fbd49204"


def command(*args, expect_success=True):
    run = subprocess.run(list(map(str, args)), capture_output=True, text=True,
                         check=False, timeout=45)
    if expect_success and run.returncode:
        raise AssertionError(f"failed ({run.returncode}): {args}\n"
                             f"stdout: {run.stdout[-1800:]}\nstderr: {run.stderr[-1800:]}")
    if not expect_success and run.returncode == 0:
        raise AssertionError(f"expected rejection: {args}")
    return run


def main():
    if len(sys.argv) != 2:
        raise ValueError("usage: verify_official_mkbootimg_v4.py <tagged-source-checkout>")
    src = Path(sys.argv[1]).resolve()
    tree = command("git", "-C", src, "rev-parse", "HEAD^{tree}").stdout.strip()
    assert tree == OFFICIAL_TREE, f"unexpected upstream tree {tree}"
    bp = (src / "Android.bp").read_text(encoding="utf-8")
    mkcode = (src / "mkbootimg.py").read_text(encoding="utf-8")
    for target in ("bootimg_headers", "mkbootimg", "unpack_bootimg",
                   "repack_bootimg", "certify_bootimg", "mkbootimg_test"):
        assert f'name: "{target}"' in bp, target
    assert 'name: "libmkbootimg_abi_check"' not in bp
    assert "parser.add_argument('--dt'," not in mkcode
    assert "parser.add_argument('--dtb'," in mkcode
    assert "Boot header version {args.header_version} not supported" in mkcode
    assert "write_vendor_boot_header(args)" in mkcode
    print("PASS: official Android17 exact Git tree, Soong and boot/v4 logic")

    with tempfile.TemporaryDirectory(prefix="a17-mkbootimg-") as directory:
        wd = Path(directory)
        files = {
            "kernel": b"synthetic-test-kernel-image-DO-NOT-FLASH" * 31,
            "ramdisk": b"synthetic-test-ramdisk-DO-NOT-FLASH" * 7,
            "vendor_ramdisk": b"synthetic-vendor-fragment-DO-NOT-FLASH" * 5,
            "dtb": b"synthetic-dtb-not-a-real-device-tree" * 5,
            "bootconfig": b"androidboot.test.synthetic=1\n",
        }
        for name, content in files.items():
            (wd / name).write_bytes(content)
        boot = wd / "boot.img"
        vendor_boot = wd / "vendor_boot.img"
        make = src / "mkbootimg.py"
        extract = src / "unpack_bootimg.py"
        command(
            sys.executable, make,
            "--header_version", "4",
            "--pagesize", "4096",
            "--kernel", wd / "kernel",
            "--ramdisk", wd / "ramdisk",
            "--output", boot,
            "--vendor_boot", vendor_boot,
            "--dtb", wd / "dtb",
            "--vendor_bootconfig", wd / "bootconfig",
            "--ramdisk_type", "platform",
            "--ramdisk_name", "synthetic",
            "--vendor_ramdisk_fragment", wd / "vendor_ramdisk",
        )
        boot_data = boot.read_bytes()
        vendor_data = vendor_boot.read_bytes()
        assert boot_data[:8] == b"ANDROID!", "boot image magic"
        assert vendor_data[:8] == b"VNDRBOOT", "vendor boot image magic"
        assert struct.unpack_from("<I", boot_data, 40)[0] == 4, "boot v4 header"
        assert struct.unpack_from("<I", vendor_data, 8)[0] == 4, "vendor boot v4 header"
        print(f"PASS: official mkbootimg executed, v4 boot={len(boot_data)} "
              f"vendor_boot={len(vendor_data)} bytes")

        output_boot = wd / "unpacked-boot"
        output_vendor = wd / "unpacked-vendor"
        command(sys.executable, extract, "--boot_img", boot, "--out", output_boot)
        command(sys.executable, extract, "--boot_img", vendor_boot, "--out", output_vendor)
        for source, extracted in (
            ("kernel", output_boot / "kernel"),
            ("ramdisk", output_boot / "ramdisk"),
            ("vendor_ramdisk", output_vendor / "vendor_ramdisk00"),
            ("dtb", output_vendor / "dtb"),
            ("bootconfig", output_vendor / "bootconfig"),
        ):
            actual = extracted.read_bytes()
            assert actual == files[source], f"{source} round-trip mismatch"
        print("PASS: unpacked kernel, ramdisk, vendor fragment, DTB and bootconfig byte-identical")

        invalid = command(sys.executable, make, "--header_version", "5",
                          "--kernel", wd / "kernel", "--output", wd / "invalid.img",
                          expect_success=False)
        assert "not supported" in invalid.stderr.lower(), invalid.stderr[-900:]
        print("PASS: incompatible boot header v5 rejected rather than silently emitted")

    print("HOST ONLY: no actual kernel/DTB, bootloader verification, AVB keys, FBE, Android17 Soong or mondrian test")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print("FAIL:", error, file=sys.stderr)
        sys.exit(1)
