# Playwright Screenshots

A local Python tool to generate full-page screenshots of all relevant pages in a website, based on a root URL or a `sitemap.xml`. It is intended as a practical visual archive after go-live, with screenshot sets tailored to Beaver Builder breakpoints.

## Project location

Your current project folder is:

```text
/Users/mennofink/Library/CloudStorage/GoogleDrive-menno@webfixers.nl/.shortcut-targets-by-id/1snrUQNe2fCBN9HocLIwfJVuVQU4AE_2x/Development/Applicaties/playwright-screenshots
```

## Recommended project structure

Keep the Python script and the virtual environment together in the same project folder.

```text
playwright-screenshots/
├── screenshot.py
├── README.md
├── .gitignore
├── .venv/
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
cd "/Users/mennofink/Library/CloudStorage/GoogleDrive-menno@webfixers.nl/.shortcut-targets-by-id/1snrUQNe2fCBN9HocLIwfJVuVQU4AE_2x/Development/Applicaties/playwright-screenshots"
source .venv/bin/activate
```

Once the prompt shows `(.venv)`, you are ready to run the script.

## Usage

The entry point is `screenshot.py`. You provide a website root URL or sitemap URL and choose either the `basic` or `extended` screenshot set.

### Basic example

```bash
python screenshot.py --url https://example.com/sitemap.xml --variant basic
```

### Extended example

```bash
python screenshot.py --url https://example.com/sitemap.xml --variant extended
```

### Generate a browseable HTML index too

```bash
python screenshot.py --url https://example.com/sitemap.xml --variant basic --generate-index
```

### Example with your current workflow

```bash
cd "/Users/mennofink/Library/CloudStorage/GoogleDrive-menno@webfixers.nl/.shortcut-targets-by-id/1snrUQNe2fCBN9HocLIwfJVuVQU4AE_2x/Development/Applicaties/playwright-screenshots"
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

- `--url`: root URL or sitemap URL
- `--variant basic`: practical reduced screenshot set
- `--variant extended`: more detailed breakpoint coverage
- `--generate-index`: creates an HTML gallery of screenshots
- `--output`: custom output directory
- `--only-failed`: rerun only pages that failed previously
- `--retries`: number of retries per page and viewport
- `--concurrency`: number of pages processed in parallel

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
cd "/Users/mennofink/Library/CloudStorage/GoogleDrive-menno@webfixers.nl/.shortcut-targets-by-id/1snrUQNe2fCBN9HocLIwfJVuVQU4AE_2x/Development/Applicaties/playwright-screenshots"
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

A good next improvement is to add simple `.command` launcher files, and after that a small graphical interface where you can paste a sitemap URL and choose `Basic` or `Extended`.
