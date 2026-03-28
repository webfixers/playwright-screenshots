# AGENTS.md

## Project
This repository contains a local Playwright-based screenshot tool for capturing website pages from a sitemap across multiple viewport presets.

## Main goals
- Keep the tool reliable and simple to run on macOS.
- Preserve the current workflow for non-technical daily use.
- Prefer small, safe usability improvements over big rewrites.
- Keep the project ready for a future GUI, but do not build the GUI yet unless explicitly asked.

## Current workflow assumptions
- The project is run locally on macOS.
- The project lives in a dedicated project folder.
- The Python virtual environment is expected at `.venv/`.
- The main script is `screenshot.py`.
- The main end-user launcher is `run-screenshots.command`.
- Screenshots are stored under `screenshots/<domain>/<YYYY-MM-DD>/`.
- Domain-level files such as `report.json` and `report.csv` should remain grouped under `screenshots/<domain>/`.

## Development principles
- Make small, reversible changes.
- Prefer backward-compatible improvements.
- Do not break the existing launcher workflow unless explicitly requested.
- Avoid unnecessary dependencies.
- Keep the tool easy to understand for a non-developer user.
- Preserve existing behavior unless there is a clear reason to change it.
- When changing behavior, also update the documentation.

## Git workflow
- Use small, focused commits.
- Write clear commit messages.
- Prefer feature branches for larger changes.
- Do not rewrite history unless explicitly requested.
- Keep tagged versions meaningful and stable.

## macOS compatibility
- Maintain compatibility with macOS Terminal usage.
- Keep `.command` launchers executable and easy to use.
- Prefer solutions that work without requiring heavy setup.
- Be careful with paths that contain spaces.
- Assume the user may move the project folder, so avoid hardcoding paths unless they are intentionally part of a launcher.

## Python and environment rules
- Use the existing `.venv` virtual environment.
- Do not commit `.venv/`.
- Do not commit generated screenshots.
- Keep dependencies minimal.
- If adding a dependency, explain why it is needed and update setup instructions.

## Code style
- Keep code readable and practical.
- Use clear function names.
- Add comments only where they help understanding.
- Write all code comments in English.
- Prefer straightforward logic over clever abstractions.
- Do not introduce large frameworks unless explicitly requested.

## Output and file structure
- Keep screenshots separated by domain.
- Keep per-run screenshots separated by date.
- Do not mix screenshots from different domains in the same folder.
- Preserve `report.json`, `report.csv`, and optional `index.html` behavior unless explicitly changing the reporting design.
- Any new output files should have predictable names and locations.

## UX priorities
When improving the tool, prioritize:
1. Clear progress feedback in Terminal
2. Safe defaults
3. Minimal user input
4. Easy repeatability
5. Easy inspection of output

## Preferred next-step direction
Preferred improvements, in roughly this order:
1. Smarter launcher options
2. Better URL filtering and confirmation before very large runs
3. Automatically opening the output folder or report after completion
4. Investigation of true full-page screenshot capture for long pages
5. Future lightweight GUI

## Full-page screenshot follow-up
A known future improvement is to investigate why long pages are not always captured completely in a single screenshot and whether true full-page capture can be added, similar to browser tools like GoFullPage.

## Documentation rules
- Keep `README.md` aligned with real usage.
- Update README when setup, launcher behavior, output structure, or commands change.
- Prefer practical examples over abstract explanation.

## Safety and scope
- Do not add cloud services or remote storage unless explicitly requested.
- Do not add telemetry or tracking.
- Do not add automatic deletion of screenshots unless explicitly requested.
- Do not remove existing files automatically without making that behavior explicit.

## When making changes
Before finalizing work:
- check that the launcher still works
- check that the script still runs from the virtual environment
- check that output still lands in the expected domain/date structure
- update README if needed
- suggest a sensible commit message
