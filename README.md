# SM4L — Solidworks Makers For Linux

We got **SOLIDWORKS Design Professional for Makers 2026 SP3.0** running on an Arch Linux x86_64 laptop through UMU and Proton. On October 7, 2026, Anthony created a cube and chamfered it after we fixed a startup crash and disabled Enhanced graphics performance.

[Download the same installer from Linux](docs/DOWNLOAD.md), then [follow the replication guide](docs/REPLICATE.md) on the desktop. It records the actual installation route, commands, source hashes, registry settings and rollback steps. [The investigation record](docs/FINDINGS.md) explains why each fix exists and which experiments we dropped. [checkpoint.json](checkpoint.json) records the tested versions and evidence.

This is a working laptop setup with a replication guide, not a tested unattended installer. A fresh desktop prefix is the next test. Embedded browser elements still flash. Save/reopen and SpaceMouse support have not been verified.

The repository contains our compatibility code and our own `swcompat.dll` proxy. Get the SOLIDWORKS media, Microsoft prerequisites and Proton from their original sources. Use your own Makers account and assigned license. Vendor payloads, installed prefixes, cookies, launch tickets and crash dumps are excluded.

The recorded installer selection was W4Y Ultimate, but the running CAD window identifies itself as Professional for Makers. We did not uninstall and reinstall between the license error and successful launch. That mismatch was a hypothesis, not an established cause or a reason to bypass licensing.

## What's here

| Files | Purpose |
| --- | --- |
| `launch_proton.sh` | Dedicated prefix, disabled fsync/esync, host Wine server and a larger file-descriptor budget |
| `patch_offline_installer.py` | Verified copy of the installer with the false IE10 export-presence guard skipped |
| `rtl_name_match.c`, `swcompat.dll`, directory-compat scripts | Real missing Unicode/DOS wildcard matcher for the vendor dictionary compiler |
| `prepare_design_install.py`, `cad-msi-experiment.c` | Verified Spatial InterOp extraction and the exact CAD MSI installation experiment |
| Firefox scripts | Dedicated Windows-identifying profile and prefix-specific browser routing |
| `patch_header_layout.py` | Version-pinned, prefix-local null `HDM_LAYOUT` guard |
| `*_probe.c`, `test_*.py` | Reproductions and checks for the actual failures and patches |

Run the checks listed at the end of the replication guide before applying patches to a matching installation. A hash refusal means stop and inspect the new build; do not remove the guard.
