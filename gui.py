#!/usr/bin/env python3
"""Small local web GUI for the Playwright screenshot tool."""

from __future__ import annotations

import datetime
import json
import os
import signal
import subprocess
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Playwright Screenshots</title>
  <style>
    :root {
      --bg: #f3f4ef;
      --panel: #fffdf7;
      --ink: #21302b;
      --muted: #64726d;
      --line: #d8ddd5;
      --accent: #165d4a;
      --accent-2: #e7f3ee;
      --danger: #8c2f39;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(22, 93, 74, 0.08), transparent 32%),
        linear-gradient(180deg, #fbfaf5 0%, var(--bg) 100%);
      color: var(--ink);
    }
    .shell {
      width: min(1100px, calc(100% - 32px));
      margin: 24px auto;
      display: grid;
      gap: 18px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 18px 40px rgba(25, 42, 36, 0.08);
    }
    .hero {
      padding: 24px;
      display: grid;
      gap: 8px;
    }
    h1 {
      margin: 0;
      font-size: clamp(28px, 4vw, 42px);
      line-height: 1.05;
    }
    .hero p, .hint, .meta {
      margin: 0;
      color: var(--muted);
    }
    .panel {
      padding: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px 18px;
    }
    .field {
      display: grid;
      gap: 6px;
    }
    .field.full {
      grid-column: 1 / -1;
    }
    label, .section-title {
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.01em;
    }
    input[type="text"], input[type="number"], textarea, select {
      width: 100%;
      border: 1px solid #c8d0c8;
      border-radius: 12px;
      padding: 12px 14px;
      background: white;
      font: inherit;
      color: var(--ink);
    }
    textarea {
      min-height: 90px;
      resize: vertical;
    }
    .radio-row, .check-row, .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px 14px;
      align-items: center;
    }
    .radio-pill, .check-pill {
      border: 1px solid var(--line);
      background: #f8faf7;
      border-radius: 999px;
      padding: 8px 12px;
      display: inline-flex;
      gap: 8px;
      align-items: center;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, opacity 120ms ease;
    }
    button:hover { transform: translateY(-1px); }
    button.primary {
      background: var(--accent);
      color: white;
    }
    button.secondary {
      background: var(--accent-2);
      color: var(--accent);
    }
    button.warning {
      background: #f5e4e2;
      color: var(--danger);
    }
    button.ghost {
      background: #eef1eb;
      color: var(--ink);
    }
    button:disabled {
      opacity: 0.45;
      cursor: default;
      transform: none;
    }
    .status-strip {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      padding: 14px 16px;
      border-radius: 14px;
      background: #f6f9f6;
      border: 1px solid var(--line);
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--muted);
    }
    .dot.running { background: #d08d11; }
    .dot.finished { background: var(--accent); }
    .dot.failed { background: var(--danger); }
    pre {
      margin: 0;
      padding: 16px;
      min-height: 320px;
      max-height: 52vh;
      overflow: auto;
      background: #18211f;
      color: #e8f4ef;
      border-radius: 16px;
      font: 12px/1.5 "SFMono-Regular", Menlo, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .hidden { display: none !important; }
    @media (max-width: 760px) {
      .grid { grid-template-columns: 1fr; }
      .shell { width: min(100% - 20px, 1100px); margin: 10px auto 24px; }
      .panel, .hero { padding: 16px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <p class="meta">Local web GUI</p>
      <h1>Playwright Screenshots</h1>
      <p>Start screenshot runs from your browser, keep the existing CLI logic, and inspect progress live without Tkinter.</p>
    </section>

    <section class="panel">
      <form id="run-form" class="grid">
        <div class="field full">
          <div class="section-title">Input mode</div>
          <div class="radio-row">
            <label class="radio-pill"><input type="radio" name="input_mode" value="single" checked> Single website</label>
            <label class="radio-pill"><input type="radio" name="input_mode" value="file"> Website list file</label>
          </div>
        </div>

        <div class="field full" id="single-field">
          <label for="single_url">Website or sitemap</label>
          <input id="single_url" name="single_url" type="text" placeholder="example.com or example.com/sitemap.xml">
        </div>

        <div class="field full hidden" id="file-field">
          <label for="url_file">Website list file</label>
          <div class="button-row">
            <input id="url_file" name="url_file" type="text" placeholder="/Users/.../sites.txt">
            <button class="ghost" type="button" id="choose-file-button">Choose file...</button>
          </div>
          <p class="hint">One website or sitemap entry per line. Comments starting with <code>#</code> are supported.</p>
        </div>

        <div class="field">
          <label for="variant">Variant</label>
          <select id="variant" name="variant">
            <option value="basic">Basic</option>
            <option value="extended">Extended</option>
          </select>
        </div>

        <div class="field">
          <label for="timeout_profile">Timeout profile</label>
          <select id="timeout_profile" name="timeout_profile">
            <option value="normal">Normal</option>
            <option value="slow">Slow</option>
          </select>
        </div>

        <div class="field">
          <label for="include_filters">Include filters</label>
          <input id="include_filters" name="include_filters" type="text" placeholder="/blog/,/news/">
        </div>

        <div class="field">
          <label for="exclude_filters">Exclude filters</label>
          <input id="exclude_filters" name="exclude_filters" type="text" placeholder="/tag/,/author/">
        </div>

        <div class="field">
          <label for="max_urls">Max URLs</label>
          <input id="max_urls" name="max_urls" type="number" min="1" step="1" placeholder="10">
        </div>

        <div class="field full">
          <div class="section-title">Options</div>
          <div class="check-row">
            <label class="check-pill"><input type="checkbox" id="only_failed" name="only_failed"> Only failed</label>
            <label class="check-pill"><input type="checkbox" id="generate_index" name="generate_index" checked> Generate HTML index</label>
          </div>
        </div>

        <div class="field full">
          <div class="button-row">
            <button class="primary" type="submit" id="start-button">Start screenshots</button>
            <button class="warning" type="button" id="stop-button" disabled>Stop run</button>
            <button class="secondary" type="button" id="open-output-button" disabled>Open last output</button>
          </div>
        </div>
      </form>
    </section>

    <section class="panel">
      <div class="status-strip">
        <div class="status-pill"><span class="dot" id="status-dot"></span><span id="status-text">Ready</span></div>
        <div class="meta" id="status-meta">No run started yet.</div>
      </div>
    </section>

    <section class="panel">
      <div class="button-row" style="margin-bottom: 10px;">
        <div class="section-title">Live log</div>
      </div>
      <pre id="log-output">Ready.\n</pre>
    </section>
  </div>

  <script>
    const form = document.getElementById('run-form');
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');
    const openOutputButton = document.getElementById('open-output-button');
    const logOutput = document.getElementById('log-output');
    const statusText = document.getElementById('status-text');
    const statusMeta = document.getElementById('status-meta');
    const statusDot = document.getElementById('status-dot');
    const singleField = document.getElementById('single-field');
    const fileField = document.getElementById('file-field');
    const chooseFileButton = document.getElementById('choose-file-button');

    function currentInputMode() {
      return form.querySelector('input[name="input_mode"]:checked').value;
    }

    function updateInputMode() {
      const singleMode = currentInputMode() === 'single';
      singleField.classList.toggle('hidden', !singleMode);
      fileField.classList.toggle('hidden', singleMode);
    }

    function collectPayload() {
      return {
        input_mode: currentInputMode(),
        single_url: document.getElementById('single_url').value,
        url_file: document.getElementById('url_file').value,
        variant: document.getElementById('variant').value,
        timeout_profile: document.getElementById('timeout_profile').value,
        include_filters: document.getElementById('include_filters').value,
        exclude_filters: document.getElementById('exclude_filters').value,
        max_urls: document.getElementById('max_urls').value,
        only_failed: document.getElementById('only_failed').checked,
        generate_index: document.getElementById('generate_index').checked,
      };
    }

    function updateState(state) {
      logOutput.textContent = state.log_text || 'Ready.\\n';
      logOutput.scrollTop = logOutput.scrollHeight;
      statusText.textContent = state.status_text || 'Ready';
      statusMeta.textContent = state.status_meta || 'No run started yet.';
      startButton.disabled = !!state.running;
      stopButton.disabled = !state.running;
      openOutputButton.disabled = !state.can_open_output;
      statusDot.className = 'dot ' + (state.running ? 'running' : (state.last_return_code === 0 ? 'finished' : (state.last_return_code === null ? '' : 'failed')));
    }

    async function pollState() {
      try {
        const response = await fetch('/api/state');
        const state = await response.json();
        updateState(state);
      } catch (error) {
        statusText.textContent = 'Disconnected';
        statusMeta.textContent = String(error);
      }
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      startButton.disabled = true;
      try {
        const response = await fetch('/api/start', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(collectPayload()),
        });
        const payload = await response.json();
        if (!response.ok) {
          alert(payload.error || 'Could not start the run.');
        }
      } finally {
        setTimeout(pollState, 150);
      }
    });

    openOutputButton.addEventListener('click', async () => {
      const response = await fetch('/api/open-output', {method: 'POST'});
      const payload = await response.json();
      if (!response.ok) {
        alert(payload.error || 'Could not open output.');
      }
    });

    stopButton.addEventListener('click', async () => {
      const response = await fetch('/api/stop', {method: 'POST'});
      const payload = await response.json();
      if (!response.ok) {
        alert(payload.error || 'Could not stop the run.');
      }
      setTimeout(pollState, 150);
    });

    chooseFileButton.addEventListener('click', async () => {
      const response = await fetch('/api/choose-file', {method: 'POST'});
      const payload = await response.json();
      if (!response.ok) {
        alert(payload.error || 'Could not choose a file.');
        return;
      }
      if (payload.path) {
        document.getElementById('url_file').value = payload.path;
      }
    });

    form.querySelectorAll('input[name="input_mode"]').forEach((input) => {
      input.addEventListener('change', updateInputMode);
    });

    updateInputMode();
    pollState();
    setInterval(pollState, 1000);
  </script>
</body>
</html>
"""


def domain_slug(root_url: str) -> str:
    """Convert a URL-like string into a filesystem-safe domain folder name."""
    parsed = urlparse(root_url)
    host = parsed.netloc or parsed.path
    host = host.lower().strip()
    host = host.split('@')[-1]
    host = host.split(':')[0]
    host = host.strip('/')
    if host.startswith('www.'):
        host = host[4:]
    allowed = ''.join(ch if ch.isalnum() or ch in '._-' else '-' for ch in host)
    while '--' in allowed:
        allowed = allowed.replace('--', '-')
    return allowed or 'site'


def normalize_input_url(raw_input: str) -> str:
    """Normalize loose website input into a URL-like string for output path prediction."""
    value = raw_input.strip()
    if not value:
        return value
    if value.startswith('//'):
        value = 'https:' + value
    parsed = urlparse(value)
    if parsed.scheme:
        return value
    if '/' in value:
        return 'https://' + value.lstrip('/')
    return 'https://' + value


class AppState:
    """Shared state for the local web GUI."""

    def __init__(self, script_dir: Path) -> None:
        self.script_dir = script_dir
        self.python_path = script_dir / '.venv' / 'bin' / 'python'
        self.script_path = script_dir / 'screenshot.py'
        self.output_root = script_dir / 'screenshots'
        self.lock = threading.Lock()
        self.process: Optional[subprocess.Popen[str]] = None
        self.log_text = 'Ready.\n'
        self.status_text = 'Ready'
        self.status_meta = 'No run started yet.'
        self.last_output_target: Optional[Path] = None
        self.last_return_code: Optional[int] = None
        self.stop_requested = False

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            can_open_output = bool(self.last_output_target and self.last_output_target.exists())
            return {
                'running': self.process is not None,
                'log_text': self.log_text,
                'status_text': self.status_text,
                'status_meta': self.status_meta,
                'can_open_output': can_open_output,
                'last_output_target': str(self.last_output_target) if self.last_output_target else '',
                'last_return_code': self.last_return_code,
            }

    def append_log(self, text: str) -> None:
        with self.lock:
            self.log_text += text
            if len(self.log_text) > 200000:
                self.log_text = self.log_text[-200000:]

    def set_running(self, process: subprocess.Popen[str], command: list[str]) -> None:
        with self.lock:
            self.process = process
            self.last_return_code = None
            self.last_output_target = None
            self.stop_requested = False
            self.status_text = 'Running'
            self.status_meta = ' '.join(command)
            self.log_text += '\n' + '=' * 72 + '\n'
            self.log_text += 'Starting command:\n' + ' '.join(command) + '\n\n'

    def set_stopping(self) -> None:
        with self.lock:
            self.stop_requested = True
            self.status_text = 'Stopping'
            self.status_meta = 'Stopping screenshot run...'
            self.log_text += '\nStopping screenshot run...\n'

    def finish(self, return_code: int, output_target: Optional[Path]) -> None:
        with self.lock:
            self.process = None
            self.last_return_code = return_code
            self.last_output_target = output_target
            if self.stop_requested:
                self.status_text = 'Stopped'
                self.status_meta = 'Run stopped by user.'
                self.log_text += '\nRun stopped by user.\n'
            elif return_code == 0:
                self.status_text = 'Finished'
                self.status_meta = 'Run finished successfully.'
                self.log_text += '\nRun finished successfully.\n'
            else:
                self.status_text = 'Failed'
                self.status_meta = f'Run finished with exit code {return_code}.'
                self.log_text += f'\nRun finished with exit code {return_code}.\n'
            self.stop_requested = False


def validate_payload(state: AppState, payload: Dict[str, Any]) -> Optional[str]:
    """Return a human-readable error when the request is not valid."""
    if not state.python_path.exists():
        return f'Missing virtual environment Python: {state.python_path}'
    if not state.script_path.exists():
        return f'Missing screenshot.py: {state.script_path}'

    input_mode = payload.get('input_mode', 'single')
    if input_mode == 'single':
        if not str(payload.get('single_url', '')).strip():
            return 'Enter a website or sitemap first.'
    elif input_mode == 'file':
        file_path = Path(str(payload.get('url_file', '')).strip())
        if not str(file_path):
            return 'Choose a website list file first.'
        if not file_path.exists():
            return f'List file not found: {file_path}'
    else:
        return 'Unknown input mode.'

    max_urls = str(payload.get('max_urls', '')).strip()
    if max_urls and (not max_urls.isdigit() or max_urls == '0'):
        return 'Max URLs must be a positive whole number.'

    return None


def build_command(state: AppState, payload: Dict[str, Any]) -> list[str]:
    """Build the screenshot.py command from GUI payload."""
    command = [
        str(state.python_path),
        '-u',
        str(state.script_path),
        '--variant', str(payload.get('variant', 'basic') or 'basic'),
        '--timeout-profile', str(payload.get('timeout_profile', 'normal') or 'normal'),
        '--no-open',
    ]

    if payload.get('generate_index', True):
        command.append('--generate-index')
    if payload.get('only_failed'):
        command.append('--only-failed')

    include_filters = str(payload.get('include_filters', '')).strip()
    exclude_filters = str(payload.get('exclude_filters', '')).strip()
    max_urls = str(payload.get('max_urls', '')).strip()

    if include_filters:
        command.extend(['--include', include_filters])
    if exclude_filters:
        command.extend(['--exclude', exclude_filters])
    if max_urls:
        command.extend(['--max-urls', max_urls])

    if payload.get('input_mode') == 'file':
        command.extend(['--url-file', str(payload.get('url_file', '')).strip()])
    else:
        command.extend(['--url', str(payload.get('single_url', '')).strip()])

    return command


def predict_output_target(state: AppState, payload: Dict[str, Any]) -> Optional[Path]:
    """Predict the most useful output path after a finished run."""
    if payload.get('input_mode') == 'file':
        return state.output_root if state.output_root.exists() else None

    normalized = normalize_input_url(str(payload.get('single_url', '')))
    if not normalized:
        return None
    date_str = datetime.date.today().strftime('%Y-%m-%d')
    run_dir = state.output_root / domain_slug(normalized) / date_str
    if payload.get('generate_index', True):
        index_path = run_dir / 'index.html'
        return index_path if index_path.exists() else run_dir
    return run_dir


def choose_file(script_dir: Path) -> tuple[bool, str]:
    """Open a native macOS file chooser and return the selected path."""
    script = '''
set chosenFile to choose file with prompt "Choose website list file"
POSIX path of chosenFile
'''
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            check=True,
            capture_output=True,
            text=True,
            cwd=script_dir,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or '').strip()
        if 'User canceled' in stderr:
            return True, ''
        return False, stderr or 'Could not choose a file.'
    return True, result.stdout.strip()


def open_path(target_path: Path) -> tuple[bool, str]:
    """Open a file or folder on macOS."""
    try:
        subprocess.run(['open', str(target_path)], check=True)
    except subprocess.CalledProcessError as exc:
        return False, str(exc)
    return True, ''


def start_run(state: AppState, payload: Dict[str, Any]) -> tuple[bool, str]:
    """Start a background screenshot run."""
    validation_error = validate_payload(state, payload)
    if validation_error:
        return False, validation_error

    with state.lock:
        if state.process is not None:
            return False, 'A screenshot run is already active.'

    command = build_command(state, payload)
    try:
        process = subprocess.Popen(
            command,
            cwd=state.script_dir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
    except Exception as exc:
        return False, f'Could not start the screenshot run: {exc}'

    state.set_running(process, command)

    def worker() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            state.append_log(line)
        return_code = process.wait()
        output_target = predict_output_target(state, payload)
        state.finish(return_code, output_target if output_target and output_target.exists() else None)

    threading.Thread(target=worker, daemon=True).start()
    return True, ''


def stop_run(state: AppState) -> tuple[bool, str]:
    """Stop the active screenshot run if one is still running."""
    with state.lock:
        process = state.process
    if process is None:
        return False, 'No screenshot run is active.'

    state.set_stopping()

    try:
        process.send_signal(signal.SIGINT)
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception as exc:
            return False, f'Could not stop the screenshot run: {exc}'

    def force_kill_later() -> None:
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=3)
                return
            except Exception:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    threading.Thread(target=force_kill_later, daemon=True).start()
    return True, ''


class AppHandler(BaseHTTPRequestHandler):
    """HTTP handler for the local screenshot web GUI."""

    app_state: AppState

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, html: str) -> None:
        data = html.encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> Dict[str, Any]:
        content_length = int(self.headers.get('Content-Length', '0') or 0)
        if content_length <= 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))

    def do_GET(self) -> None:  # noqa: N802
        if self.path == '/':
            self._send_html(HTML_PAGE)
            return
        if self.path == '/api/state':
            self._send_json(self.app_state.snapshot())
            return
        self._send_json({'error': 'Not found.'}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == '/api/start':
            payload = self._read_json()
            ok, error = start_run(self.app_state, payload)
            if not ok:
                self._send_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({'ok': True})
            return

        if self.path == '/api/open-output':
            snapshot = self.app_state.snapshot()
            target = snapshot.get('last_output_target')
            if not target:
                self._send_json({'error': 'No output is available yet.'}, status=HTTPStatus.BAD_REQUEST)
                return
            ok, error = open_path(Path(str(target)))
            if not ok:
                self._send_json({'error': error}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json({'ok': True})
            return

        if self.path == '/api/stop':
            ok, error = stop_run(self.app_state)
            if not ok:
                self._send_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({'ok': True})
            return

        if self.path == '/api/choose-file':
            ok, result = choose_file(self.app_state.script_dir)
            if not ok:
                self._send_json({'error': result}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json({'path': result})
            return

        self._send_json({'error': 'Not found.'}, status=HTTPStatus.NOT_FOUND)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    state = AppState(script_dir)
    handler_class = type('PlaywrightGUIHandler', (AppHandler,), {'app_state': state})
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_class)
    url = f'http://127.0.0.1:{server.server_port}/'
    print(f'Opening local GUI at {url}')
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
