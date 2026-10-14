# HF5.9 update: tested checkpoint and experimental Wine patch

On October 13, 2026, the HF4.13 → HF5.9 platform update completed in a copied prefix on the Intel laptop. Launching from the real platform Open button then opened SOLIDWORKS Design Professional for Makers 2026 SP3.0 with an assembly rendered. The original live prefix and shared Proton installation were preserved.

This checkpoint includes installer completion and visible CAD startup. HF5.9 save/reopen, fresh modeling, repeated start/exit stability, full loader/lifecycle/exception regression and desktop replication remain open. The older two-machine checks in [INSTALL.md](INSTALL.md) and [tested-versions.json](tested-versions.json) describe HF4.13. `setup.sh` does not install this Wine patch automatically.

## What changed

| Layer | Failure | Included change |
| --- | --- | --- |
| Wine shell32 | `UnzipInt` fails opening the update ZIP with `hr=S_FALSE` | ZIP-folder NameSpace, enumeration and item/collection CopyHere; bounded extraction with size/CRC validation and temporary-file promotion |
| Wine wininet | HF5.9 uses missing `InternetSetCookieEx2` | Cookie API implementation built on the existing cookie code and an API test |
| Wine ntdll | JS0GROUP cannot initialize the manually mapped JS0PCC image | Real static-TLS registration/release through Wine's existing allocator, plus x64 discovery metadata for the caller's private Windows lookup |
| SM4L directory compatibility | Installer recopies a new stock CATSysTS before dictionary compilation | Exact HF5.9 checksum support in the builder and recopy watcher; unknown builds remain refused |

The Wine changes are in [hf59-compat.patch](../patches/wine/hf59-compat.patch). [The patch README](../patches/wine/README.md) identifies the base and licensing. The TLS self-check is [wine_tls_probe.c](../experiments/wine_tls_probe.c). No vendor binaries, license decisions, authentication payloads, cookies or installed prefixes are included.

## Tested versions and results

- Base runtime: UMU-Proton-10.0-4, with Wine pinned to ValveSoftware/wine commit `b8fdff8e1f855b5276ec4ddca0f31b2792554322`.
- Platform: `V6R2026x.HF5.9`, installed SPlevel `428.6.9`. CAD's product title still says 2026 SP3.0; that title alone does not identify the platform hotfix.
- Shell automation: **483 checks, no failures, 16 existing todo checks**. The actual update ZIP had 254 entries / 209 files, 62,246,620 unpacked bytes, methods 0/8. Every extracted file matched Python zipfile output by SHA256. The real vendor launcher also logged successful extraction.
- WinINet: **1,719 checks passed** after adding InternetSetCookieEx2.
- Synthetic TLS self-check: stock runtime returns 1 because the compatibility entry points are absent; patched runtime returns 0. It checks template bytes, zero-fill, existing and new threads, per-thread isolation, release and null registration refusal.
- Existing ntdll `thread` test: **26 checks, zero failures**. An attempted ntdll `loader` invocation was rejected because that executable has no test with that name; it was not a completed loader regression run.
- Installer: dictionary action returned 0, all four selected components completed, final close returned 0. The restart finished at 21:07:15 EDT and closed at 21:08:29 EDT on October 13.
- CAD: one real Open launch with an assembly rendered, confirmed by the user and a local screenshot. No Windows control was available.

## Why the TLS change was needed

The HF5.9 custom loader inspected ntdll's `.rdata` and `.text` directly. It searched for the private `LdrpHandleTlsData` routine before initializing static TLS for the manually mapped PE image. Successful logged API calls did not establish compatibility with that internal ABI.

The observed caller uses JS0GROUP RVAs `0x8a230` / `0x8a370` for discovery and `0x8a690` for TLS setup; the string `LdrpHandleTlsData` is at RVA `0x1c5df8`. These describe the tested build, not portable offsets for patching another release. The Wine adapter registers actual per-thread data through `alloc_tls_slot` under the loader lock and releases it through `free_tls_slot`. The x64 discovery layout is experimental and needs broader lifecycle/unwind review before upstream submission or routine deployment.

JS0GROUP's earlier `cannot load JS0PCC.dll` and null call were therefore a loader-compatibility failure in this experiment. No vendor licensing code or entitlement result was changed to get through it.

## Source/build workflow

Start with the exact base in a separate source checkout and keep all artifacts in your own state directory. Do not apply the patch to an unknown Wine release.

```bash
export STATE="$HOME/.local/share/solidworks-proton"
export SM4L_ROOT="$PWD"  # run from the SM4L checkout
export WINE_SRC="$STATE/src/proton-wine"

git -C "$WINE_SRC" rev-parse HEAD
# expected: b8fdff8e1f855b5276ec4ddca0f31b2792554322

git -C "$WINE_SRC" apply --check "$SM4L_ROOT/patches/wine/hf59-compat.patch"
git -C "$WINE_SRC" apply "$SM4L_ROOT/patches/wine/hf59-compat.patch"
```

The patch check is for a clean source checkout. The development checkout already contains these changes; don't apply them twice. Wine-generated configure, Vulkan and syscall files are not part of this patch.

The tested build preparation used `autoreconf -fi`, `tools/make_specfiles`, and the Wine Vulkan generator with Vulkan-Docs v1.4.318 `vk.xml` / `video.xml`. The runtime's Vulkan-Headers pin was insufficient for that generation step. Generator changes to committed source files were excluded from the published patch.

