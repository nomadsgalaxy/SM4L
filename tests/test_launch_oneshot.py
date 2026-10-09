"""Check launch_proton.sh --oneshot: no persistent server is started, the program's exit code comes back, and when a wineserver
already serves the prefix the program runs through Proton's own wine64 instead. Fake umu-run, wineserver and wine64 are used."""
import _paths
import json, os, shutil, subprocess, tempfile
from pathlib import Path

launcher = (_paths.ROOT / 'bin' / 'launch_proton.sh').resolve()
tool = '#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["CAPTURE"]+"{suffix}").write_text(json.dumps({{"args":sys.argv[1:],"prefix":os.environ.get("WINEPREFIX")}}))\nsys.exit(int(os.environ.get("{exit_var}","0")))\n'
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    umu = root / 'umu'; umu.write_text(tool.format(suffix='.umu', exit_var='FAKE_UMU_EXIT')); umu.chmod(0o755)
    proton = root / 'proton'
    (proton / 'files/bin').mkdir(parents=True)
    server = proton / 'files/bin/wineserver'; server.write_text(tool.format(suffix='.server', exit_var='FAKE_SERVER_EXIT')); server.chmod(0o755)
    wine = proton / 'files/bin/wine64'; wine.write_text(tool.format(suffix='.wine', exit_var='FAKE_WINE_EXIT')); wine.chmod(0o755)
    exe = root / 'tool.exe'; exe.touch()
    capture = root / 'capture'
    state = root / 'state'
    env = dict(os.environ, SM4L_MIN_REG_KEYS='1', UMU_RUN=str(umu), CAPTURE=str(capture), SOLIDWORKS_PROTON_STATE=str(state), PROTONPATH=str(proton),
               SM4L_SPACEMOUSE='0', SM4L_UI_COMPAT='0', FAKE_UMU_EXIT='5', FAKE_WINE_EXIT='7')
    def seen(suffix): return Path(str(capture) + suffix)

    # No wineserver for the prefix: umu-run runs the program, no persistent server starts, the exit code comes back.
    done = subprocess.run([launcher, '--oneshot', exe, 'two words'], env=env, capture_output=True, text=True)
    assert done.returncode == 5, done
    assert json.loads(seen('.umu').read_text())['args'] == [str(exe), 'two words']
    assert not seen('.server').exists() and not seen('.wine').exists()

    # A wineserver serves the prefix: the program runs through wine64 against it, umu-run is not used.
    seen('.umu').unlink()
    fake_server = root / 'wineserver'
    shutil.copy('/usr/bin/sleep', fake_server)
    pfx = state / 'prefix' / 'pfx'
    pfx.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([str(fake_server), '600'], env=dict(os.environ, WINEPREFIX=str(pfx)))
    try:
        done = subprocess.run([launcher, '--oneshot', exe, 'two words'], env=env, capture_output=True, text=True)
        assert done.returncode == 7, done
        got = json.loads(seen('.wine').read_text())
        assert got['args'] == [str(exe), 'two words'] and got['prefix'] == str(pfx)
        assert not seen('.umu').exists() and not seen('.server').exists()
    finally:
        process.kill(); process.wait()

    # Not for CAD or its launcher.
    cad = root / 'sldworks.exe'; cad.touch()
    refused = subprocess.run([launcher, '--oneshot', cad], env=env, capture_output=True, text=True)
    assert refused.returncode == 2 and 'short setup commands' in refused.stderr
    # Normal mode (prefix already initialised) still starts the persistent server and execs umu-run.
    (pfx / 'system.reg').write_text('[Software\\\\Classes\\\\CLSID\\\\{x}] 1\n')
    seen('.umu').unlink(missing_ok=True)
    done = subprocess.run([launcher, exe, 'x'], env=env, capture_output=True, text=True)
    assert done.returncode == 5 and json.loads(seen('.server').read_text())['args'] == ['-p']
print('launch_proton.sh --oneshot checks passed')
