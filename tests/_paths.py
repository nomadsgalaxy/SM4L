"""Make the code directories importable from the tests. The tests run as scripts (python3 tests/test_x.py), so this
module sits next to them and is imported first."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _d in ('addin', 'bin', 'setup', 'experiments'):
    sys.path.insert(0, str(ROOT / _d))
