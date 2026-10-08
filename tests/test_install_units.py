"""Check unit rendering (paths with spaces, % and $), stale-unit removal, and the WineBrowser/menu registration, all in
temporary directories; systemd and the real prefix are never touched."""
import _paths
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
import register_paths as r

ROOT = _paths.ROOT
def run(script, *args, env=None, check=True):
    return subprocess.run(['bash', str(script), *args], capture_output=True, text=True, env=env, check=check)

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    # Rendering from this checkout.
    dest = tmp / 'units'
    (dest).mkdir(); (dest / 'sm4l-old.service').write_text('[Service]\nExecStart=/old\n'); (dest / 'unrelated.service').write_text('x')
    out = run(ROOT / 'bin' / 'install_units.sh', '--dest', str(dest), '--no-systemctl').stdout
    names = sorted(p.name for p in (ROOT / 'units').glob('sm4l-*.service'))
    assert names and all((dest / n).exists() for n in names), out
    assert not (dest / 'sm4l-old.service').exists() and (dest / 'unrelated.service').exists() and 'removed stale sm4l-old.service' in out
    for n in names:
        text = (dest / n).read_text()
        assert '@SM4L_ROOT@' not in text and str(ROOT) in text and 'ExecStart=' in text
    first = {n: (dest / n).read_text() for n in names}
    run(ROOT / 'bin' / 'install_units.sh', '--dest', str(dest), '--no-systemctl')
    assert first == {n: (dest / n).read_text() for n in names}                       # idempotent
    # A checkout path with a space, a percent sign and a dollar sign.
    odd = tmp / 'my checkout 100%$x'
    (odd / 'bin').mkdir(parents=True); shutil.copytree(ROOT / 'units', odd / 'units')
    shutil.copy(ROOT / 'bin' / 'install_units.sh', odd / 'bin' / 'install_units.sh')
    run(odd / 'bin' / 'install_units.sh', '--dest', str(tmp / 'odd-dest'), '--no-systemctl')
    text = (tmp / 'odd-dest' / 'sm4l-spacemouse.service').read_text()
    assert 'ExecStart=/usr/bin/python3 -B "%s/addin/spacemouse.py"' % str(odd.resolve()).replace('%', '%%').replace('$', '$$') in text, text
    # A double quote in the path is refused.
    bad = tmp / 'bad"dir'
    (bad / 'bin').mkdir(parents=True); shutil.copytree(ROOT / 'units', bad / 'units'); shutil.copy(ROOT / 'bin' / 'install_units.sh', bad / 'bin' / 'install_units.sh')
    refused = run(bad / 'bin' / 'install_units.sh', '--dest', str(tmp / 'bad-dest'), '--no-systemctl', check=False)
    assert refused.returncode == 2 and not (tmp / 'bad-dest').exists()

# WineBrowser value edit.
script = '/home/u/SM4L/bin/open_windows_firefox.sh'
base = ['[Software\\\\Wine\\\\Other] 1\n', '"A"="b"\n', '\n', '[Software\\\\Wine\\\\WineBrowser] 2\n', '#time=1\n', '"Browsers"="/old/path.sh"\n', '\n', '[Software\\\\Z] 3\n']
new, changed = r.set_browser(base, script)
assert changed and new[5] == '"Browsers"="%s"\n' % script and new[:5] == base[:5] and new[6:] == base[6:]
assert r.set_browser(new, script) == (new, False)
fresh, changed = r.set_browser(base[:3], script)
assert changed and fresh[-2].startswith('[Software\\\\Wine\\\\WineBrowser]') and fresh[-1] == '"Browsers"="%s"\n' % script
missing, changed = r.set_browser(['[Software\\\\Wine\\\\WineBrowser] 2\n', '#time=1\n', '\n', '[Z]\n'], script)
assert changed and missing[2] == '"Browsers"="%s"\n' % script
assert r.browser_value('/a b/"c"\\d') == '"Browsers"="/a b/\\"c\\"\\\\d"\n'

# Registration end to end with a temp state and menu directory (no wineserver for it: user.reg is edited offline).
with tempfile.TemporaryDirectory() as tmp:
    state = Path(tmp) / 'state'; pfx = state / 'prefix' / 'pfx'; pfx.mkdir(parents=True)
    (pfx / 'user.reg').write_text(''.join(base))
    env = dict(os.environ, SOLIDWORKS_PROTON_STATE=str(state), XDG_DATA_HOME=str(Path(tmp) / 'share'))
    done = subprocess.run([sys.executable, str(ROOT / 'bin' / 'register_paths.py')], env=env, capture_output=True, text=True, check=True).stdout
    assert 'updated in user.reg' in done and str(ROOT / 'bin' / 'open_windows_firefox.sh') in (pfx / 'user.reg').read_text()
    assert 'launch_solidworks.sh' in (Path(tmp) / 'share/applications/SM4L-solidworks.desktop').read_text()
    again = subprocess.run([sys.executable, str(ROOT / 'bin' / 'register_paths.py')], env=env, capture_output=True, text=True, check=True).stdout
    assert 'already correct' in again
    checked = subprocess.run([sys.executable, str(ROOT / 'bin' / 'register_paths.py'), '--check'], env=dict(env, XDG_DATA_HOME=str(Path(tmp) / 'none')), capture_output=True, text=True, check=True).stdout
    assert 'WineBrowser' in checked and not (Path(tmp) / 'none').exists()
print('unit rendering, stale-unit removal, odd checkout paths, WineBrowser and menu registration checks passed')
