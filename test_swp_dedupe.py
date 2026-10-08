"""Build and run the host-side checks of the SetWindowPos dedupe rules (swp_dedupe.h)."""
import subprocess, sys, tempfile
from pathlib import Path
here = Path(__file__).parent
with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / 'test_swp_dedupe'
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-I', str(here), str(here / 'test_swp_dedupe.c'), '-o', str(exe)], check=True)
    out = subprocess.run([str(exe)], capture_output=True, text=True)
    sys.stdout.write(out.stdout)
    sys.exit(out.returncode)