Configure a separate build directory for x86_64 PE DLLs with `--enable-win64 --enable-archs=x86_64` and the host dependencies required by that Wine revision. The experimental local build disabled unneeded Unix library integrations; it was not a complete replacement Proton build. From that configured directory:

```bash
make -j8 dlls/shell32/x86_64-windows/shell32.dll \
  dlls/wininet/x86_64-windows/wininet.dll \
  dlls/ntdll/x86_64-windows/ntdll.dll
make -j8 dlls/shell32/tests/x86_64-windows/shell32_test.exe \
  dlls/wininet/tests/x86_64-windows/wininet_test.exe \
  dlls/ntdll/tests/x86_64-windows/ntdll_test.exe
```

Run the matching `shelldispatch`, `internet` and `thread` tests through the isolated 64-bit runtime. Preserve the test output; don't report a missing or rejected test as passed. The bundled zlib uses Z_SOLO and the ZIP implementation supplies its allocation callbacks.

To compile the standalone TLS probe against those Wine headers/import libraries:

```bash
export WINE_BUILD="$STATE/src/build-wine64"
clang -target x86_64-windows -fuse-ld=lld --no-default-config \
  -Wno-pragma-pack -fno-builtin -include stdarg.h -D__WINE_PE_BUILD \
  -I"$WINE_SRC/include" -I"$WINE_SRC/include/msvcrt" -nostdlib \
  -Wl,-entry:mainCRTStartup -Wl,-subsystem:console \
  "$SM4L_ROOT/experiments/wine_tls_probe.c" \
  "$WINE_BUILD/dlls/kernel32/x86_64-windows/libkernel32.a" \
  -o "$STATE/wine-tls-probe.exe"
```

Run the probe in a disposable prefix, using the copied runtime's `files/bin/wine64`. The probe constructs synthetic TLS data and requires no SOLIDWORKS files or account. The test prefix must use the same fsync/esync settings as its server.

## Deploy only into a test copy

1. Save and close CAD normally; verify no `sldworks.exe` remains. Never kill an open CAD or switch its launcher/server with unsaved work.
2. Preserve a backup and create separate prefix and Proton runtime copies. Confirm their resolved paths differ from live. Isolate external user-folder symlinks in the test copy.
3. Disable the copied launcher service before updating so it cannot compete for live port 20250. During the eventual real Open test, run only one launcher on that port and retain a way to restore the live service.
4. Atomically install shell32/wininet only into the test prefix. Clear the `Wine builtin DLL` marker at offset 64 only in those deployed native test copies; otherwise Wine may redirect to the installed builtins. Keep original DLL backups. Never write through a prefix symlink/hardlink into shared Proton.
5. Scope shell32's `native,builtin` override to `AppDefaults\3DEXPERIENCELauncher.exe`. The successful copy retained a wininet `native,builtin` override for the cookie implementation.
6. Atomically replace `files/lib/wine/x86_64-windows/ntdll.dll` only in the isolated runtime. Keep ntdll's builtin marker; do not apply the shell32 deployment transformation to it. Use that runtime consistently for the test launcher, its server and CAD.
7. Run the synthetic TLS probe and matching Wine tests before attempting one real platform Open launch. The product still requires the normal account, role and license handoff.

Known limits: classic single-disk ZIP only, no ZIP64, extraction paths limited to MAX_PATH; x64 TLS discovery only. This repository ships source for review, not a general runtime updater.

## Installer failures and recovery

The tested update archive was `SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF5.9.Windows64.zip`. Its bootstrap hashes matched the existing `setup/patch_offline_installer.py` guard:

- setup.exe: `c3aeeecdb030e124c74eb9a4897ff08c60122e2ed7bc2058b313c8c4cddb222a`.
- setup_noUAC.exe: `a10b812fe9ad68085bbc898823706b08d3ddefff0a71910600b2b9f0920fdd31`.

That helper creates a separately named admin bootstrap, bypassing only the false HttpWebSocketReceive presence prerequisite. It does not implement WebSockets; its modified copy's vendor signature is invalid. A direct no-UAC retry lacked the launcher's elevation pipe context. A direct admin retry without the generated `--multi` input then lacked CAFS download settings. The successful copied-prefix route retained the launcher's actual local component/cache/download input. That JSON contains auth data: never print it, commit it or share raw logs containing its values.

The update recopied CATSysTS. Its HF5.9 stock hash is `1786dbca6b75a66d5cb7156b797135b44a0ccfeaff12780d89a92989175bc559`; all 196 KERNEL32 import names matched the previously supported build. The builder and `--watch-for-recopy` now accept this exact build while preserving refusal for unknown hashes.

Use the existing [directory-compatibility procedure](INSTALL.md#7-install-the-platform). If an existing `.pre-swcompat` backup belongs to an older build, preserve it separately; the helper intentionally refuses a conflicting backup. Never substitute an old patched CATSysTS for a new build. Start the watcher before choosing Restart installation, then verify the dictionary action and final installer close both return 0. DisplayVersion may be updated before an eventual failure.

## Rollback and next checks

Keep the original live prefix/runtime and the test backups until validation is complete. With CAD normally closed, stop only the test units/server and restore the live launcher units. Do not change global runtime symlinks or the live service environment while CAD is open.

Before live deployment, verify HF5.9 save/reopen and modeling, normal exit and restart, threaded TLS lifecycle/unwind behavior, and desktop replication. Then package a guarded runtime deployment and rollback separately. The patch and this checkpoint do not establish long-term stability.
