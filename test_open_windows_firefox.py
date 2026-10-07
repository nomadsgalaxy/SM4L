import os
from pathlib import Path
import subprocess
import tempfile

script = Path(__file__).with_name('open_windows_firefox.sh').resolve()
with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    state = home / 'state with spaces'
    profile = state / 'browser-windows-firefox'
    profile.mkdir(parents=True)
    (profile / 'user.js').write_text('// test profile')
    client = home / '.local/share/umu/steamrt3/pressure-vessel/bin/steam-runtime-launch-client'
    client.parent.mkdir(parents=True)
    client.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    client.chmod(0o755)
    env = dict(os.environ, HOME=str(home), SOLIDWORKS_PROTON_STATE=str(state))
    url = 'https://example.3ds.com/?ticket=a&next=b#dashboard:test'
    result = subprocess.run(['bash', str(script), url], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['--host', '--', '/usr/bin/firefox', '--profile', str(profile), '--new-tab', url]
    assert subprocess.run(['bash', str(script)], env=env, capture_output=True).returncode == 2
    (profile / 'user.js').unlink()
    assert subprocess.run(['bash', str(script), url], env=env, capture_output=True).returncode == 2
print('Browser routing preserves URL arguments and refuses missing profile.')
