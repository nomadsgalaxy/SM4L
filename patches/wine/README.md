# Experimental Wine fixes for the HF5.9 update

`hf59-compat.patch` contains the Wine changes tested on October 13, 2026:

- shell32 ZIP-folder shell automation and extraction, with tests;
- wininet InternetSetCookieEx2, its public declaration/export and API test;
- ntdll static-TLS registration/release with experimental x64 discovery metadata.

Apply only to ValveSoftware/wine commit **b8fdff8e1f855b5276ec4ddca0f31b2792554322**, the Wine base used by UMU-Proton-10.0-4. The patch includes the new ZIP source/header and excludes configure output, generated syscall/Vulkan files, build artifacts, vendor binaries, installed prefixes and authentication data.

Read [the HF5.9 guide](../../docs/HF5.9.md) before building or deploying. The observed checkpoint is installer completion and a rendered CAD assembly in an isolated Intel-laptop copy. It is not a routine live-update mechanism. The TLS discovery layout is x64-specific and needs broader lifecycle/unwind and repeated-start validation. The ZIP implementation excludes ZIP64 and extraction paths beyond MAX_PATH.

## Integrity and checks

`hf59-compat.sha256` records the patch's SHA256. Check it from this directory:

```bash
sha256sum -c hf59-compat.sha256
```

In a clean checkout at the exact pinned Wine commit:

```bash
git apply --check /path/to/SM4L/patches/wine/hf59-compat.patch
```

The source tests are in the patch. The standalone synthetic TLS self-check is [experiments/wine_tls_probe.c](../../experiments/wine_tls_probe.c). Its build command and the observed test counts are in [HF5.9.md](../../docs/HF5.9.md). No prebuilt experimental ntdll is shipped.

## License

The Wine modifications retain the **GNU Lesser General Public License, version 2.1 or later**, as stated in the affected Wine source files. Preserve those notices and the upstream Wine license when redistributing a build. These patch contents are not relicensed by SM4L's GPL notice. See the [pinned upstream Wine COPYING.LIB](https://github.com/ValveSoftware/wine/blob/b8fdff8e1f855b5276ec4ddca0f31b2792554322/COPYING.LIB).
