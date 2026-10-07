"""Check motion bounds, axis tuning and the exact Windows packet layout."""
import math
from pathlib import Path
import stat
import tempfile
import time
from spacemouse import MAGIC, PACKET, publish, values, smooth

assert smooth([100]*6, [0]*6, 1/30, .05, 10) == [0]*6
assert smooth([0]*6, [100]*6, 1/30, 0, 10) == [100]*6
filtered = smooth([0]*6, [100]*6, 1/30, .05, 10)
assert all(0 < x < 100 for x in filtered)
assert all(a < b < 100 for a,b in zip(filtered, smooth(filtered, [100]*6, 1/30, .05, 10)))
args = (.000002, .00004, .00008, 10, [1]*6)
assert values([0]*6, 1/30, *args) == (0, 0, 1, 0, 0, 0)
assert values([10]*6, 1/30, *args) == (0, 0, 1, 0, 0, 0)
for axis in range(6):
    raw = [0]*6
    raw[axis] = 100
    motion = values(raw, 1/30, *args)
    assert motion[axis] != (1 if axis == 2 else 0)
    for other in range(6):
        if other != axis:
            assert motion[other] == (1 if other == 2 else 0)
    signs = [1]*6
    signs[axis] = -1
    inverse = values(raw, 1/30, *args[:-1], signs)
    assert math.isclose(motion[axis]*inverse[axis], 1) if axis == 2 else math.isclose(motion[axis], -inverse[axis])
bounded = values([10**9]*6, 10, 1, 1, 1, 0, [1]*6)
assert abs(bounded[0]) <= .05 and abs(bounded[1]) <= .05
assert .8 <= bounded[2] <= 1.2 and all(abs(x) <= .1 for x in bounded[3:])
try:
    values([math.nan]*6, 1/30, *args)
    raise AssertionError('NaN accepted')
except ValueError:
    pass
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory)/'motion.bin'
    publish(target, 1, bounded)
    magic, seq, stamp, *motion = PACKET.unpack(target.read_bytes())
    assert PACKET.size == 64 and magic == MAGIC and seq == 1
    assert 0 <= time.time_ns()//100+116444736000000000-stamp < 2000000
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert tuple(motion) == bounded
    publish(target, 2, (0, 0, 1, 0, 0, 0))
    assert PACKET.unpack(target.read_bytes())[1] == 2
    assert len(list(Path(directory).iterdir())) == 1
print('SpaceMouse mapping, bounds and atomic packet checks passed')
