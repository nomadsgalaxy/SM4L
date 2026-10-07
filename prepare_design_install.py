"""Prepare the verified 2026 SP3.0 ZIP workaround; originals stay unchanged."""
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile

MSI_SHA = 'f0ab874d24fd70842764ef90ca0293406d6c322cd3329f230ce80d564a5b91c4'
ZIP_SHA = '3a5584aa82d821a7426da919b02d309cea1afd7f9e540c3e23a9eab43358ccda'


def safe_members(infos):
    for info in infos:
        name = info.filename
        if (PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
                or '\\' in name or ':' in name or stat.S_ISLNK(info.external_attr >> 16)):
            raise ValueError(f'Unsafe ZIP member: {name}')
    return infos


def prepare(data, install):
    data, install = Path(data), Path(install)
    for name, expected in [('solidworks.msi', MSI_SHA), ('spatialiop.zip', ZIP_SHA)]:
        with (data / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError(f'Unsupported source: {name}')
    target = install / 'spiop/files'
    copy = data / 'solidworks-proton-preextracted.msi'
    if copy.exists():
        raise FileExistsError(copy)
    # ponytail: one verified vendor build; inspect and pin each new release separately.
    with zipfile.ZipFile(data / 'spatialiop.zip') as archive:
        infos = safe_members(archive.infolist())
        root = target.resolve()
        for info in infos:
            if not (target / info.filename).resolve().is_relative_to(root):
                raise ValueError('Existing symlink escapes extraction destination')
        target.mkdir(parents=True, exist_ok=True)
        archive.extractall(target)  # zipfile verifies each file's CRC while extracting.
        for info in infos:
            if not info.is_dir() and (target / info.filename).stat().st_size != info.file_size:
                raise ValueError(f'Incomplete extraction: {info.filename}')
    with (data / 'solidworks.msi').open('rb') as source, copy.open('xb') as output:
        shutil.copyfileobj(source, output)
    print(f'Extracted {len(infos)} entries; created {copy}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: prepare_design_install.py DATA_DIRECTORY INSTALLED_SOLIDWORKS_DIRECTORY')
    prepare(*sys.argv[1:])
