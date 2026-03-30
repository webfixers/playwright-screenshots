#!/usr/bin/env python3
"""Small Tkinter GUI for the Playwright screenshot tool."""

from __future__ import annotations

import datetime
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText
except ImportError as exc:  # pragma: no cover - only relevant on broken Python installs
    print(f"Tkinter is not available in this Python environment: {exc}", file=sys.stderr)
    raise SystemExit(1)


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


class ScreenshotGUI:
    """Tkinter app that launches screenshot.py and streams the output."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('Playwright Screenshots')
        self.root.minsize(900, 760)

        self.script_dir = Path(__file__).resolve().parent
        self.python_path = self.script_dir / '.venv' / 'bin' / 'python'
        self.script_path = self.script_dir / 'screenshot.py'
        self.output_root = self.script_dir / 'screenshots'

        self.process: Optional[subprocess.Popen[str]] = None
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.last_output_target: Optional[Path] = None

        self.input_mode = tk.StringVar(value='single')
        self.single_url = tk.StringVar()
        self.url_file = tk.StringVar()
        self.variant = tk.StringVar(value='basic')
        self.timeout_profile = tk.StringVar(value='normal')
        self.only_failed = tk.BooleanVar(value=False)
        self.generate_index = tk.BooleanVar(value=True)
        self.include_filters = tk.StringVar()
        self.exclude_filters = tk.StringVar()
        self.max_urls = tk.StringVar()
        self.status_text = tk.StringVar(value='Ready')

        self._build_ui()
        self._update_input_mode()
        self.root.after(100, self._drain_log_queue)
        self.root.protocol('WM_DELETE_WINDOW', self._handle_close)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        form = ttk.Frame(self.root, padding=16)
        form.grid(row=0, column=0, sticky='nsew')
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text='Input mode').grid(row=0, column=0, sticky='w')
        mode_frame = ttk.Frame(form)
        mode_frame.grid(row=0, column=1, sticky='w')
        ttk.Radiobutton(mode_frame, text='Single website', value='single', variable=self.input_mode,
                        command=self._update_input_mode).grid(row=0, column=0, padx=(0, 12))
        ttk.Radiobutton(mode_frame, text='Website list file', value='file', variable=self.input_mode,
                        command=self._update_input_mode).grid(row=0, column=1)

        ttk.Label(form, text='Website or sitemap').grid(row=1, column=0, sticky='w', pady=(10, 0))
        self.single_url_entry = ttk.Entry(form, textvariable=self.single_url)
        self.single_url_entry.grid(row=1, column=1, sticky='ew', pady=(10, 0))

        ttk.Label(form, text='List file').grid(row=2, column=0, sticky='w', pady=(10, 0))
        file_frame = ttk.Frame(form)
        file_frame.grid(row=2, column=1, sticky='ew', pady=(10, 0))
        file_frame.columnconfigure(0, weight=1)
        self.url_file_entry = ttk.Entry(file_frame, textvariable=self.url_file)
        self.url_file_entry.grid(row=0, column=0, sticky='ew')
        ttk.Button(file_frame, text='Browse...', command=self._browse_url_file).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(form, text='Variant').grid(row=3, column=0, sticky='w', pady=(10, 0))
        variant_frame = ttk.Frame(form)
        variant_frame.grid(row=3, column=1, sticky='w', pady=(10, 0))
        ttk.Radiobutton(variant_frame, text='Basic', value='basic', variable=self.variant).grid(row=0, column=0, padx=(0, 12))
        ttk.Radiobutton(variant_frame, text='Extended', value='extended', variable=self.variant).grid(row=0, column=1)

        ttk.Label(form, text='Timeout profile').grid(row=4, column=0, sticky='w', pady=(10, 0))
        timeout_frame = ttk.Frame(form)
        timeout_frame.grid(row=4, column=1, sticky='w', pady=(10, 0))
        ttk.Radiobutton(timeout_frame, text='Normal', value='normal', variable=self.timeout_profile).grid(row=0, column=0, padx=(0, 12))
        ttk.Radiobutton(timeout_frame, text='Slow', value='slow', variable=self.timeout_profile).grid(row=0, column=1)

        ttk.Label(form, text='Include filters').grid(row=5, column=0, sticky='w', pady=(10, 0))
        ttk.Entry(form, textvariable=self.include_filters).grid(row=5, column=1, sticky='ew', pady=(10, 0))

        ttk.Label(form, text='Exclude filters').grid(row=6, column=0, sticky='w', pady=(10, 0))
        ttk.Entry(form, textvariable=self.exclude_filters).grid(row=6, column=1, sticky='ew', pady=(10, 0))

        ttk.Label(form, text='Max URLs').grid(row=7, column=0, sticky='w', pady=(10, 0))
        ttk.Entry(form, textvariable=self.max_urls).grid(row=7, column=1, sticky='ew', pady=(10, 0))

        options_frame = ttk.Frame(form)
        options_frame.grid(row=8, column=0, columnspan=2, sticky='w', pady=(12, 0))
        ttk.Checkbutton(options_frame, text='Only failed', variable=self.only_failed).grid(row=0, column=0, padx=(0, 16))
        ttk.Checkbutton(options_frame, text='Generate HTML index', variable=self.generate_index).grid(row=0, column=1)

        button_frame = ttk.Frame(form)
        button_frame.grid(row=9, column=0, columnspan=2, sticky='w', pady=(14, 0))
        self.start_button = ttk.Button(button_frame, text='Start screenshots', command=self._start_run)
        self.start_button.grid(row=0, column=0)
        self.open_button = ttk.Button(button_frame, text='Open last output', command=self._open_last_output, state='disabled')
        self.open_button.grid(row=0, column=1, padx=(8, 0))
        ttk.Label(button_frame, textvariable=self.status_text).grid(row=0, column=2, padx=(16, 0))

        log_frame = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        log_frame.grid(row=1, column=0, sticky='nsew')
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        ttk.Label(log_frame, text='Live log').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.log_widget = ScrolledText(log_frame, wrap='word', font=('Menlo', 11))
        self.log_widget.grid(row=1, column=0, sticky='nsew')
        self.log_widget.configure(state='disabled')

    def _browse_url_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title='Choose website list file',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')],
            initialdir=self.script_dir,
        )
        if file_path:
            self.url_file.set(file_path)

    def _update_input_mode(self) -> None:
        single_mode = self.input_mode.get() == 'single'
        self.single_url_entry.configure(state='normal' if single_mode else 'disabled')
        self.url_file_entry.configure(state='disabled' if single_mode else 'normal')

    def _append_log(self, text: str) -> None:
        self.log_widget.configure(state='normal')
        self.log_widget.insert('end', text)
        self.log_widget.see('end')
        self.log_widget.configure(state='disabled')

    def _drain_log_queue(self) -> None:
        try:
            while True:
                message_type, payload = self.log_queue.get_nowait()
                if message_type == 'log':
                    self._append_log(payload)
                elif message_type == 'done':
                    self._finish_run(payload)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._drain_log_queue)

    def _validate_form(self) -> bool:
        if not self.python_path.exists():
            messagebox.showerror('Missing Python', f'Missing virtual environment Python:\n{self.python_path}')
            return False
        if not self.script_path.exists():
            messagebox.showerror('Missing script', f'Missing screenshot.py:\n{self.script_path}')
            return False

        if self.input_mode.get() == 'single':
            if not self.single_url.get().strip():
                messagebox.showerror('Missing website', 'Enter a website or sitemap first.')
                return False
        else:
            raw_file_path = self.url_file.get().strip()
            if not raw_file_path:
                messagebox.showerror('Missing list file', 'Choose a website list file first.')
                return False
            file_path = Path(raw_file_path)
            if not file_path.exists():
                messagebox.showerror('List file not found', f'Could not find:\n{file_path}')
                return False

        max_urls = self.max_urls.get().strip()
        if max_urls:
            if not max_urls.isdigit() or max_urls == '0':
                messagebox.showerror('Invalid max URLs', 'Max URLs must be a positive whole number.')
                return False

        return True

    def _build_command(self) -> list[str]:
        command = [
            str(self.python_path),
            str(self.script_path),
            '--variant', self.variant.get(),
            '--timeout-profile', self.timeout_profile.get(),
            '--no-open',
        ]

        if self.generate_index.get():
            command.append('--generate-index')
        if self.only_failed.get():
            command.append('--only-failed')

        include_filters = self.include_filters.get().strip()
        exclude_filters = self.exclude_filters.get().strip()
        max_urls = self.max_urls.get().strip()

        if include_filters:
            command.extend(['--include', include_filters])
        if exclude_filters:
            command.extend(['--exclude', exclude_filters])
        if max_urls:
            command.extend(['--max-urls', max_urls])

        if self.input_mode.get() == 'single':
            command.extend(['--url', self.single_url.get().strip()])
        else:
            command.extend(['--url-file', self.url_file.get().strip()])

        return command

    def _predict_output_target(self) -> Optional[Path]:
        if self.input_mode.get() != 'single':
            return self.output_root if self.output_root.exists() else None

        normalized = normalize_input_url(self.single_url.get())
        if not normalized:
            return None
        date_str = datetime.date.today().strftime('%Y-%m-%d')
        run_dir = self.output_root / domain_slug(normalized) / date_str
        if self.generate_index.get():
            index_path = run_dir / 'index.html'
            return index_path if index_path.exists() else run_dir
        return run_dir

    def _set_running_state(self, is_running: bool) -> None:
        self.start_button.configure(state='disabled' if is_running else 'normal')
        if is_running:
            self.open_button.configure(state='disabled')

    def _start_run(self) -> None:
        if self.process is not None:
            return
        if not self._validate_form():
            return

        command = self._build_command()
        self.last_output_target = None
        self.status_text.set('Running...')
        self._append_log('\n' + '=' * 72 + '\n')
        self._append_log('Starting command:\n')
        self._append_log(' '.join(command) + '\n\n')
        self._set_running_state(True)

        def worker() -> None:
            try:
                self.process = subprocess.Popen(
                    command,
                    cwd=self.script_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert self.process.stdout is not None
                for line in self.process.stdout:
                    self.log_queue.put(('log', line))
                return_code = self.process.wait()
                self.log_queue.put(('done', str(return_code)))
            except Exception as exc:
                self.log_queue.put(('log', f'\nFailed to start process: {exc}\n'))
                self.log_queue.put(('done', '1'))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _finish_run(self, return_code_text: str) -> None:
        return_code = int(return_code_text)
        self.process = None
        self.worker_thread = None
        self.last_output_target = self._predict_output_target()
        if self.last_output_target and self.last_output_target.exists():
            self.open_button.configure(state='normal')

        self._set_running_state(False)
        if return_code == 0:
            self.status_text.set('Finished')
            self._append_log('\nRun finished successfully.\n')
        else:
            self.status_text.set('Failed')
            self._append_log(f'\nRun finished with exit code {return_code}.\n')

    def _open_last_output(self) -> None:
        if not self.last_output_target or not self.last_output_target.exists():
            messagebox.showinfo('No output yet', 'No output folder or index file is available yet.')
            return
        try:
            subprocess.run(['open', str(self.last_output_target)], check=False)
        except Exception as exc:
            messagebox.showerror('Could not open output', str(exc))

    def _handle_close(self) -> None:
        if self.process is not None:
            should_close = messagebox.askyesno(
                'Quit GUI',
                'A screenshot run is still active. Quit the GUI anyway?',
            )
            if not should_close:
                return
            try:
                self.process.terminate()
            except Exception:
                pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass
    ScreenshotGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
