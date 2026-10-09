"""Build the CAD MSI helper (setup/cad_msi_install.c) with the exact commands INSTALL step 8 gives, so a moved or broken source is
caught before an install: it must compile without warnings and link against the Wine import libraries."""
import _paths
import subprocess, tempfile
from pathlib import Path

source = _paths.ROOT / 'setup' / 'cad_msi_install.c'
libs = Path('/usr/lib/wine/x86_64-windows')
assert source.is_file(), source
with tempfile.TemporaryDirectory() as tmp:
    obj, exe = Path(tmp) / 'cad-msi.obj', Path(tmp) / 'cad-msi.exe'
    steps = (['clang', '--target=x86_64-pc-windows-msvc', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-builtin', '-c', str(source), '-o', str(obj)],
             ['lld-link', '/entry:entry', '/subsystem:console', '/nodefaultlib', '/machine:x64', '/out:' + str(exe), str(obj),
              str(libs / 'libkernel32.a'), str(libs / 'libmsi.a')])
    for command in steps:
        done = subprocess.run(command, capture_output=True, text=True)
        assert done.returncode == 0 and not done.stderr.strip(), '%s failed:\n%s' % (command[0], done.stderr[:1500])
    data = exe.read_bytes()
    assert data[:2] == b'MZ' and len(data) > 1000
print('setup/cad_msi_install.c builds with the INSTALL step 8 commands')
