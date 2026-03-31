# Playwright Screenshots

A local Python tool to generate full-page screenshots of all relevant pages in a website, based on a root URL or a `sitemap.xml`. It is intended as a practical visual archive after go-live, with screenshot sets tailored to Beaver Builder breakpoints.

## Project location

The project can live in any folder on your Mac. The `.command` launcher now resolves its own location automatically, so moving the project folder does not require editing the launcher.

## Recommended project structure

Keep the Python script and the virtual environment together in the same project folder.

```text
playwright-screenshots/
├── gui.py
├── macos-app/
├── screenshot.py
├── README.md
├── .gitignore
├── .venv/
├── build-macos-app.command
├── run-screenshots.command
├── run-screenshots-gui.command
└── screenshots/
    └── example.com/
```

## First-time setup

Only do this once on a new Mac or a new copy of the project.

```bash
cd "/Users/mennofink/Library/CloudStorage/GoogleDrive-menno@webfixers.nl/.shortcut-targets-by-id/1snrUQNe2fCBN9HocLIwfJVuVQU4AE_2x/Development/Applicaties/playwright-screenshots"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install playwright aiohttp
python -m playwright install
```

## Every next time

When you want to generate screenshots again later, open Terminal and run:

```bash
cd "/path/to/playwright-screenshots"
source .venv/bin/activate
```

Once the prompt shows `(.venv)`, you are ready to run the script.

## Usage

The entry point is `screenshot.py`. You can provide a full URL, a bare domain like `example.com`, or a sitemap path like `example.com/sitemap.xml`, and then choose either the `basic` or `extended` screenshot set.

For batch runs, you can also provide a text file with one website or sitemap entry per line.

If you prefer not to work in Terminal, you can now also use the local web GUI in `gui.py` or launch it via `run-screenshots-gui.command`.
The GUI is now a small local web interface started by `gui.py`. It runs locally on your Mac, opens in your browser, and still uses the project `.venv` for the actual screenshot run.

You can also build a native macOS app that runs screenshot jobs directly without showing a Terminal window or opening a browser.

## GUI usage

Start the GUI with:

```bash
cd "/path/to/playwright-screenshots"
source .venv/bin/activate
python gui.py
```

Or on macOS, just double-click `run-screenshots-gui.command`.

The first GUI version includes:

- single website or website list file mode
- `basic` or `extended` variants
- `normal` or `slow` timeout profile
- `only failed`, include, exclude and max URL options
- an optional GUI toggle to block third-party media such as YouTube embeds during capture
- a `Pause run` / `Resume run` control for long runs
- a live log view in the browser during the run
- live progress feedback for current page and viewport
- a small recent-run history in the GUI
- a `Stop run` button to stop the active screenshot process cleanly
- an `Open last output` button after the run finishes
- a native file chooser for website list files on macOS

The GUI intentionally reuses `screenshot.py` underneath, so the CLI and GUI stay aligned.
Closing the browser tab does not stop the run by itself, because the local GUI server still runs in Terminal. Use the `Stop run` button in the browser or `Ctrl+C` in the Terminal window that launched the GUI.
The GUI stores a small local history in `.gui-history.json` inside the project folder.

## macOS app

If you want a proper `.app` that runs screenshot jobs natively without showing Terminal, build the app once with:

```bash
cd "/path/to/playwright-screenshots"
./build-macos-app.command
```

That creates:

```text
build/Playwright Screenshots.app
```

Keep that `.app` inside the project folder so it can still find `.venv` and `screenshot.py` even if you move the whole project later.

What this app does:

- starts `screenshot.py` directly using the project `.venv`
- builds and uses its own custom macOS app icon
- lets you enter a website or sitemap directly in a native window
- supports both single-website mode and website-list-file mode
- shows native controls for variant, timeout profile, filters, max URLs, and media blocking
- shows live run progress and logs in the native app window
- lets you pause and resume the active run
- lets you stop the active screenshot run from the native app window
- lets you open the last generated output directly from the native app window
- keeps a small native recent-run history and can reopen selected outputs
- shows the current app version in the native wrapper window
- includes a `Quit App` button in the native wrapper window
- keeps using the same existing `screenshot.py` engine and output structure

This is now a first native macOS frontend around the existing Python engine. The separate web GUI is still available, but the app no longer depends on opening it in a browser.
The native app stores a small local history in `.native-app-history.json` inside the project folder.

### Basic example

```bash
python screenshot.py --url example.com --variant basic
```

### Extended example

```bash
python screenshot.py --url www.example.com --variant extended
```

### Generate a browseable HTML index too

```bash
python screenshot.py --url https://example.com/sitemap.xml --variant basic --generate-index
```

If you omit `https://`, the script now adds it automatically. When needed, it also tries common variants such as `www.` and both `sitemap.xml` and `sitemap_index.xml`.

On macOS in an interactive Terminal session, the script will automatically open the generated `index.html` after a successful run. Without `--generate-index`, it opens the dated run folder instead.

### Example with include/exclude filters

```bash
python screenshot.py --url https://example.com/sitemap.xml --variant basic --include /blog/,/news/ --exclude /tag/,/author/
```

### Example with a safer sample run

```bash
python screenshot.py --url https://example.com/sitemap.xml --variant basic --max-urls 10 --generate-index --no-open
```

### Example with the slow timeout profile

```bash
python screenshot.py --url example.com --variant basic --timeout-profile slow
```

### Example with a website list file

