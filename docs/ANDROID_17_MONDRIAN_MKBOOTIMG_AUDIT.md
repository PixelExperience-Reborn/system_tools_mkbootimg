# P1 — boot image / vendor_boot v4 / Android 17 / mondrian

Date: 2026-11-04. Source-compatibility and **synthetic image host checks** only; this is **not** an installed boot image for mondrian.

## Source comparison and original PE history

- PixelExperience-Reborn `system_tools_mkbootimg`, archived `seventeen` HEAD `e83b7edced84312d13f346b9b129dc6bb9ec1956`; this head is a 2016 legacy add-`--dt` patch atop older Android upstream history, **not an AOSP17 product implementation**.
- Historical PE commit `e83b7edc`, "mkbootimg: add support for --dt": changes legacy boot header's version/DT-size field to `max(args.header_version, filesize(args.dt))`; adds the `--dt` input, hashes it and writes the DT blob into the old boot image. This is tied to older Qualcomm boot image conventions and can corrupt modern header interpretation if transplanted wholesale.
- Official Android17 r1 `platform/system/tools/mkbootimg` **tree `79c702136b6587fe4d2097a462c64db9fbd49204`**, `Android.bp` blob `51d4488682da5fc5e95d8442163c9b82c7673839`: https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/tags/android-17.0.0_r1/ .
- Official AOSP17 `mkbootimg.py` uses `--header_version` (supports v0–v4), `--dtb` for supported modern DTB placement, `--vendor_boot`, `--vendor_ramdisk` and `--vendor_ramdisk_fragment`, plus separate `unpack_bootimg`, `repack_bootimg`, GKI certification and tests. The old explicit `--dt` is absent, and modern v4 boot and vendor_boot headers must not have their version field replaced by the size of a DT. Note: Python argparse can resolve abbreviated option prefixes; the absence of a declared `--dt` **does not itself prove the CLI rejects that token** — the **semantics and output format** must be tested.
- The old Soong `Android.bp` includes `libmkbootimg_abi_headers`/`libmkbootimg_abi_check` VNDK and `mkbootimg_defaults`; official Android17 `Android.bp` exposes `bootimg_headers`, standalone `mkbootimg`/`unpack_bootimg`/`repack_bootimg`/`certify_bootimg`, with `mkbootimg_test`. Do not replace the newer build graph with old VNDK defaults.

## Native PE-Reborn mondrian bring-up constraints

The **existing LF52406 mondrian + sm8450-common LineageOS-derived tree is a hardware reference only.** Its `BoardConfigCommon.mk` defines `BOARD_BOOT_HEADER_VERSION := 4`, `BOARD_MKBOOTIMG_ARGS := --header_version $(BOARD_BOOT_HEADER_VERSION)`, `BOARD_INCLUDE_DTB_IN_BOOTIMG := true`, `BOARD_DTBOIMG_PARTITION_SIZE`, `BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE`, and `BOARD_AVB_ENABLE := true`. **These are historical configuration observations, NOT reviewed Android17-native PE product settings.** Cross-check real device partition metadata, boot/vendor_boot layout, recovery ramdisk, DTB, DTBO and kernel vendor_dlkm against stock images and a known good reproducible build; do not assume the old `BOARD_INCLUDE_DTB_IN_BOOTIMG` and other flags can be copied unchanged.

**Security concern in the reference board config:** it includes paths under `external/avb/test/data/testkey_rsa2048.pem` and sets `BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3`. These are test and boot-verification-related settings, not a production signing policy. Do **not** transfer this configuration into a release product by default. Independent key custody, verified boot chain, rollback indexes and OTA migration need explicit security review. Do not publish private signing keys.

A standalone AnyKernel zip success is not evidence that the kernel/DTBO/modules are correctly integrated into a GKI boot/vendor_boot partition. Follow native Android17 product build and test gates separately.

## Required test gates

1. [x] Historical legacy `--dt` header patch and affected hash/data layout identified.
2. [x] Official AOSP17 source tree/version, Soong, boot header and vendor ramdisk architecture identified.
3. [ ] Historical source inventory CI check for legacy DT behavior passed.
4. [ ] **Execute actual official AOSP17 r1 tools** against synthetic boot v4 and vendor_boot v4 (including vendor ramdisk fragment + DTB), unpack and byte-compare kernel, ramdisk, fragment, DTB, bootconfig. This is not bootloader validation.
5. [ ] Verify official `mkbootimg_test`, Python source API and actual Soong host build as part of full Android17 workspace.
6. [ ] Author independent PE-Reborn mondrian/sm8450-common device trees; verify actual stock image header, DTBO IDs, vendor boot ramdisk, partition sizes, AVB and rollback.
7. [ ] Build complete Android17 boot/recovery/OTA, test live boot/unlock/FBE and CTS/VTS/device compatibility. **No physical mondrian testing has occurred.**

**Decision:** staged manifest keeps official `platform/system/tools/mkbootimg` and official `system/libufdt` tools. No old PE `--dt` patch and no LineageOS product inheritance.
