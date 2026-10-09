"""Check that launch_proton.sh creates a fresh prefix with a plain umu-run BEFORE it starts the persistent wineserver (a server
started on an empty prefix overwrites Proton's default registry with a tiny one), and leaves a ready prefix alone."""
import _paths
import json, os, subprocess, tempfile
from pathlib import Path

launcher = (_paths.ROOT / 'bin' / 'launch_proton.sh').resolve()
UMU = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
a = sys.argv[1:]
base = os.environ["CAPTURE"]
if a and a[0].endswith("cmd.exe"):
    Path(base + ".init").write_text(json.dumps({"args": a, "server_started": Path(base + ".server").exists()}))
    if os.environ.get("FAKE_INIT_WRITES", "1") == "1":
        reg = Path(os.environ["WINEPREFIX"]) / "pfx" / "system.reg"
        (Path(os.environ["WINEPREFIX"]) / "pfx" / "drive_c" / "users" / "steamuser").mkdir(parents=True, exist_ok=True)
        reg.write_text("".join("[Software\\\\\\\\Classes\\\\\\\\CLSID\\\\\\\\{%d}] 1\\n" % i for i in range(int(os.environ.get("FAKE_INIT_KEYS", "1")))))
    sys.exit(0)
Path(base + ".umu").write_text(json.dumps({"args": a}))
'''
SERVER = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ["-w"]:
    sys.exit(0)
reg = Path(os.environ["WINEPREFIX"]) / "system.reg"
Path(os.environ["CAPTURE"] + ".server").write_text(json.dumps({"args": sys.argv[1:], "registry_ready_at_start": reg.exists() and b"CLSID" in reg.read_bytes()}))
'''
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    umu = root / 'umu'; umu.write_text(UMU); umu.chmod(0o755)
    proton = root / 'proton'; (proton / 'files/bin').mkdir(parents=True)
    server = proton / 'files/bin/wineserver'; server.write_text(SERVER); server.chmod(0o755)
    exe = root / 'tool.exe'; exe.touch()
    state = root / 'state'; pfx = state / 'prefix' / 'pfx'
    capture = root / 'capture'
    env = dict(os.environ, SM4L_MIN_REG_KEYS='1', UMU_RUN=str(umu), CAPTURE=str(capture), SOLIDWORKS_PROTON_STATE=str(state), PROTONPATH=str(proton),
               SM4L_SPACEMOUSE='0', SM4L_UI_COMPAT='0')
    def seen(suffix): return Path(str(capture) + suffix)
    def reset():
        for s in ('.init', '.server', '.umu'): seen(s).unlink(missing_ok=True)
    def launch(**extra): return subprocess.run([launcher, exe], env=dict(env, **extra), capture_output=True, text=True)

    # 1. Fresh prefix (no system.reg): initialised first, server only afterwards, and it sees the full registry.
    done = launch(); assert done.returncode == 0, done
    init = json.loads(seen('.init').read_text())
    assert init['args'][-3:] == ['cmd.exe', '/c', 'exit 0'][-3:] or init['args'][0].endswith('cmd.exe'), init
    assert init['server_started'] is False
    got = json.loads(seen('.server').read_text())
    assert got['args'] == ['-p'] and got['registry_ready_at_start'] is True
    assert json.loads(seen('.umu').read_text())['args'] == [str(exe)]
    # 2. A ready prefix is left alone: no second initialisation.
    reset(); done = launch(); assert done.returncode == 0 and not seen('.init').exists() and seen('.server').exists()
    # 3. A trivial registry (what an early server leaves behind: no CLSID keys) counts as not ready and is initialised again.
    reset(); (pfx / 'system.reg').write_text('[Software\\\\Wine] 1\n')
    done = launch(); assert done.returncode == 0 and seen('.init').exists()
    assert json.loads(seen('.server').read_text())['registry_ready_at_start'] is True
    # 4. If the initialisation does not produce a registry, no server is started on that prefix and the launcher fails.
    reset(); (pfx / 'system.reg').unlink()
    done = launch(FAKE_INIT_WRITES='0')
    assert done.returncode == 3 and 'not initialised' in done.stderr and not seen('.server').exists() and not seen('.umu').exists()
    # 5. --oneshot never starts the persistent server and does not run the separate initialisation (its own umu-run creates the prefix).
    reset()
    done = subprocess.run([launcher, '--oneshot', exe], env=env, capture_output=True, text=True)
    assert done.returncode == 0 and not seen('.init').exists() and not seen('.server').exists() and seen('.umu').exists()
    # 6. With the real minimum (5000 keys) a registry that has the CLSID key but only a few keys is not ready; a healthy one is.
    reset()
    big = ''.join('[Software\\\\Classes\\\\CLSID\\\\{%d}] 1\n' % i for i in range(6000))
    (pfx / 'system.reg').write_text(big[:big.index('{100}')])
    strict = dict({k: v for k, v in env.items() if k != 'SM4L_MIN_REG_KEYS'}, FAKE_INIT_KEYS='6000')
    done = subprocess.run([launcher, exe], env=strict, capture_output=True, text=True)
    assert done.returncode == 0 and seen('.init').exists()      # about 100 keys: initialised again
    reset(); (pfx / 'system.reg').write_text(big)
    done = subprocess.run([launcher, exe], env=strict, capture_output=True, text=True)
    assert done.returncode == 0 and not seen('.init').exists() and seen('.server').exists()   # 6000 keys: left alone
    # 7. The standard profile folders: a fresh prefix has no Desktop and CAD's Open/Save dialogs crash without it. They are made after the
    #    init (normal and --oneshot), on every launch if missing, and existing entries (including symlinks) are left alone.
    users = pfx / 'drive_c' / 'users'
    wanted = ['steamuser/' + n for n in ('Desktop', 'Documents', 'Downloads', 'Pictures', 'Music', 'Videos')] + ['Public/Desktop', 'Public/Documents']
    import shutil
    shutil.rmtree(pfx); reset()
    done = launch(); assert done.returncode == 0 and all((users / w).is_dir() for w in wanted), [w for w in wanted if not (users / w).is_dir()]
    shutil.rmtree(users / 'steamuser' / 'Desktop'); (users / 'steamuser' / 'Documents').rmdir()
    (users / 'steamuser' / 'Documents').symlink_to('Downloads')                  # a symlink in place of a folder: kept as it is
    reset(); done = launch(); assert done.returncode == 0
    assert (users / 'steamuser' / 'Desktop').is_dir() and (users / 'steamuser' / 'Documents').is_symlink()
    shutil.rmtree(users / 'steamuser' / 'Desktop'); reset(); (pfx / 'system.reg').unlink()
    done = subprocess.run([launcher, '--oneshot', exe], env=env, capture_output=True, text=True)   # --oneshot creates a prefix too
    assert done.returncode == 0 and (users / 'steamuser' / 'Desktop').is_dir()
print('fresh prefix is initialised before the persistent server starts; a ready prefix is left alone')
