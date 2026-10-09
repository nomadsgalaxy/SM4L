"""Check launch isolation and argument handling without downloading or running Proton."""
import _paths
import os
from pathlib import Path
import subprocess
import tempfile

launcher = (_paths.ROOT/'bin'/'launch_proton.sh').resolve()
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    fake = root / 'umu'
    fake.write_text('#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\na=sys.argv[1:]\nif a and a[0].endswith("cmd.exe"):\n reg=Path(os.environ["WINEPREFIX"])/"pfx"/"system.reg"\n reg.parent.mkdir(parents=True,exist_ok=True)\n reg.write_text("[Software\\\\\\\\Classes\\\\\\\\CLSID\\\\\\\\{x}] 1\\n")\n sys.exit(0)\nPath(os.environ["CAPTURE"]).write_text(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd(),"prefix":os.environ.get("WINEPREFIX"),"proton":os.environ.get("PROTONPATH"),"nofsync":os.environ.get("PROTON_NO_FSYNC"),"noesync":os.environ.get("PROTON_NO_ESYNC")}))\n')
    fake.chmod(0o755)
    exe = root / 'app with spaces.exe'
    exe.touch()
    capture = root / 'capture.json'
    proton = root / 'proton'
    server = proton / 'files/bin/wineserver'
    server.parent.mkdir(parents=True)
    server.write_text('#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\nif sys.argv[1:]==["-w"]: sys.exit(0)\nPath(os.environ["CAPTURE"]+".server").write_text(json.dumps({"prefix":os.environ["WINEPREFIX"],"fsync":os.environ["WINEFSYNC"],"esync":os.environ["WINEESYNC"],"args":sys.argv[1:],"launch_lock_inherited":Path("/proc/self/fd/9").exists()}))\nsys.exit(int(os.environ.get("FAKE_SERVER_EXIT", "0")))\n')
    server.chmod(0o755)
    env = dict(os.environ, SM4L_MIN_REG_KEYS='1', UMU_RUN=str(fake), CAPTURE=str(capture), SOLIDWORKS_PROTON_STATE=str(root / 'state'), PROTONPATH=str(proton), SM4L_SPACEMOUSE="0", SM4L_UI_COMPAT="0")
    env.pop('PROTON_NO_FSYNC', None)
    env.pop('PROTON_NO_ESYNC', None)
    subprocess.run([launcher, exe, 'argument with spaces'], env=env, check=True)
    import json
    got = json.loads(capture.read_text())
    assert got == {'args': [str(exe), 'argument with spaces'], 'cwd': str(root), 'prefix': str(root / 'state/prefix'), 'proton': str(proton), 'nofsync': '1', 'noesync': '1'}
    assert json.loads(Path(str(capture)+'.server').read_text()) == {'prefix': str(root / 'state/prefix/pfx'), 'fsync': '0', 'esync': '0', 'args': ['-p'], 'launch_lock_inherited': False}
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
    env['FAKE_SERVER_EXIT']='0'
    cad=Path(env['SOLIDWORKS_PROTON_STATE'])/'prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS Apps 2026/SOLIDWORKS/sldworks.exe'
    cad.parent.mkdir(parents=True,exist_ok=True);cad.touch()
    wrapper=launcher.with_name('launch_solidworks.sh')
    # A running CAD process or concurrent launch must stop before server startup.
    import fcntl
    gate = root/'pgrep'
    gate.write_text('#!/bin/sh\nexit "${FAKE_CAD_RUNNING:-1}"\n')
    gate.chmod(0o755)
    env['PATH'] = str(root)+os.pathsep+os.environ['PATH']
    server_capture = Path(str(capture)+'.server')
    server_capture.unlink(missing_ok=True)
    env['FAKE_CAD_RUNNING'] = '0'
    blocked = subprocess.run([wrapper],env=env,capture_output=True,text=True)
    assert blocked.returncode == 1 and 'already running' in blocked.stderr
    assert not server_capture.exists()
    env['FAKE_CAD_RUNNING'] = '1'
    with (Path(env['SOLIDWORKS_PROTON_STATE'])/'cad-run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        blocked = subprocess.run([wrapper],env=env,capture_output=True,text=True)
        assert blocked.returncode == 1 and 'already in progress' in blocked.stderr
        assert not server_capture.exists()
    vendor = root/'SWXDesktopLauncher.exe'
    vendor.touch()
    # A vendor client releases its gate before spawning long-lived children.
    check_lock = root/'check-vendor-lock'
    check_lock.write_text('#!/usr/bin/env python3\nimport fcntl,os\nfrom pathlib import Path\nwith (Path(os.environ["SOLIDWORKS_PROTON_STATE"])/"cad-run.lock").open("a") as f: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\n')
    check_lock.chmod(0o755)
    subprocess.run([launcher,vendor],env=dict(env,UMU_RUN=str(check_lock)),check=True)
    subprocess.run([wrapper,'part with spaces.SLDPRT'],env=env,check=True)
    assert json.loads(capture.read_text())['args']==[str(cad),'part with spaces.SLDPRT']
    # Exercise automatic bridge startup without connecting to hardware.
    hook = root/'nohup'
    hook.write_text('#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\np=Path(os.environ["CAPTURE"]);p.with_suffix(".bridge").write_text(json.dumps({"args":sys.argv[1:],"server_started":Path(str(p)+".server").exists()}))\n')
    hook.chmod(0o755)
    env['PATH'] = str(root)+os.pathsep+os.environ['PATH']
    env['SM4L_SPACEMOUSE'] = '1'
    Path(str(capture)+'.server').unlink()
    subprocess.run([wrapper], env=env, check=True)
    import time
    for attempt in range(100):
        if capture.with_suffix('.bridge').exists():
            break
        time.sleep(.01)
    bridge = json.loads(capture.with_suffix('.bridge').read_text())
    assert bridge['server_started']
    assert bridge['args'] == ['python3', '-B', str(_paths.ROOT/'addin'/'spacemouse.py')]
    env.update(SM4L_SPACEMOUSE='0', SM4L_UI_COMPAT='1')
    capture.with_suffix('.bridge').unlink()
    subprocess.run([wrapper], env=env, check=True)
    for attempt in range(100):
        if capture.with_suffix('.bridge').exists(): break
        time.sleep(.01)
    ui = json.loads(capture.with_suffix('.bridge').read_text())
    assert ui['server_started']
    assert ui['args'] == ['python3', '-B', str(_paths.ROOT/'addin'/'spacemouse.py'), '--ui-only']
    data = root/'menu with spaces'
    env['XDG_DATA_HOME'] = str(data)
    subprocess.run(['python3', str(launcher.with_name('install_desktop.py'))], env=env, check=True)
    entry = data/'applications/SM4L-solidworks.desktop'
    assert f'Exec="{wrapper}"' in entry.read_text()
    assert 'Name=SOLIDWORKS for Makers' in entry.read_text()
    from install_desktop import desktop_entry
    assert '%%' in desktop_entry(Path('/tmp/100%/launch.sh'))
    import shutil
    if shutil.which('desktop-file-validate'):
        subprocess.run(['desktop-file-validate', str(entry)], check=True)
print('Proton launcher and CAD menu checks passed')
