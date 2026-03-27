"""
Playwright-based website screenshot tool
=======================================

This script crawls one or more `sitemap.xml` files for a given website, filters
the resulting URLs and then produces full‑page screenshots for a set of
viewport sizes. It is intended to capture a visual baseline of a live site
for design or QA purposes.

Key features
------------

* Understands both `urlset` and `sitemapindex` structures and recurses into
  nested sitemaps.
* Filters out admin pages, feeds, querystring variants, anchors and common
  document types (PDF, images, etc.).
* Generates screenshots in either a **basic** or **extended** viewport set
  inspired by Beaver Builder breakpoints.
* Waits for pages to become idle, scrolls to trigger lazy loading and hides
  or removes common overlays (cookie banners, newsletters, modals, etc.) via
  CSS injection.
* Writes results to a JSON/CSV report and optionally builds an HTML index to
  quickly browse the captured images.
* Supports retrying failed URLs without stopping the entire run.

Usage example
-------------

```
python screenshot.py --url https://example.com --variant basic --output screenshots
```

See the accompanying README for more details.

"""

import argparse
import asyncio
import csv
import datetime
import json
import os
import re
import sys
from collections import Counter
from html import escape
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import aiohttp
from playwright.async_api import async_playwright, Browser, Page, Response


def slugify(url: str) -> str:
    """Convert a URL into a filesystem-safe slug.

    Strips the scheme and domain, removes fragments and query strings and
    replaces disallowed characters with hyphens. If the path is empty the
    slug `home` is returned.
    """
    parsed = urlparse(url)
    path = parsed.path
    if not path or path == '/':
        return 'home'
    path = path.strip('/')
    slug = re.sub(r'[^A-Za-z0-9_\-]+', '-', path)
    slug = re.sub(r'-{2,}', '-', slug)
    return slug[:200] if slug else 'page'


def domain_slug(root_url: str) -> str:
    """Convert a URL into a filesystem-safe domain folder name."""
    parsed = urlparse(root_url)
    host = parsed.netloc or parsed.path
    host = host.lower().strip()
    host = host.split('@')[-1]
    host = host.split(':')[0]
    host = host.strip('/')
    if host.startswith('www.'):
        host = host[4:]
    host = re.sub(r'[^a-z0-9._-]+', '-', host)
    host = re.sub(r'-{2,}', '-', host)
    return host or 'site'


def build_output_paths(base_output_dir: str, root_url: str, date_str: str) -> Dict[str, str]:
    """Build the output folder structure for a single domain.

    Layout:
    base_output_dir/
      domain/
        report.json
        report.csv
        YYYY-MM-DD/
          page-slug/
            viewport.png
          index.html
    """
    domain_dir = os.path.join(base_output_dir, domain_slug(root_url))
    run_dir = os.path.join(domain_dir, date_str)
    return {
        'base_output_dir': base_output_dir,
        'domain_dir': domain_dir,
        'run_dir': run_dir,
        'report_json': os.path.join(domain_dir, 'report.json'),
        'report_csv': os.path.join(domain_dir, 'report.csv'),
        'index_html': os.path.join(run_dir, 'index.html'),
    }


def is_relevant(url: str) -> bool:
    """Return True if the URL should be processed.

    Filters out WordPress admin/login pages, feeds, query strings, anchors and
    common file types such as PDFs and images.
    """
    lowered = url.lower()
    if any(part in lowered for part in ('wp-admin', 'wp-login', 'preview', 'login')):
        return False
    if 'feed' in lowered:
        return False
    if '?' in url or '#' in url:
        return False
    if re.search(r'\.(pdf|jpg|jpeg|png|gif|svg|webp|mp4|zip)$', lowered):
        return False
    return True


