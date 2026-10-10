#!/usr/bin/env python3
"""glFlush / SpaceMouse A/B against the open CAD of the LOCAL prefix: python3 run_glflush_ab.py [seconds, default 50]
Window A: gl-diag + frame-diag only (all mitigations off). Window B: plus glFlush coalescing (16 ms), frame dynamics and catch-up.
Do the SAME motion in both: mouse orbit for the first half, SpaceMouse for the second. Per window it prints UI-thread and process CPU,
glFlush calls, skipped calls and time (UI add-in log) and the SpaceMouse frame lines (SpaceMouse add-in log). Window A also prints the
one-time GL dump (pixel format, renderer, profile, framebuffer) and the view preferences.
The prefix is ~/.local/share/solidworks-proton/prefix/pfx, or $SM4L_PREFIX. All flag files it creates are removed again at the end."""
import glob, os, re, subprocess, sys, time
PFX = os.environ.get('SM4L_PREFIX') or os.path.expanduser('~/.local/share/solidworks-proton/prefix/pfx')
C = PFX + '/drive_c'
UI, SM = C + '/sm4l-ui-compat.log', C + '/sm4l-spacemouse-addin.log'
SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 50
def lines(path):
    try: return open(path, errors='ignore').read().splitlines()
    except OSError: return []
def hexes(line, key): return [int(x, 16) for x in re.findall(key + r'=0x([0-9a-f]+)', line)]
try: cad = subprocess.check_output(['pgrep', '-xo', 'sldworks.exe']).decode().strip()
except subprocess.CalledProcessError: sys.exit('SOLIDWORKS (sldworks.exe) is not running')
hz = os.sysconf('SC_CLK_TCK')
def cpu():
    out = {}
    for name, path in (('UI thread', f'/proc/{cad}/task/{cad}/stat'), ('process', f'/proc/{cad}/stat')):
        s = open(path).read(); f = s[s.rindex(')') + 2:].split(); out[name] = int(f[11]) + int(f[12])
    return out
def window(label, extra, first):
    ui0, sm0 = len(lines(UI)), len(lines(SM))
    flags = dict.fromkeys(['sm4l-gl-diag', 'sm4l-frame-diag'] + [f for f, _ in extra], '')
    flags.update(dict(extra))
    try:
        for f, content in flags.items(): open(C + '/' + f, 'w').write(content)
        for _ in range(40):
            time.sleep(0.5)
            if any(l.startswith('gl flush') for l in lines(UI)[ui0:]): break
        else: print('    (note: no "gl flush" line within 20 s; the detour may not be installed, check the UI log)')
        time.sleep(1); mark_ui, mark_sm = len(lines(UI)), len(lines(SM)); c0 = cpu()
        print('\n>>> WINDOW %s: RECORDING (%d s): mouse orbit first, then SpaceMouse <<<' % (label, SECONDS), flush=True)
        for left in range(SECONDS, 0, -10):
            print('    %2d s left' % left, flush=True); time.sleep(min(10, left))
        c1 = cpu(); time.sleep(1)
    finally:
        for f in flags:
            try: os.remove(C + '/' + f)
            except OSError: pass
    ui, sm = lines(UI)[mark_ui:], lines(SM)[mark_sm:]
    print('\n=== WINDOW %s RESULT ===' % label)
    for k in c0: print('%-9s CPU: %.1f s (%.0f%% of one core over %d s)' % (k, (c1[k] - c0[k]) / hz, 100 * (c1[k] - c0[k]) / hz / SECONDS, SECONDS))
    fl = [l for l in ui if l.startswith('gl flush')]
    calls = sum(sum(hexes(l, 'calls')) for l in fl); skipped = sum(sum(hexes(l, 'skipped')) for l in fl); us = sum(sum(hexes(l, r'us in real flushes')) for l in fl)
    print('glFlush: %d calls, %d skipped, %d real, %.2f s in real flushes (%.0f%% of the window)' % (calls, skipped, calls - skipped, us / 1e6, 100 * us / 1e6 / SECONDS))
    fd = [l for l in sm if 'frame diag' in l]
    print('SpaceMouse frame lines (%d); first, middle, last:' % len(fd))
    for l in (fd[:1] + fd[len(fd) // 2:len(fd) // 2 + 1] + fd[-1:]) if fd else []: print('  ' + l.strip()[:230])
    if first:
        print('\nOne-time GL dump and view preferences (UI log):')
        for l in lines(UI)[ui0:]:
            if l.startswith(('gl context', ' gl ', 'view preferences', ' Remove', ' Level', ' Large', ' Perf', ' Transp', 'glflush')): print('  ' + l.rstrip()[:230])
        found = re.search(r'renderer=(.*?) version=', ' '.join(lines(UI)[ui0:]))
        nvidia = any(open(v).read().strip() == '0x10de' for v in glob.glob('/sys/class/drm/card[0-9]*/device/vendor'))
        if found and nvidia and 'NVIDIA' not in found.group(1):
            print('\n  !!! WARNING: this machine has an NVIDIA GPU but CAD renders on "%s". See bin/gpu_env.sh (SM4L_GPU=nvidia) and the launch log gpu.log.' % found.group(1))
        elif found: print('\n  renderer check: CAD renders on "%s"' % found.group(1))
window('A', [], True)
print('\n--- Same motion again. Window B (coalesce 16 ms + dynamics + catch-up) starts in 20 s. ---', flush=True)
time.sleep(20)
window('B', [('sm4l-glflush-coalesce-ms', '16'), ('sm4l-frame-dynamics', ''), ('sm4l-frame-catchup', '')], False)
print('\nDone. Compare UI CPU, glFlush time and the frame lines of A and B.')
