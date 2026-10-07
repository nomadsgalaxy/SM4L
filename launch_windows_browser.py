"""Open the SOLIDWORKS platform with an isolated Firefox Windows identity."""
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.parse import urlsplit

PLATFORM = os.environ.get('SOLIDWORKS_PLATFORM_URL', '')
MARKER = '// Managed by SOLIDWORKS launch_windows_browser.py\n'


def configure(profile, version):
    if not re.fullmatch(r'\d+(?:\.\d+)*', version):
        raise ValueError('Invalid Firefox version')
    agent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}'
    prefs = {'general.useragent.override': agent, 'general.platform.override': 'Win32',
             'general.oscpu.override': 'Windows NT 10.0; Win64; x64',
             'general.appversion.override': '5.0 (Windows)'}
    path = Path(profile) / 'user.js'
    if path.exists() and not path.read_text().startswith(MARKER):
        raise ValueError('Refusing to replace unrelated user.js')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MARKER + ''.join(f'user_pref({json.dumps(k)}, {json.dumps(v)});\n' for k, v in prefs.items()))
    return agent


def main():
    url = urlsplit(PLATFORM)
    if url.scheme != 'https' or not (url.hostname or '').endswith('.3ds.com') or url.username or url.password:
        raise SystemExit('SOLIDWORKS_PLATFORM_URL must be an HTTPS 3ds.com platform URL without credentials')
    browser = shutil.which('firefox')
    if not browser:
        raise SystemExit('Firefox is required; none is installed')
    version = re.search(r'Firefox (\d+(?:\.\d+)*)', subprocess.check_output([browser, '--version'], text=True))
    if not version:
        raise SystemExit('Cannot determine installed Firefox version')
    state = Path(os.environ.get('SOLIDWORKS_PROTON_STATE', str(Path.home() / '.local/share/solidworks-proton')))
    profile = state / 'browser-windows-firefox'
    agent = configure(profile, version[1])
    verified = False

    class Check(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log browser requests or authentication material.

        def do_GET(self):
            if self.path != '/':
                self.send_error(404)
                return
            script = "fetch('/identity',{method:'POST',body:JSON.stringify({userAgent:navigator.userAgent,platform:navigator.platform,oscpu:navigator.oscpu})}).then(r=>{if(r.ok)location.replace(" + json.dumps(PLATFORM).replace('<', r'\u003c') + ");else document.body.textContent='Windows identity check failed';});"
            page = ('<!doctype html><title>SOLIDWORKS browser check</title><p>Checking Windows browser identity...</p><script>' + script + '</script>').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            nonlocal verified
            length = int(self.headers.get('Content-Length', '0'))
            if self.path != '/identity' or not 0 < length <= 4096:
                self.send_error(400)
                return
            try:
                identity = json.loads(self.rfile.read(length))
                verified = (identity.get('userAgent') == agent and self.headers.get('User-Agent') == agent
                            and identity.get('platform') == 'Win32' and 'Windows' in identity.get('oscpu', ''))
            except (ValueError, AttributeError):
                verified = False
            self.send_response(200 if verified else 400)
            self.send_header('Content-Length', '0')
            self.end_headers()
            print('Verified Windows identity:' if verified else 'Identity mismatch:', json.dumps(identity if 'identity' in locals() else {}), flush=True)

    # ponytail: one local startup probe, not a persistent browser automation service.
    with http.server.HTTPServer(('127.0.0.1', 0), Check) as server:
        server.timeout = 1
        log_path = state / 'browser-windows-firefox.log'
        with log_path.open('ab') as log:
            log_path.chmod(0o600)
            process = subprocess.Popen(
                [browser, '--new-instance', '--profile', str(profile), f'http://127.0.0.1:{server.server_port}/'],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        deadline = time.monotonic() + 45
        while not verified and time.monotonic() < deadline:
            server.handle_request()
        if not verified:
            raise SystemExit('Browser identity was not verified within 45 seconds; close the dedicated Firefox window before retrying')
    print(f'Opened SOLIDWORKS platform; Firefox PID {process.pid}; startup log {log_path}', flush=True)
    # Keep the invoking execution alive until the browser closes.
    result = process.wait()
    print(f'Firefox exited with code {result}', flush=True)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
