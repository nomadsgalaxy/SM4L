"""Check the msxml6 override edit, and install/rollback in a throwaway prefix (needs 7z and the KB2957482 package).
Usage: test_install_msxml6.py [PACKAGE]   (default: the winetricks cache; the install part is skipped if it is missing)"""
import _paths
import os, sys, tempfile
from pathlib import Path
import install_msxml6 as m

# Registry edit: add, idempotent, replace a wrong value, create the section, remove only our line.
base = ['[Software\\\\Wine\\\\AppDefaults\\\\sldworks.exe\\\\DllOverrides] 1\n', '#time=1\n', '"comctl32"="native,builtin"\n', '\n',
        '[Software\\\\Wine\\\\X11 Driver] 2\n', '"A"="b"\n']
new, changed = m.add_override(base)
assert changed and new[3] == m.VALUE + '\n' and new[4:] == base[3:]
assert m.add_override(new) == (new, False)
wrong = [l.replace('native,builtin"\n', 'builtin"\n') if l.startswith('"msxml6"') else l for l in new]
fixed, changed = m.add_override(wrong)
assert changed and fixed == new
fresh, changed = m.add_override(base[4:])
assert changed and any(l.startswith(m.SECTION) for l in fresh) and fresh[-1] == m.VALUE + '\n'
assert m.remove_override(new) == (base, True) and m.remove_override(base) == (base, False)
assert m.has_override(new) and not m.has_override(base)

# --check must fail (exit 1) until both the DLLs and the override are in place; setup.sh relies on the exit status.
with tempfile.TemporaryDirectory() as tmp:
    prefix = Path(tmp) / 'prefix' / 'pfx'
    for folder in ('system32', 'syswow64'):
        (prefix / 'drive_c' / 'windows' / folder).mkdir(parents=True)
        (prefix / 'drive_c' / 'windows' / folder / 'msxml6.dll').write_bytes(b'stub')
    (prefix / 'user.reg').write_text(''.join(base))
    assert m.main([str(prefix), '--check']) == 1                                    # nothing installed
    reg = prefix / 'user.reg'; reg.write_text(''.join(m.add_override(base)[0]))
    assert m.main([str(prefix), '--check']) == 1                                    # override only, stub DLLs
    reg.write_text(''.join(base))
    (prefix / 'drive_c' / 'windows' / 'system32' / 'msxml6.dll').write_bytes(b'x')   # still not the pinned file
    assert m.main([str(prefix), '--check']) == 1

# Install / idempotence / rollback in a fake prefix.
pkg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.path.expanduser(f'~/.cache/winetricks/msxml6/{m.PACKAGE}'))
if not pkg.exists():
    print('Override edit checks passed; package not found, install test skipped'); sys.exit(0)
with tempfile.TemporaryDirectory() as tmp:
    prefix = Path(tmp) / 'prefix' / 'pfx'
    for folder in ('system32', 'syswow64'):
        (prefix / 'drive_c' / 'windows' / folder).mkdir(parents=True)
        (prefix / 'drive_c' / 'windows' / folder / 'msxml6.dll').write_bytes(b'stub-' + folder.encode())
    (prefix / 'user.reg').write_text(''.join(base))
    assert m.state_of(prefix) == (False, False)
    assert m.install(prefix, pkg) == 0
    assert m.state_of(prefix) == (True, True) and m.main([str(prefix), '--check']) == 0
    assert m.install(prefix, pkg) == 0                      # already installed: nothing changes
    assert (m.backup_dir(prefix) / 'system32-msxml6.dll').read_bytes() == b'stub-system32'
    try:
        m.install(prefix, pkg.with_name('missing.exe'))
    except SystemExit:
        pass
    assert m.rollback(prefix) == 0
    win = prefix / 'drive_c' / 'windows'
    assert (win / 'system32' / 'msxml6.dll').read_bytes() == b'stub-system32'
    assert (win / 'syswow64' / 'msxml6.dll').read_bytes() == b'stub-syswow64'
    assert not (win / 'system32' / 'msxml6r.dll').exists() and not (win / 'syswow64' / 'msxml6r.dll').exists()
    assert (prefix / 'user.reg').read_text() == ''.join(base)
    bad = Path(tmp) / 'bad.exe'; bad.write_bytes(b'not the package')
    try:
        m.install(prefix, bad)
    except SystemExit as e:
        assert 'SHA256' in str(e)
    else:
        raise AssertionError('Accepted a package with the wrong hash')
print('msxml6 override edit, install, idempotence, rollback and hash refusal checks passed')
