#!/usr/bin/env python3
"""Source-only assertions for old Android boot image generator; not boot validation."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]

def check(ok,label):
    if not ok: raise AssertionError(label)
    print("PASS archived mkbootimg:",label)

try:
    bp=(ROOT/"Android.bp").read_text(encoding="utf-8")
    script=(ROOT/"mkbootimg.py").read_text(encoding="utf-8")
    header=(ROOT/"include/bootimg/bootimg.h").read_text(encoding="utf-8")
    unpack=(ROOT/"unpack_bootimg.py").read_text(encoding="utf-8")
    for target in ('name: "mkbootimg"','name: "unpack_bootimg"','name: "repack_bootimg"','name: "certify_bootimg"'):
        check(target in bp,"archived host Soong "+target)
    check('name: "libmkbootimg_abi_check"' in bp and 'name: "mkbootimg_defaults"' in bp,
          "archived VNDK/Soong defaults differ from AOSP17")
    check("max(args.header_version, filesize(args.dt))" in script,
          "archived PE --dt patch writes DT size in legacy header field")
    check("parser.add_argument('--dt'," in script and "update_sha(sha, args.dt)" in script,
          "archived PE explicit old --dt argument and boot ID hash")
    check("write_padded_file(args.output, args.dt, args.pagesize)" in script,
          "archived PE appends old DT data to boot")
    check("args.header_version > 0 and args.dt != None" in script,
          "archive explicitly rejects mixing --dt with newer header versions")
    check("BOOT_MAGIC" in header and "VENDOR_BOOT_MAGIC" in header,
          "old header definitions include boot and vendor boot image magic")
    check("unpack_boot_image" in unpack and "unpack_vendor_boot_image" in unpack,
          "archive has format-specific extraction tools")
    print("PASS: legacy source inventory only. Not compatible with AOSP17 v4 until proven separately.")
except (AssertionError,OSError) as error:
    print("FAIL:",error,file=sys.stderr)
    sys.exit(1)
