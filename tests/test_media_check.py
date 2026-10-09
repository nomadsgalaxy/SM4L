"""Check the media and patched-installer checks on a fake media tree (setup.exe gets a made-up pinned hash for the test)."""
import _paths
import hashlib, tempfile
from pathlib import Path
import media_check as mc
import patch_offline_installer as patcher

def make_setup():
    data = bytearray(b'\x00' * (patcher.BRANCH_OFFSET + 64))
    data[patcher.BRANCH_OFFSET:patcher.BRANCH_OFFSET + 2] = bytes.fromhex('75 52')
    return bytes(data)

with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / '2').mkdir()
    media = Path(tmp) / '1'; media.mkdir()
    setup = make_setup()
    patcher.SOURCE_SHA256['setup.exe'] = hashlib.sha256(setup).hexdigest()     # the real pin belongs to the vendor file
    (media / 'setup.exe').write_bytes(setup)
    for name, body in (('CAFS/a.dsa', b'a'), ('CAFS/b.dsa', b'bb'), ('1.txt', b'x')):
        (media / name).parent.mkdir(parents=True, exist_ok=True); (media / name).write_bytes(body)
    (Path(tmp) / '2' / 'two.dsa').write_bytes(b'cc')   # a file of the second folder
    (media / '0data').mkdir()
    entries = ''.join('<File hash="%s" path="/%s"/>' % (hashlib.sha256((media / n).read_bytes()).hexdigest(), n) for n in ('CAFS/a.dsa', 'CAFS/b.dsa', '1.txt'))
    two = '<File hash="%s" path="/two.dsa"/>' % hashlib.sha256(b'cc').hexdigest()
    (media / '0data' / 'MediaContent.xml').write_text('<Media><CDs><CD>%s</CD><CD>%s</CD></CDs></Media>' % (entries, two))
    mc.EXPECTED_FILES, mc.EXPECTED_BYTES = 4, 1 + 2 + 1 + 2          # the pins of the real release do not apply to this fake tree

    assert mc.check_media(media) is None and mc.check_hashes(media) is None
    assert mc.main([str(media), 'media']) == 0 and mc.main([str(media), 'hashes']) == 0
    # A file that is not there yet (copy still running) fails, unless the media was pruned after the install.
    (media / 'CAFS/b.dsa').rename(media / 'CAFS/b.part')
    assert 'missing' in mc.check_media(media) and mc.main([str(media), 'media']) == 1
    assert mc.check_media(media, allow_pruned=True) is None and mc.main([str(media), 'media', '--allow-pruned']) == 0
    (media / 'CAFS/b.part').rename(media / 'CAFS/b.dsa')
    # A file of another folder is checked too; a partial (shorter) file fails the size total, a same-size wrong file the hash check.
    (Path(tmp) / '2' / 'two.dsa').unlink(); assert 'missing' in mc.check_media(media); (Path(tmp) / '2' / 'two.dsa').write_bytes(b'cc')
    (media / 'CAFS/b.dsa').write_bytes(b'b'); assert 'partial' in mc.check_media(media)
    (media / 'CAFS/b.dsa').write_bytes(b'bX'); assert mc.check_media(media) is None and 'mismatch' in mc.check_hashes(media)
    (media / 'CAFS/b.dsa').write_bytes(b'bb')
    mc.EXPECTED_FILES = 5; assert 'another media release' in mc.check_media(media); mc.EXPECTED_FILES = 4
    # setup.exe: partial copy, other build, missing.
    (media / 'setup.exe').write_bytes(setup[:1000]); assert 'pinned' in mc.check_media(media)
    (media / 'setup.exe').write_bytes(setup + b'\x01'); assert 'pinned' in mc.check_media(media, allow_pruned=True)
    (media / 'setup.exe').unlink(); assert 'missing' in mc.check_media(media)
    (media / 'setup.exe').write_bytes(setup)
    # Manifest missing or broken.
    (media / '0data' / 'MediaContent.xml').write_text('<Media><File'); assert 'unreadable' in mc.check_media(media)
    (media / '0data' / 'MediaContent.xml').unlink(); assert 'MediaContent.xml' in mc.check_media(media)
    # The patched copy: missing, the original, truncated, flipped byte, and the real thing.
    assert 'missing' in mc.check_patch(media)
    target = media / 'setup_admin_proton_offline.exe'
    target.write_bytes(setup); assert 'not the expected' in mc.check_patch(media)
    good = patcher.patched_bytes(setup)
    target.write_bytes(good[:-5]); assert 'not the expected' in mc.check_patch(media)
    target.write_bytes(good[:200] + b'\x01' + good[201:]); assert 'not the expected' in mc.check_patch(media)
    target.write_bytes(good); assert mc.check_patch(media) is None and mc.main([str(media), 'patch']) == 0
print('media completeness, hash and patched-installer checks passed')
