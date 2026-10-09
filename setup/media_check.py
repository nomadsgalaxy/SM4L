#!/usr/bin/env python3
"""Check the extracted vendor media and the patched offline installer, so setup.sh does not report a step as done while the
copy is still running or while a file is partial.
Usage: media_check.py MEDIA_1 media [--allow-pruned] | patch | hashes
  media    setup.exe must have the pinned SHA256, and every file the vendor's own manifest (0data/MediaContent.xml) lists must
           exist in its numbered folder (the media is folders 1..7 next to each other; MEDIA_1 is folder 1), with the file
           count and total size of the release this repo supports. --allow-pruned skips those checks (the media may have been
           trimmed after the install finished).
  patch    setup_admin_proton_offline.exe must be byte for byte what patch_offline_installer.py makes from setup.exe.
  hashes   also verify the SHA256 of every manifest file (reads all of the media: slow, about 28 GB).
Exit 0 when the check passes; otherwise 1, with the reason on stderr."""
import hashlib, sys
import xml.etree.ElementTree as ET
from pathlib import Path
import patch_offline_installer as patcher

MANIFEST = Path('0data') / 'MediaContent.xml'
EXPECTED_FILES = 575            # files the manifest of the supported release lists, over its 7 folders
EXPECTED_BYTES = 28567415757    # and their total size (the unpacked ZIP is 28,567,505,049 bytes with the few files outside the manifest)

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()

def manifest_files(media):
    """[(path on disk, expected sha256)] from the vendor manifest. The n-th <CD> element is folder n next to MEDIA_1
    (which is folder 1). Raises FileNotFoundError / ET.ParseError if the manifest is unusable."""
    root = ET.parse(media / MANIFEST).getroot()
    out = []
    for number, cd in enumerate(root.iter('CD'), 1):
        out += [(media.parent / str(number) / f.get('path').lstrip('/'), f.get('hash')) for f in cd.iter('File') if f.get('path')]
    return out

def check_setup(media):
    setup = media / 'setup.exe'
    if not setup.is_file():
        return 'setup.exe is missing'
    if sha256(setup) != patcher.SOURCE_SHA256['setup.exe']:
        return 'setup.exe does not have the pinned SHA256 (partial copy or another build)'
    return None

def check_media(media, allow_pruned=False):
    problem = check_setup(media)
    if problem or allow_pruned:
        return problem
    try:
        files = manifest_files(media)
    except (FileNotFoundError, ET.ParseError) as error:
        return '%s is missing or unreadable (%s)' % (MANIFEST.as_posix(), error)
    missing = [p for p, _ in files if not p.is_file()]
    if missing:
        return '%d of %d files the vendor manifest lists are missing (the copy is not finished?), for example %s' % (len(missing), len(files), missing[0])
    if len(files) != EXPECTED_FILES:
        return 'the manifest lists %d files, expected %d (another media release?)' % (len(files), EXPECTED_FILES)
    size = sum(p.stat().st_size for p, _ in files)
    if size != EXPECTED_BYTES:
        return 'the manifest files add up to %d bytes, expected %d (a file is partial or altered?)' % (size, EXPECTED_BYTES)
    return None

def check_hashes(media):
    for path, want in manifest_files(media):
        if sha256(path) != want:
            return 'SHA256 mismatch: %s' % path
    return None

def check_patch(media):
    problem = check_setup(media)
    if problem:
        return problem
    target = media / 'setup_admin_proton_offline.exe'
    if not target.is_file():
        return 'setup_admin_proton_offline.exe is missing'
    if target.read_bytes() != patcher.patched_bytes((media / 'setup.exe').read_bytes()):
        return 'setup_admin_proton_offline.exe is not the expected patched copy of setup.exe (partial or altered)'
    return None

def main(argv):
    if len(argv) < 2 or argv[1] not in ('media', 'patch', 'hashes'):
        sys.exit(__doc__)
    media = Path(argv[0])
    if argv[1] == 'media':
        problem = check_media(media, '--allow-pruned' in argv)
    elif argv[1] == 'patch':
        problem = check_patch(media)
    else:
        problem = check_media(media) or check_hashes(media)
    if problem:
        print('media_check: ' + problem, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
