"""Catch breakage from moving files: import every script in addin/, bin/, setup/ and experiments/ the way it would run (its own
directory first on sys.path, top-level code executed but not its main), and check the repo paths that the shell scripts and
setup.sh build from their checkout root."""
import _paths
import re, subprocess, sys
from pathlib import Path

root = _paths.ROOT
problems = []

# 1. Python scripts: top-level imports must resolve from the script's own directory (or the standard library / installed packages).
for directory in ('addin', 'bin', 'setup', 'experiments'):
    for script in sorted((root / directory).glob('*.py')):
        text = script.read_text()
        guarded = re.search(r'if __name__\s*==\s*.__main__.', text) is not None
        if guarded:
            code = 'import runpy, sys; sys.path.insert(0, %r); runpy.run_path(%r, run_name="import_check")' % (str(script.parent), str(script))
            done = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True)
            if done.returncode:
                problems.append('%s/%s: %s' % (directory, script.name, (done.stderr.strip().splitlines() or ['failed'])[-1]))
        else:
            # No main guard: check the imports statically (the module must be stdlib, installed, or a file next to the script).
            import ast
            for node in ast.walk(ast.parse(text)):
                names = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
                for name in names:
                    if name in sys.stdlib_module_names or name == '_paths' or (script.parent / (name + '.py')).exists():
                        continue
                    import importlib.util
                    saved = list(sys.path); sys.path[:] = [x for x in sys.path if not x.startswith(str(root))]   # installed packages only, not the repo
                    found = importlib.util.find_spec(name); sys.path[:] = saved
                    if found is None:
                        problems.append('%s/%s: cannot import %s' % (directory, script.name, name))

# 2. Paths built from the checkout root in shell scripts and setup.sh must exist. In a script that sets root to its own directory
#    (launch_service.sh, launch_solidworks.sh) $root is that directory; everywhere else it is the checkout.
shell = [root / 'setup.sh'] + sorted((root / 'bin').glob('*.sh')) + sorted((root / 'experiments').glob('*.sh'))
for script in shell:
    text = script.read_text()
    own_dir = re.search(r'^root="\$\(dirname -- "\$\(realpath -- "\$0"\)"\)"$', text, re.M) is not None
    for match in re.finditer(r'"\$\{?(root|sm4l_root|SM4L_ROOT)\}?/([A-Za-z0-9_./-]+)"', text):
        base = script.parent if (match.group(1) == 'root' and own_dir) else root
        if not (base / match.group(2)).exists():
            problems.append('%s: refers to %s, which does not exist' % (script.relative_to(root), match.group(2)))
# 3. Files that Python scripts locate relative to their own file (Path(__file__).with_name(...), .parents[1]/'dir'/'file').
for script in sorted(p for d in ('addin', 'bin', 'setup', 'experiments') for p in (root / d).glob('*.py')):
    text = script.read_text()
    for name in re.findall(r"__file__\)(?:\.resolve\(\))?\.with_name\('([^']+)'\)", text):
        if not (script.parent / name).exists():
            problems.append('%s/%s: %r does not exist next to it' % (script.parent.name, script.name, name))
    for parts in re.findall(r"parents\[1\]\s*/\s*'([a-z]+)'\s*/\s*'([^']+)'", text):
        if not (root / parts[0] / parts[1]).exists():
            problems.append('%s/%s: refers to %s/%s, which does not exist' % (script.parent.name, script.name, *parts))
assert not problems, '\n'.join(problems)
print('every script in addin/, bin/, setup/ and experiments/ imports, and the checkout paths they use exist')
