#!/usr/bin/env python3
"""SpaceMouse redraw variants on the open CAD of the LOCAL prefix (flag files only, no restart):
    python3 run_redraw_variants.py [seconds per variant, default 20] [letters, default all]
For each variant it sets the flag files, waits 3 s, then asks you to push/tilt the SpaceMouse cap steadily (the same motion every
time) for the window, and prints the average of the frame diag lines logged in it (milliseconds per frame; interval is the time
between applied frames). Say, per variant, whether the view visibly updates DURING the motion and how the detail looks.
Variants: 1 baseline (diag only), 2 notoggle, 3 noredraw, 4 dynamics, 5 dynamics+catchup, 6 dynamics+notoggle+noredraw,
7-9/a paint i/u/r/w + notoggle, b paint i with the default toggle, c gesture flag, d synthetic middle-button drag (default scale),
e mmb with px_per_rad=600, f mmb with px_per_rad=-300. Example: "20 1d" runs the baseline and then the middle-button drag.
Prefix: ~/.local/share/solidworks-proton/prefix/pfx or $SM4L_PREFIX. Every flag file is removed again at the end."""
import os, re, sys, time
C = (os.environ.get('SM4L_PREFIX') or os.path.expanduser('~/.local/share/solidworks-proton/prefix/pfx')) + '/drive_c'
SM = C + '/sm4l-spacemouse-addin.log'
SEC = int(sys.argv[1]) if len(sys.argv) > 1 else 20
ALL = ['mmb', 'paint', 'gesture', 'diag', 'notoggle', 'noredraw', 'dynamics', 'catchup']
VARIANTS = [('1 baseline (diag only)', []), ('2 notoggle', ['notoggle']), ('3 noredraw (the view may not repaint)', ['noredraw']),
            ('4 dynamics only', ['dynamics']), ('5 dynamics + catchup', ['dynamics', 'catchup']),
            ('6 dynamics + notoggle + noredraw', ['dynamics', 'notoggle', 'noredraw']),
            ('7 paint i (InvalidateRect) + notoggle', ['paint:i', 'notoggle']), ('8 paint u (Invalidate + UpdateWindow) + notoggle', ['paint:u', 'notoggle']),
            ('9 paint r (RedrawWindow) + notoggle', ['paint:r', 'notoggle']), ('a paint w (WindowRedraw) + notoggle', ['paint:w', 'notoggle']),
            ('b paint i + the default graphics-update toggle', ['paint:i']), ('c gesture flag', ['gesture']),
            ('d synthetic middle-button drag, default scale', ['mmb:']), ('e mmb, px_per_rad=600', ['mmb:px_per_rad=600']),
            ('f mmb, px_per_rad=-300 (rotation flipped)', ['mmb:px_per_rad=-300'])]
if len(sys.argv) > 2: VARIANTS = [v for v in VARIANTS if v[0][0] in sys.argv[2]]
def lines():
    try: return open(SM, errors='ignore').read().splitlines()
    except OSError: return []
def clear():
    for f in ALL:
        try: os.remove(C + '/sm4l-frame-' + f)
        except OSError: pass
try:
    for name, extra in VARIANTS:
        clear()
        for f in ['diag'] + extra:
            f, _, content = f.partition(':'); open(C + '/sm4l-frame-' + f, 'w').write(content)
        time.sleep(3); mark = len(lines())
        print('\n>>> VARIANT %s: move the SpaceMouse cap steadily for %d s NOW <<<' % (name, SEC), flush=True)
        time.sleep(SEC + 1)
        rows = [l for l in lines()[mark:] if 'frame diag' in l]
        acc = {}
        for l in rows:
            for k, v in re.findall(r'(\w+)=(\d+)', l.split(':', 1)[1].split('flags')[0]): acc.setdefault(k, []).append(int(v))
        print('    %d diag lines; averages in ms:' % len(rows), {k: round(sum(v) / len(v) / 1000, 1) for k, v in acc.items() if k != 'missed'}, 'missed', sum(acc.get('missed', [])))
        if not rows: print('    (no frame lines: the cap produced no motion, or the flag was not picked up)')
        for l in [l for l in lines()[mark:] if l.startswith('mmb:')][:2]: print('    ' + l.strip())
        time.sleep(4)
finally:
    clear()
print('\nflags cleared. Done.')