async def fetch_xml(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch XML content from a URL with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                return await resp.text()
        except Exception as exc:
            if attempt < retries - 1:
                await asyncio.sleep(1)
                continue
            raise exc


async def parse_sitemaps(root_url: str) -> Set[str]:
    """Recursively fetch and parse the sitemap(s) for a website."""
    seen_sitemaps: Set[str] = set()
    urls: Set[str] = set()

    async def _parse(url: str, session: aiohttp.ClientSession) -> None:
        if url in seen_sitemaps:
            return
        seen_sitemaps.add(url)
        try:
            xml_content = await fetch_xml(session, url)
        except Exception as e:
            print(f"Failed to fetch sitemap {url}: {e}", file=sys.stderr)
            return
        try:
            import xml.etree.ElementTree as ET
            tree = ET.fromstring(xml_content)
        except Exception as e:
            print(f"Failed to parse sitemap XML {url}: {e}", file=sys.stderr)
            return
        tag = tree.tag.lower().split('}')[-1]
        if tag == 'sitemapindex':
            for sitemap in tree.findall('.//{*}sitemap'):
                loc_elem = sitemap.find('{*}loc')
                if loc_elem is not None and loc_elem.text:
                    await _parse(loc_elem.text.strip(), session)
        elif tag == 'urlset':
            for url_elem in tree.findall('{*}url'):
                loc = url_elem.find('{*}loc')
                if loc is not None and loc.text:
                    page_url = loc.text.strip()
                    if is_relevant(page_url):
                        urls.add(page_url)

    async with aiohttp.ClientSession() as session:
        parsed = urlparse(root_url)
        sitemap_url = root_url if parsed.path and parsed.path.endswith('.xml') else root_url.rstrip('/') + '/sitemap.xml'
        await _parse(sitemap_url, session)
    return urls


async def hide_overlays_and_disable_animations(page: Page) -> None:
    """Inject CSS to hide common overlays and disable animations."""
    disable_css = """
        *, *::before, *::after {
            animation-duration: 0s !important;
            transition-duration: 0s !important;
            animation-delay: 0s !important;
            transition-delay: 0s !important;
        }
    """
    overlay_selectors = [
        '[id*="cookie"]', '[class*="cookie"]', '[id*="gdpr"]', '[class*="gdpr"]',
        '[class*="modal"]', '[id*="modal"]', '[class*="popup"]', '[id*="popup"]',
        '[class*="newsletter"]', '[id*="newsletter"]', '[class*="subscribe"]',
        '[id*="subscribe"]', '[class*="chat"]', '[id*="chat"]', '[class*="sticky"]',
        '[class*="banner"]', '[id*="banner"]', '[class*="floating"]', '[id*="floating"]'
    ]
    overlay_css = '\n'.join(
        f"{sel} {{ display: none !important; visibility: hidden !important; }}"
        for sel in overlay_selectors
    )
    await page.add_style_tag(content=disable_css + overlay_css)


async def scroll_to_bottom(page: Page) -> None:
    """Scroll down the page gradually to trigger lazy loaded content."""
    await page.evaluate("""
        async () => {
            return await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 500;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= document.body.scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 250);
            });
        }
    """)


async def process_url(
    browser: Browser,
    url: str,
    viewports: List[Tuple[str, int, int]],
    run_dir: str,
    report: List[Dict[str, Optional[str]]],
    sitemap_source: str,
    retries: int,
    page_index: int,
    total_pages: int,
) -> None:
    """Capture screenshots for a single URL across all viewports."""
    slug = slugify(url)
    page_dir = os.path.join(run_dir, slug)
    os.makedirs(page_dir, exist_ok=True)
    print(f"[{page_index}/{total_pages}] Starting {url}")

    page_successes = 0
    page_failures = 0

    for viewport_index, (vp_name, width, height) in enumerate(viewports, start=1):
        success = False
        final_url = None
        status_code: Optional[int] = None
        page_title: Optional[str] = None
        error_msg: Optional[str] = None
        screenshot_path = os.path.join(page_dir, f"{vp_name}.png")
        attempt = 0
        context = None

        print(
            f"[{page_index}/{total_pages}] {slug} -> viewport {viewport_index}/{len(viewports)}: "
            f"{vp_name} ({width}x{height})"
        )

        while attempt <= retries and not success:
            try:
                context = await browser.new_context(viewport={"width": width, "height": height})
                page = await context.new_page()
                response: Optional[Response] = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                try:
                    await page.wait_for_load_state('networkidle', timeout=30000)
                except Exception:
                    pass
                final_url = page.url
                status_code = response.status if response else None
                page_title = await page.title()
                await hide_overlays_and_disable_animations(page)
                await scroll_to_bottom(page)
                await page.wait_for_timeout(1000)
                await page.screenshot(path=screenshot_path, full_page=True)
                success = True
                page_successes += 1
                print(f"[{page_index}/{total_pages}] Saved {vp_name}: {os.path.relpath(screenshot_path, run_dir)}")
            except Exception as exc:
                error_msg = str(exc)
                attempt += 1
                if attempt <= retries:
                    print(
                        f"[{page_index}/{total_pages}] Retry {attempt}/{retries} for {url} [{vp_name}] "
                        f"after error: {error_msg}",
                        file=sys.stderr,
                    )
                else:
                    page_failures += 1
                    print(
                        f"[{page_index}/{total_pages}] Failed {url} [{vp_name}]: {error_msg}",
                        file=sys.stderr,
                    )
            finally:
                if context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass
                    context = None

        report.append({
            'url': url,
            'final_url': final_url,
            'status': 'success' if success else 'failed',
            'http_status': status_code,
            'page_title': page_title,
            'viewport': vp_name,
            'sitemap_source': sitemap_source,
            'screenshot_path': os.path.relpath(screenshot_path, run_dir) if success else '',
            'error': error_msg,
        })

    print(
        f"[{page_index}/{total_pages}] Finished {url} | "
        f"successful viewports: {page_successes}, failed viewports: {page_failures}"
    )


def generate_html_index(report: List[Dict[str, Optional[str]]], run_dir: str, date_str: str) -> None:
    """Generate a simple HTML index to browse the captured screenshots."""
    index_path = os.path.join(run_dir, 'index.html')
    page_entries: Dict[str, List[Dict[str, str]]] = {}
    for entry in report:
        if entry['status'] != 'success':
            continue
        url = entry['url']
        page_entries.setdefault(url, []).append({
            'viewport': entry['viewport'],
            'path': entry['screenshot_path'],
            'title': entry.get('page_title') or '',
        })
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="UTF-8">',
        '<title>Screenshot Index</title>',
        '<style>',
        'body { font-family: Arial, sans-serif; padding: 20px; }',
        'h2 { margin-top: 40px; }',
        'img { max-width: 100%; border: 1px solid #ccc; margin-bottom: 20px; }',
        '.viewport { margin-bottom: 10px; font-weight: bold; }',
        '</style>',
        '</head>',
        '<body>',
        f'<h1>Screenshot Index ({date_str})</h1>'
    ]
    for url, shots in page_entries.items():
        html_parts.append(f'<h2>{escape(url)}</h2>')
        for shot in sorted(shots, key=lambda x: x['viewport']):
            html_parts.append(f'<div class="viewport">{escape(shot["viewport"])} ({escape(shot["title"])})</div>')
            html_parts.append(f'<img src="{escape(shot["path"]).replace(os.sep, "/")}" alt="{escape(shot["viewport"])}">')
    html_parts.append('</body></html>')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    print(f"Generated HTML index at {index_path}")


