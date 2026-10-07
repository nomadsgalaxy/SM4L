import stat
import tempfile
from pathlib import Path
from zipfile import ZipInfo
from prepare_design_install import prepare, safe_members

assert safe_members([ZipInfo('code/bin/example.dll')])
for name in ['../outside', '/absolute', 'code/../../outside', 'C:/outside', 'code\\outside']:
    try:
        safe_members([ZipInfo(name)])
    except ValueError:
        pass
    else:
        raise AssertionError(name)
link = ZipInfo('link')
link.external_attr = (stat.S_IFLNK | 0o777) << 16
try:
    safe_members([link])
except ValueError:
    pass
else:
    raise AssertionError('Symlink accepted')
with tempfile.TemporaryDirectory() as directory:
    data = Path(directory)
    (data / 'solidworks.msi').write_bytes(b'unrecognized build')
    try:
        prepare(data, data / 'install')
    except ValueError:
        pass
    else:
        raise AssertionError('Unverified installer accepted')
    assert not (data / 'install').exists()
    assert not (data / 'solidworks-proton-preextracted.msi').exists()
print('ZIP traversal/symlink and unsupported-build refusal checks passed')
