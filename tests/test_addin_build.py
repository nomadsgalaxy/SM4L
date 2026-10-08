"""Build every variant of the add-in source with the exact commands spacemouse.py (and so the bridge units) use, and fail on
any compiler or linker message. Catches declaration-order and unused-code errors before a unit does."""
import _paths
import subprocess, sys, tempfile
from pathlib import Path
import spacemouse

source = _paths.ROOT / 'addin' / 'spacemouse-view.c'
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    for kind, link_kind, name in (('exe', 'exe', 'helper.exe'), ('addin', 'addin', 'spacemouse.dll'), ('ui-addin', 'addin', 'ui-compat.dll')):
        obj, out = tmp / (kind + '.obj'), tmp / name
        for command in (spacemouse.compile_command(source, obj, kind), spacemouse.link_command(obj, out, link_kind)):
            done = subprocess.run(command, capture_output=True, text=True)
            assert done.returncode == 0 and not done.stderr.strip(), '%s failed:\n%s' % (command[0], done.stderr[:1500])
        assert out.stat().st_size > 10000, name
print('all add-in variants (helper exe, SpaceMouse add-in, UI add-in) compile and link with the units\' commands')
