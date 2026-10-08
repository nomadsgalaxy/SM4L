import _paths
from pathlib import Path
import tempfile
from launch_windows_browser import configure

with tempfile.TemporaryDirectory() as directory:
    profile = Path(directory) / 'profile'
    agent = configure(profile, '157.0')
    text = (profile / 'user.js').read_text()
    assert 'Windows NT 10.0; Win64; x64' in agent
    assert 'Firefox/157.0' in agent and 'Linux' not in agent
    assert 'general.platform.override' in text and 'Win32' in text
    assert 'general.oscpu.override' in text
    assert configure(profile, '157.0') == agent
    for version in ['157.0";bad', '', 'Linux']:
        try:
            configure(profile, version)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid version accepted')
    (profile / 'user.js').write_text('// User-owned settings\n')
    try:
        configure(profile, '157.0')
    except ValueError:
        pass
    else:
        raise AssertionError('Foreign profile settings overwritten')
    assert (profile / 'user.js').read_text() == '// User-owned settings\n'
print('Windows profile and unrelated-settings refusal checks passed')
