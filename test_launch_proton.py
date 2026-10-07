"""Check launch isolation and argument handling without downloading or running Proton."""
import os
from pathlib import Path
import subprocess
import tempfile

launcher = Path(__file__).with_name('launch_proton.sh').resolve()
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    fake = root / 'umu'
    fake.write_text('#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["CAPTURE"]).write_text(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd(),"prefix":os.environ.get("WINEPREFIX"),"proton":os.environ.get("PROTONPATH"),"nofsync":os.environ.get("PROTON_NO_FSYNC"),"noesync":os.environ.get("PROTON_NO_ESYNC")}))\n')
    fake.chmod(0o755)
    exe = root / 'app with spaces.exe'
    exe.touch()
    capture = root / 'capture.json'
    proton = root / 'proton'
    server = proton / 'files/bin/wineserver'
    server.parent.mkdir(parents=True)
    server.write_text('#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\nPath(os.environ["CAPTURE"]+".server").write_text(json.dumps({"prefix":os.environ["WINEPREFIX"],"fsync":os.environ["WINEFSYNC"],"esync":os.environ["WINEESYNC"],"args":sys.argv[1:]}))\nsys.exit(int(os.environ.get("FAKE_SERVER_EXIT", "0")))\n')
    server.chmod(0o755)
    env = dict(os.environ, UMU_RUN=str(fake), CAPTURE=str(capture), SOLIDWORKS_PROTON_STATE=str(root / 'state'), PROTONPATH=str(proton))
    env.pop('PROTON_NO_FSYNC', None)
    env.pop('PROTON_NO_ESYNC', None)
    subprocess.run([launcher, exe, 'argument with spaces'], env=env, check=True)
    import json
    got = json.loads(capture.read_text())
    assert got == {'args': [str(exe), 'argument with spaces'], 'cwd': str(root), 'prefix': str(root / 'state/prefix'), 'proton': str(proton), 'nofsync': '1', 'noesync': '1'}
    assert json.loads(Path(str(capture)+'.server').read_text()) == {'prefix': str(root / 'state/prefix/pfx'), 'fsync': '0', 'esync': '0', 'args': ['-p']}
    assert len(list((root / 'state/logs').glob('run-*'))) == 1
    env.update(PROTON_NO_FSYNC='0', PROTON_NO_ESYNC='0')
    subprocess.run([launcher, exe], env=env, check=True)
    override = json.loads(capture.read_text())
    assert override['nofsync'] == override['noesync'] == '0'
    assert json.loads(Path(str(capture)+'.server').read_text())['fsync'] == '1'
    env['FAKE_SERVER_EXIT'] = '2'  # Wine uses 2 when another server owns the lock.
    subprocess.run([launcher, exe, 'existing server'], env=env, check=True)
    assert json.loads(capture.read_text())['args'][-1] == 'existing server'
    env['FAKE_SERVER_EXIT'] = '1'
    assert subprocess.run([launcher, exe], env=env, capture_output=True).returncode == 1
    subprocess.run([launcher, '--check'], env=env, check=True)
    assert json.loads(capture.read_text())['args'] == ['--version']
    assert subprocess.run([launcher, root / 'missing.exe'], env=env, capture_output=True).returncode == 2
print('Proton launcher checks passed')
