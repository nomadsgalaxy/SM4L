import _paths
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
# An existing preextracted MSI (for example from a cache copied from another machine) is refused up front with a message that says
# what to do, and is neither read, overwritten nor deleted.
import prepare_design_install as module
with tempfile.TemporaryDirectory() as directory:
    data = Path(directory)
    keep = data / 'solidworks-proton-preextracted.msi'
    keep.write_bytes(b'from another machine')
    try:
        prepare(data, data / 'install')
    except FileExistsError as error:
        assert 'move it aside' in str(error) and str(keep) in str(error) and 'never overwrites or deletes' in str(error)
    else:
        raise AssertionError('Existing preextracted MSI accepted')
    assert keep.read_bytes() == b'from another machine' and not (data / 'install').exists()
    done = __import__('subprocess').run([__import__('sys').executable, str(Path(module.__file__)), str(data), str(data / 'install')], capture_output=True, text=True)
    assert done.returncode == 1 and 'move it aside' in done.stderr and 'Traceback' not in done.stderr
print('ZIP traversal/symlink, unsupported-build and existing-copy refusal checks passed')
