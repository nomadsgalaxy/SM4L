"""Validate the one-byte change against the locally supplied, supported installer."""
import sys
from pathlib import Path
from patch_offline_installer import BRANCH_OFFSET, patched_bytes

if len(sys.argv) != 2:
    raise SystemExit('Usage: test_patch_offline_installer.py MEDIA_1_DIRECTORY')
source = Path(sys.argv[1]) / 'setup_noUAC.exe'
for source in (source, source.with_name('setup.exe')):
    data = source.read_bytes()
    out = patched_bytes(data)
    assert len(out) == len(data)
    assert [i for i, (a, b) in enumerate(zip(data, out)) if a != b] == [BRANCH_OFFSET]
    assert out[BRANCH_OFFSET:BRANCH_OFFSET + 2] == bytes.fromhex('eb 52')
    for bad in (b'', data[:-1], data[:100] + b'!' + data[101:]):
        try:
            patched_bytes(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Accepted an unsupported or altered installer')
print('Both installer patches: exact single-byte change and modified-input refusal passed')
