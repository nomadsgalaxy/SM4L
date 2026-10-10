"""Check bin/gpu_env.sh against a fake /sys/class/drm: the desktop layout (monitors on the NVIDIA card) changes nothing, a hybrid
laptop (monitors on the other GPU) gets the NVIDIA offload variables, variables the user already set are kept, and SM4L_GPU=none/nvidia
override the detection."""
import _paths
import os, subprocess, tempfile
from pathlib import Path

script = _paths.ROOT / 'bin' / 'gpu_env.sh'
NAMES = ['__NV_PRIME_RENDER_OFFLOAD', '__GLX_VENDOR_LIBRARY_NAME', '__VK_LAYER_NV_optimus']

def layout(root, cards):
    """cards: [(vendor, [connector statuses])] becomes card0, card1, ... with card<N>-<connector>/status files."""
    for n, (vendor, statuses) in enumerate(cards):
        (root / f'card{n}/device').mkdir(parents=True)
        (root / f'card{n}/device/vendor').write_text(vendor + '\n')
        for i, status in enumerate(statuses):
            (root / f'card{n}-DP-{i + 1}').mkdir()
            (root / f'card{n}-DP-{i + 1}/status').write_text(status + '\n')

def run(root, **extra):
    env = {k: v for k, v in os.environ.items() if k not in NAMES and k != 'SM4L_GPU'}
    env.update(SM4L_DRM_ROOT=str(root), **extra)
    done = subprocess.run(['bash', '-c', f'source {script}; echo "$SM4L_GPU_NOTE"; ' + '; '.join(f'echo {n}=${{{n}-unset}}' for n in NAMES)], env=env, capture_output=True, text=True, check=True)
    note, *values = done.stdout.splitlines()
    return note, dict(v.split('=', 1) for v in values)

OFFLOAD = {'__NV_PRIME_RENDER_OFFLOAD': '1', '__GLX_VENDOR_LIBRARY_NAME': 'nvidia', '__VK_LAYER_NV_optimus': 'NVIDIA_only'}
UNSET = dict.fromkeys(NAMES, 'unset')
with tempfile.TemporaryDirectory() as tmp:
    desktop, hybrid, nvidia_only, no_gpu = (Path(tmp) / n for n in ('desktop', 'hybrid', 'nvidia_only', 'none'))
    layout(desktop, [('0x1002', ['disconnected']), ('0x10de', ['connected', 'connected'])])      # AMD iGPU unused, monitors on NVIDIA
    layout(hybrid, [('0x8086', ['connected']), ('0x10de', ['disconnected', 'disconnected'])])    # Intel drives the panel
    layout(nvidia_only, [('0x10de', ['disconnected'])])
    no_gpu.mkdir()
    assert run(desktop)[1] == UNSET
    assert run(nvidia_only)[1] == UNSET and run(no_gpu)[1] == UNSET
    note, got = run(hybrid)
    assert got == OFFLOAD and 'offload on' in note, (note, got)
    assert run(hybrid, __GLX_VENDOR_LIBRARY_NAME='mesa')[1] == dict(OFFLOAD, __GLX_VENDOR_LIBRARY_NAME='mesa')   # the user's value wins
    assert run(hybrid, SM4L_GPU='none')[1] == UNSET
    assert run(desktop, SM4L_GPU='nvidia')[1] == OFFLOAD
    assert run(hybrid, SM4L_GPU='auto')[1] == OFFLOAD
    note, got = run(hybrid, SM4L_GPU='bogus')
    assert got == UNSET and 'not none, nvidia or auto' in note
print('gpu_env: desktop and single-GPU layouts untouched, hybrid gets the offload variables, user values and the SM4L_GPU overrides respected')