async def main() -> None:
    parser = argparse.ArgumentParser(description='Website screenshotter using Playwright.')
    parser.add_argument('--url', required=True, help='Root URL of the website (e.g. https://example.com) or a sitemap.xml URL.')
    parser.add_argument('--variant', choices=['basic', 'extended'], default='basic',
                        help='Screenshot set to use (default: basic).')
    parser.add_argument('--output', default='screenshots', help='Base output directory for screenshots and reports.')
    parser.add_argument('--retries', type=int, default=2, help='Number of retries for each page/viewport (default: 2).')
    parser.add_argument('--only-failed', action='store_true',
                        help='Reprocess only pages marked as failed in the last report.json file for this domain.')
    parser.add_argument('--generate-index', action='store_true',
                        help='Generate an HTML index page to browse the screenshots.')
    parser.add_argument('--concurrency', type=int, default=1,
                        help='Number of pages to process concurrently (default: 1). Concurrency >1 may increase memory usage.')
    args = parser.parse_args()

    basic_viewports = [
        ('desktop', 1400, 900),
        ('medium', 1199, 900),
        ('tablet', 991, 1200),
        ('mobile', 767, 1400),
    ]
    extended_viewports = [
        ('desktop-wide', 1400, 900),
        ('desktop-breakpoint', 1200, 900),
        ('medium-below', 1199, 900),
        ('tablet-breakpoint', 992, 1200),
        ('tablet-below', 991, 1200),
        ('mobile-breakpoint', 768, 1400),
        ('mobile-below', 767, 1400),
    ]
    viewports = basic_viewports if args.variant == 'basic' else extended_viewports
    date_str = datetime.date.today().strftime('%Y-%m-%d')

    paths = build_output_paths(args.output, args.url, date_str)
    os.makedirs(paths['domain_dir'], exist_ok=True)
    os.makedirs(paths['run_dir'], exist_ok=True)

    print(f"Output folder for this domain: {paths['domain_dir']}")
    print(f"Run folder for today: {paths['run_dir']}")

    urls: List[str] = []
    sitemap_source = args.url
    if args.only_failed:
        report_path = paths['report_json']
        if not os.path.exists(report_path):
            print('No report.json found for this domain. Cannot use --only-failed.', file=sys.stderr)
            return
        with open(report_path, 'r', encoding='utf-8') as f:
            past_report = json.load(f)
        failed_urls: Set[str] = {entry['url'] for entry in past_report if entry['status'] != 'success'}
        urls = sorted(failed_urls)
        print(f'Rerunning {len(urls)} previously failed URLs for this domain...')
    else:
        print('Fetching sitemap(s)...')
        sitemap_urls = await parse_sitemaps(args.url)
        print(f'Found {len(sitemap_urls)} URLs in sitemap(s).')
        urls = sorted(sitemap_urls)

    total_pages = len(urls)
    if total_pages == 0:
        print('No URLs to process.', file=sys.stderr)
        return

    report: List[Dict[str, Optional[str]]] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        if args.concurrency > 1:
            semaphore = asyncio.Semaphore(args.concurrency)

            async def worker(page_index: int, page_url: str) -> None:
                async with semaphore:
                    await process_url(
                        browser, page_url, viewports, paths['run_dir'], report,
                        sitemap_source, args.retries, page_index, total_pages
                    )

            tasks = [
                asyncio.create_task(worker(index, page_url))
                for index, page_url in enumerate(urls, start=1)
            ]
            await asyncio.gather(*tasks)
        else:
            for index, page_url in enumerate(urls, start=1):
                await process_url(
                    browser, page_url, viewports, paths['run_dir'], report,
                    sitemap_source, args.retries, index, total_pages
                )
        await browser.close()

    with open(paths['report_json'], 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Wrote JSON report to {paths['report_json']}")

    with open(paths['report_csv'], 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['url', 'final_url', 'status', 'http_status', 'page_title', 'viewport', 'sitemap_source', 'screenshot_path', 'error']
        )
        writer.writeheader()
        for row in report:
            writer.writerow(row)
    print(f"Wrote CSV report to {paths['report_csv']}")

    if args.generate_index:
        generate_html_index(report, paths['run_dir'], date_str)

    status_counts = Counter(entry['status'] for entry in report)
    successful_pages = len({entry['url'] for entry in report if entry['status'] == 'success'})
    failed_pages = len({entry['url'] for entry in report if entry['status'] == 'failed'})
    print('Run complete.')
    print(
        f"Pages processed: {total_pages} | Pages with at least one successful viewport: {successful_pages} | "
        f"Pages with failed viewports: {failed_pages}"
    )
    print(
        f"Viewport results -> success: {status_counts.get('success', 0)}, failed: {status_counts.get('failed', 0)}"
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Aborted by user')
