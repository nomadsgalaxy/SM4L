"""Skip the IE10 export-presence check for this exact full-media bootstrap copy.

This does not implement WinINet WebSockets. Original media stays unchanged.
"""
import argparse
import hashlib
from pathlib import Path

SOURCE_SHA256 = {
    'setup.exe': 'c3aeeecdb030e124c74eb9a4897ff08c60122e2ed7bc2058b313c8c4cddb222a',
    'setup_noUAC.exe': 'a10b812fe9ad68085bbc898823706b08d3ddefff0a71910600b2b9f0920fdd31',
}
BRANCH_OFFSET = 0xc307  # setup_noUAC.exe RVA0xcf07, verified against its .text section.


def patched_bytes(data):
    if hashlib.sha256(data).hexdigest() not in SOURCE_SHA256.values():
        raise ValueError('Unsupported installer build; refusing to patch')
    if data[BRANCH_OFFSET:BRANCH_OFFSET + 2] != bytes.fromhex('75 52'):
        raise ValueError('Prerequisite branch does not match')
    # ponytail: one verified media release; inspect and add a separate hash/offset for another build.
    # JNE -> JMP to the same continuation. No return values or networking exports are faked.
    return data[:BRANCH_OFFSET] + bytes([0xeb]) + data[BRANCH_OFFSET + 1:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    if source.name not in SOURCE_SHA256:
        parser.error('Expected full-media setup.exe or setup_noUAC.exe')
    source_data = source.read_bytes()
    if hashlib.sha256(source_data).hexdigest() != SOURCE_SHA256[source.name]:
        parser.error('Filename and supported installer hash do not match')
    output = source.with_name('setup_admin_proton_offline.exe' if source.name == 'setup.exe' else 'setup_proton_offline.exe')
    data = patched_bytes(source_data)
    with output.open('xb') as file:
        file.write(data)
    print(output)
    print('Offline prerequisite workaround only; WinINet WebSocket support is unchanged.')


if __name__ == '__main__':
    main()