```bash
python screenshot.py --url-file sites.txt --variant basic --generate-index
```

Example `sites.txt`:

```text
# One website or sitemap per line
example.com
www.example.org
https://site.nl/sitemap.xml
```

### Example with your current workflow

```bash
cd "/path/to/playwright-screenshots"
source .venv/bin/activate
python screenshot.py --url https://example.com/sitemap.xml --variant basic --generate-index
```

## What the terminal output looks like

The script now shows progress per page and per viewport, for example:

```text
Output folder for this domain: screenshots/example.com
Run folder for today: screenshots/example.com/2026-03-27
Fetching sitemap(s)...
Found 11 URLs in sitemap(s).
[1/11] Starting https://example.com/
[1/11] home -> viewport 1/4: desktop (1400x900)
[1/11] Saved desktop: home/desktop.png
...
Run complete.
Pages processed: 11 | Pages with at least one successful viewport: 11 | Pages with failed viewports: 0
Viewport results -> success: 44, failed: 0
```

Before screenshots start, the script also shows a short preview of the URLs it is about to process. In interactive Terminal sessions, runs of 100 URLs or more require confirmation before capture begins.

After a successful run on macOS, the script also opens the output automatically unless you disable that behavior with `--no-open`.

For native app integrations, `screenshot.py` also supports an internal `--event-stream jsonl` mode so the app can receive structured progress updates while the normal CLI output stays intact.

The `.command` launcher now also supports a few safe extra options:

- rerun only previously failed URLs
- optional include filters
- optional exclude filters
- an optional max URL limit for smaller sample runs
- disabling automatic opening after the run
- single-site or list-file input mode

For long pages, the script now scrolls through the page, waits for the document height to settle, and returns to the top before taking the full-page screenshot. This improves capture stability on pages with lazy-loaded sections.

In batch mode, the script processes sites one by one and prints a short summary at the end. Automatic opening is skipped in batch mode to avoid opening many Finder windows or browser tabs.

You can choose a timeout profile too:

- `normal`: default timing for typical websites
- `slow`: longer waits for heavier, slower, or more script-heavy websites

The capture flow is now a bit more defensive on difficult sites too:

- it hides common consent and modal overlays more carefully
- it avoids broad layout selectors like generic banners or sticky sections
- it can run one extra stabilization pass when a page still looks suspiciously blank or blocked
- it records redirect and suspicious-result flags in the reports for easier follow-up

If you explicitly want to suppress third-party media requests such as YouTube embeds during capture, use:

```bash
python screenshot.py --url example.com --variant basic --block-third-party-media
```

This can reduce browser connection prompts, but it can also change the visible layout of pages that rely on embedded video.

## Output structure

Screenshots are grouped per domain first, so runs from different websites do not get mixed together.

```text
screenshots/
└── example.com/
    ├── report.json
    ├── report.csv
    └── 2026-03-27/
        ├── home/
        │   ├── desktop.png
        │   ├── medium.png
        │   ├── tablet.png
        │   └── mobile.png
        ├── about-the-initiative/
        └── index.html
```

## Command reference

- `--url`: root URL, bare domain, or sitemap URL
- `--url-file`: path to a text file with one website or sitemap entry per line
- `--variant basic`: practical reduced screenshot set
- `--variant extended`: more detailed breakpoint coverage
- `--include`: only process URLs containing one or more path fragments
- `--exclude`: skip URLs containing one or more path fragments
- `--max-urls`: process at most this many URLs after filtering
- `--timeout-profile`: choose `normal` or `slow` timing behavior
- `--generate-index`: creates an HTML gallery of screenshots
- `--no-open`: do not open the output automatically after a successful run
- `--output`: custom output directory
- `--only-failed`: rerun only pages that failed previously
- `--retries`: number of retries per page and viewport
- `--concurrency`: number of pages processed in parallel

## Report notes

`report.json` and `report.csv` now also include a few extra diagnostics:

- `redirected`: whether the final page target differs meaningfully from the requested URL
- `result_flags`: simple markers such as `redirected`, `very_low_content` or `likely_blocking_overlay`
- `extra_stabilization_pass`: whether the script used an extra recovery pass before taking the screenshot

These flags do not automatically fail a page, but they help spot pages that deserve a manual check.

When `--block-third-party-media` is used and third-party media requests such as YouTube embeds are blocked during capture, the report can include `third_party_media_blocked`.

## Versioning

This project is now under Git. The recommended `.gitignore` is:

```gitignore
.venv/
screenshots/
.DS_Store
```

## GitHub recommendation

Use Git locally and push to GitHub under your Webfixers account. That gives you:

- version history
- rollback points
- backup
- a clean base for future improvements like launcher files or a GUI

## Troubleshooting

### `python: command not found`

Use `python3` for creating the virtual environment. Inside the activated virtual environment, `python` should work normally.

### `No module named playwright`

This usually means the virtual environment is not active. Run:

```bash
cd "/path/to/playwright-screenshots"
source .venv/bin/activate
```

### `python not found` after moving the project folder

The virtual environment may contain references to the old location. Recreate it in the new folder:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install playwright aiohttp
python -m playwright install
```

### You are unsure which Python is active

Check with:

```bash
which python
```

When the virtual environment is active, it should point to a path ending in `.venv/bin/python` inside your project folder.

## Roadmap

Likely future improvements are:

- further investigation into true full-page capture on especially long pages
- a lightweight GUI for non-technical daily use
