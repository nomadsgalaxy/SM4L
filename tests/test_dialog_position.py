#!/usr/bin/env python3
"""Exercise the native dialog placement calculation without running CAD."""
import _paths
from pathlib import Path
import subprocess
import tempfile

source = (_paths.ROOT/'addin'/'spacemouse-view.c').read_text()
start = source.index('static void center_owned_rect(')
end = source.index('static int fix_window(', start)
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path/'check.c').write_text('#include <assert.h>\n'+source[start:end]+r'''
int main(void) {
  int owner[] = {214, 70, 2189, 1544};
  int dialog[] = {8600, 727, 8885, 888}, x, y;
  center_owned_rect(dialog, owner, &x, &y);
  assert(x == 1059 && y == 726);
  int negative[] = {-2000, 0, -1000, 800};
  center_owned_rect(dialog, negative, &x, &y);
  assert(x == -1643 && y == 319);
  int large[] = {8600, 0, 12600, 2000};
  center_owned_rect(large, owner, &x, &y);
  assert(x == 214 && y == 70);
  return 0;
}
''')
    subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', str(path/'check.c'), '-o', str(path/'check')], check=True)
    subprocess.run([str(path/'check')], check=True)
print('Dialog placement checks passed.')
