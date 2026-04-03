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
import subprocess
import sys
from collections import Counter
from html import escape
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse

import aiohttp
from playwright.async_api import async_playwright, Browser, Page, Response


EVENT_PREFIX = 'EVENT_JSON:'
ACTIVE_EVENT_STREAM: Optional[str] = None


TIMEOUT_PROFILES: Dict[str, Dict[str, int]] = {
    'normal': {
        'request_timeout_ms': 30000,
        'playwright_start_timeout_ms': 15000,
        'browser_launch_timeout_ms': 30000,
        'goto_timeout_ms': 60000,
        'initial_networkidle_timeout_ms': 30000,
        'post_scroll_networkidle_timeout_ms': 5000,
        'stable_height_interval_ms': 400,
        'scroll_pause_ms': 250,
        'final_wait_ms': 750,
    },
    'slow': {
        'request_timeout_ms': 60000,
        'playwright_start_timeout_ms': 30000,
        'browser_launch_timeout_ms': 60000,
        'goto_timeout_ms': 90000,
        'initial_networkidle_timeout_ms': 45000,
        'post_scroll_networkidle_timeout_ms': 15000,
        'stable_height_interval_ms': 700,
        'scroll_pause_ms': 500,
        'final_wait_ms': 1500,
    },
}

OVERLAY_SELECTORS = [
    '[id*="cookie"]', '[class*="cookie"]',
    '[id*="consent"]', '[class*="consent"]',
    '[id*="gdpr"]', '[class*="gdpr"]',
    '[class*="modal"]', '[id*="modal"]',
    '[class*="popup"]', '[id*="popup"]',
    '[class*="newsletter"]', '[id*="newsletter"]',
    '[class*="subscribe"]', '[id*="subscribe"]',
    '[class*="chat"]', '[id*="chat"]',
    '[id*="onetrust"]', '[class*="onetrust"]',
    '[id*="complianz"]', '[class*="complianz"]',
    '[id*="cookiebot"]', '[class*="cookiebot"]',
    '[aria-modal="true"]',
]

SECOND_PASS_FLAGS = {
    'body_hidden',
    'document_hidden',
    'very_low_content',
    'likely_blocking_overlay',
    'tiny_page_height',
}

BLOCKED_MEDIA_HOSTS = (
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'youtube-nocookie.com',
    'www.youtube-nocookie.com',
    'youtu.be',
    'ytimg.com',
    'i.ytimg.com',
    's.ytimg.com',
    'googlevideo.com',
)


def emit_event(event_name: str, **payload: Any) -> None:
    """Emit a machine-readable event for native app integrations."""
    if ACTIVE_EVENT_STREAM != 'jsonl':
        return
    event_payload = {
        'event': event_name,
        **payload,
    }
    print(f"{EVENT_PREFIX}{json.dumps(event_payload, ensure_ascii=False)}", flush=True)


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


def canonical_page_target(url: Optional[str]) -> Tuple[str, str]:
    """Return a normalized host/path pair for redirect comparison."""
    if not url:
        return '', '/'
    parsed = urlparse(url)
    host = (parsed.netloc or parsed.path).lower().strip()
    host = host.split('@')[-1].split(':')[0].strip('/')
    if host.startswith('www.'):
        host = host[4:]
    path = parsed.path or '/'
    path = path.rstrip('/') or '/'
    return host, path


def has_meaningful_redirect(input_url: str, final_url: Optional[str]) -> bool:
    """Return True when the final page target differs beyond scheme or trailing slash."""
    return canonical_page_target(input_url) != canonical_page_target(final_url)


def blocked_media_host(url: str) -> str:
    """Return the blocked media host for a request URL, or an empty string."""
    hostname = (urlparse(url).hostname or '').lower()
    for blocked_host in BLOCKED_MEDIA_HOSTS:
        normalized = blocked_host.lower()
        if hostname == normalized or hostname.endswith('.' + normalized):
            return normalized
    return ''


def normalize_input_url(raw_input: str) -> str:
    """Normalize user input into an absolute URL-like string."""
    value = raw_input.strip()
    if not value:
        return value
    if value.startswith('//'):
        value = 'https:' + value
    if not re.match(r'^[A-Za-z][A-Za-z0-9+.\-]*://', value):
        value = 'https://' + value.lstrip('/')

    parsed = urlparse(value)
    scheme = (parsed.scheme or 'https').lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or ''

    if not path or path == '/':
        return f"{scheme}://{netloc}"

    return urlunparse((scheme, netloc, path, '', parsed.query, ''))


def build_url_variants(normalized_url: str) -> List[str]:
    """Build a small set of likely working URL variants from user input."""
    parsed = urlparse(normalized_url)
    hostname = parsed.hostname or ''
    if not hostname:
        return [normalized_url]

    schemes = [parsed.scheme]
    if parsed.scheme == 'https':
        schemes.append('http')
    elif parsed.scheme == 'http':
        schemes.append('https')

    hostnames = [hostname]
    if hostname.startswith('www.'):
        hostnames.append(hostname[4:])
    else:
        hostnames.append('www.' + hostname)

    variants: List[str] = []
    for scheme in schemes:
        for candidate_hostname in hostnames:
            host = candidate_hostname
            if parsed.port:
                host = f"{candidate_hostname}:{parsed.port}"
            candidate = urlunparse((scheme, host, parsed.path or '', '', parsed.query, ''))
            if not parsed.path or parsed.path == '/':
                candidate = f"{scheme}://{host}"
            if candidate not in variants:
                variants.append(candidate)
    return variants


def build_sitemap_candidate_urls(user_input: str) -> List[str]:
    """Build sitemap URLs to try from flexible user input."""
    normalized_url = normalize_input_url(user_input)
    variants = build_url_variants(normalized_url)
    candidates: List[str] = []

    for variant in variants:
        parsed = urlparse(variant)
        if parsed.path.lower().endswith('.xml'):
            if variant not in candidates:
                candidates.append(variant)
            continue

        root = variant.rstrip('/')
        for suffix in ('/sitemap.xml', '/sitemap_index.xml'):
            candidate = root + suffix
            if candidate not in candidates:
                candidates.append(candidate)

    return candidates


def load_url_inputs(file_path: str) -> List[str]:
    """Load website inputs from a text file, ignoring blank lines and comments."""
    urls: List[str] = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            urls.append(line)
    return urls


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


def parse_filter_terms(raw_terms: Optional[List[str]]) -> List[str]:
    """Normalize include/exclude filter terms from repeated or comma-separated input."""
    terms: List[str] = []
    for raw_term in raw_terms or []:
        for part in raw_term.split(','):
            term = part.strip().lower()
            if term and term not in terms:
                terms.append(term)
    return terms


def apply_url_filters(
    urls: List[str],
    include_terms: List[str],
    exclude_terms: List[str],
    max_urls: Optional[int],
) -> Tuple[List[str], Dict[str, int]]:
    """Apply include/exclude filtering and optional max URL limit."""
    filtered_urls: List[str] = []

    for url in urls:
        lowered_url = url.lower()
        if include_terms and not any(term in lowered_url for term in include_terms):
            continue
        if exclude_terms and any(term in lowered_url for term in exclude_terms):
            continue
        filtered_urls.append(url)

    selected_urls = filtered_urls[:max_urls] if max_urls else filtered_urls
    return selected_urls, {
        'original_total': len(urls),
        'after_filters': len(filtered_urls),
        'filtered_out': len(urls) - len(filtered_urls),
        'limited_out': len(filtered_urls) - len(selected_urls),
    }


async def fetch_xml(session: aiohttp.ClientSession, url: str, request_timeout_ms: int) -> str:
    """Fetch XML content from a URL with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=request_timeout_ms / 1000)) as resp:
                resp.raise_for_status()
                return await resp.text()
        except Exception as exc:
            if attempt < retries - 1:
                await asyncio.sleep(1)
                continue
            raise exc


async def parse_sitemaps(root_url: str, request_timeout_ms: int) -> Tuple[Set[str], Optional[str]]:
    """Recursively fetch and parse sitemap candidates for a website."""

    async def _parse(url: str, session: aiohttp.ClientSession, seen_sitemaps: Set[str], urls: Set[str]) -> bool:
        if url in seen_sitemaps:
            return True
        seen_sitemaps.add(url)
        try:
            xml_content = await fetch_xml(session, url, request_timeout_ms)
        except Exception as e:
            return False
        try:
            import xml.etree.ElementTree as ET
            tree = ET.fromstring(xml_content)
        except Exception as e:
            print(f"Failed to parse sitemap XML {url}: {e}", file=sys.stderr)
            return False
        tag = tree.tag.lower().split('}')[-1]
        if tag == 'sitemapindex':
            for sitemap in tree.findall('.//{*}sitemap'):
                loc_elem = sitemap.find('{*}loc')
                if loc_elem is not None and loc_elem.text:
                    await _parse(loc_elem.text.strip(), session, seen_sitemaps, urls)
        elif tag == 'urlset':
            for url_elem in tree.findall('{*}url'):
                loc = url_elem.find('{*}loc')
                if loc is not None and loc.text:
                    page_url = loc.text.strip()
                    if is_relevant(page_url):
                        urls.add(page_url)
        return True

    candidate_sitemaps = build_sitemap_candidate_urls(root_url)
    async with aiohttp.ClientSession() as session:
        for sitemap_url in candidate_sitemaps:
            seen_sitemaps: Set[str] = set()
            urls: Set[str] = set()
            success = await _parse(sitemap_url, session, seen_sitemaps, urls)
            if success:
                return urls, sitemap_url

    tried = ', '.join(candidate_sitemaps)
    print(f"Failed to fetch a sitemap from: {tried}", file=sys.stderr)
    return set(), None


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
    overlay_css = '\n'.join(
        f"{sel} {{ display: none !important; visibility: hidden !important; }}"
        for sel in OVERLAY_SELECTORS
    )
    helper_css = """
        [data-playwright-blocking-overlay="true"] {
            display: none !important;
            visibility: hidden !important;
        }
        html[data-playwright-reset-overflow="true"],
        body[data-playwright-reset-overflow="true"] {
            overflow: auto !important;
        }
    """
    await page.add_style_tag(content=disable_css + overlay_css + helper_css)
    await page.evaluate("""
        () => {
            const tokenPattern = /(cookie|consent|gdpr|modal|popup|newsletter|subscribe|chat|intercom|drift|hubspot|onetrust|complianz|cookiebot)/i;
            const viewportArea = Math.max(1, (window.innerWidth || 1) * (window.innerHeight || 1));

            for (const element of Array.from(document.querySelectorAll('body *'))) {
                if (!(element instanceof HTMLElement)) {
                    continue;
                }

                const style = getComputedStyle(element);
                const descriptor = [
                    element.id,
                    element.className,
                    element.getAttribute('role'),
                    element.getAttribute('aria-label'),
                    element.getAttribute('data-testid'),
                ].filter(Boolean).join(' ');

                const rect = element.getBoundingClientRect();
                const areaRatio = (Math.max(0, rect.width) * Math.max(0, rect.height)) / viewportArea;
                const isFixedLike = style.position === 'fixed' || style.position === 'sticky';
                const zIndex = Number.parseInt(style.zIndex || '0', 10);
                const looksLarge = areaRatio >= 0.12 || rect.height >= (window.innerHeight || 0) * 0.22;
                const tokenMatch = tokenPattern.test(descriptor);
                const ariaModal = element.getAttribute('aria-modal') === 'true';

                if ((tokenMatch && isFixedLike && looksLarge) || (ariaModal && looksLarge) || (tokenMatch && zIndex >= 100 && looksLarge)) {
                    element.setAttribute('data-playwright-blocking-overlay', 'true');
                }
            }

            for (const root of [document.documentElement, document.body]) {
                if (!(root instanceof HTMLElement)) {
                    continue;
                }
                if (getComputedStyle(root).overflow === 'hidden') {
                    root.setAttribute('data-playwright-reset-overflow', 'true');
                }
            }
        }
    """)


async def collect_page_state(page: Page) -> Dict[str, Any]:
    """Collect lightweight page metrics to spot suspiciously blank results."""
    return await page.evaluate("""
        () => {
            const root = document.scrollingElement || document.documentElement || document.body;
            const body = document.body;
            const html = document.documentElement;
            const bodyStyle = body ? getComputedStyle(body) : null;
            const htmlStyle = html ? getComputedStyle(html) : null;
            const text = body && body.innerText ? body.innerText.trim() : '';
            const htmlLength = body && body.innerHTML ? body.innerHTML.length : 0;
            const overlayCount = document.querySelectorAll('[data-playwright-blocking-overlay="true"]').length;
            return {
                body_text_length: text.length,
                body_html_length: htmlLength,
                body_hidden: !!(bodyStyle && (bodyStyle.display === 'none' || bodyStyle.visibility === 'hidden' || bodyStyle.opacity === '0')),
                document_hidden: !!(htmlStyle && (htmlStyle.display === 'none' || htmlStyle.visibility === 'hidden' || htmlStyle.opacity === '0')),
                scroll_height: Math.max(
                    root ? root.scrollHeight : 0,
                    html ? html.scrollHeight : 0,
                    body ? body.scrollHeight : 0
                ),
                viewport_height: window.innerHeight || 0,
                main_like_elements: document.querySelectorAll('main, [role="main"], article').length,
                blocking_overlay_count: overlayCount,
            };
        }
    """)


def analyze_page_state(
    input_url: str,
    final_url: Optional[str],
    status_code: Optional[int],
    page_title: Optional[str],
    page_state: Dict[str, Any],
) -> List[str]:
    """Translate page metrics into readable report flags."""
    flags: List[str] = []

    if has_meaningful_redirect(input_url, final_url):
        flags.append('redirected')
    if status_code is not None and status_code >= 400:
        flags.append(f'http_{status_code}')
    if page_state.get('body_hidden'):
        flags.append('body_hidden')
    if page_state.get('document_hidden'):
        flags.append('document_hidden')

    body_text_length = int(page_state.get('body_text_length') or 0)
    body_html_length = int(page_state.get('body_html_length') or 0)
    scroll_height = int(page_state.get('scroll_height') or 0)
    viewport_height = int(page_state.get('viewport_height') or 0)
    main_like_elements = int(page_state.get('main_like_elements') or 0)
    blocking_overlay_count = int(page_state.get('blocking_overlay_count') or 0)

    if body_text_length < 40 and body_html_length < 2000:
        flags.append('very_low_content')
    if scroll_height <= max(viewport_height + 20, 200) and body_text_length < 80 and main_like_elements == 0:
        flags.append('tiny_page_height')
    if blocking_overlay_count > 0 and body_text_length < 200:
        flags.append('likely_blocking_overlay')
    if not (page_title or '').strip():
        flags.append('empty_title')

    return flags


async def run_additional_stabilization_pass(page: Page, timing_profile: Dict[str, int]) -> None:
    """Run one extra settling pass for pages that still look suspicious."""
    await hide_overlays_and_disable_animations(page)
    await page.wait_for_timeout(timing_profile['final_wait_ms'])
    await scroll_to_bottom(page, timing_profile)
    try:
        await page.wait_for_load_state(
            'networkidle',
            timeout=timing_profile['post_scroll_networkidle_timeout_ms'],
        )
    except Exception:
        pass
    await wait_for_stable_page_height(
        page,
        checks_needed=4,
        interval_ms=timing_profile['stable_height_interval_ms'],
        max_checks=12,
    )
    await page.wait_for_timeout(timing_profile['final_wait_ms'])


async def wait_for_stable_page_height(
    page: Page,
    checks_needed: int = 3,
    interval_ms: int = 400,
    max_checks: int = 10,
) -> None:
    """Wait until the page height stops growing for a few consecutive checks."""
    stable_checks = 0
    last_height = -1

    for _ in range(max_checks):
        current_height = await page.evaluate("""
            () => {
                const root = document.scrollingElement || document.documentElement || document.body;
                return Math.max(
                    root ? root.scrollHeight : 0,
                    document.documentElement ? document.documentElement.scrollHeight : 0,
                    document.body ? document.body.scrollHeight : 0
                );
            }
        """)
        if current_height == last_height:
            stable_checks += 1
            if stable_checks >= checks_needed:
                return
        else:
            stable_checks = 0
            last_height = current_height
        await page.wait_for_timeout(interval_ms)


async def scroll_to_bottom(page: Page, timing_profile: Dict[str, int]) -> None:
    """Scroll down the page gradually and settle long pages before capture."""
    await page.evaluate("""
        async (scrollPauseMs) => {
            const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
            const getRoot = () => document.scrollingElement || document.documentElement || document.body;

            let lastHeight = 0;
            let stableBottomChecks = 0;

            for (let step = 0; step < 60; step += 1) {
                const root = getRoot();
                const viewportHeight = window.innerHeight || 800;
                const distance = Math.max(400, Math.floor(viewportHeight * 0.85));
                window.scrollBy(0, distance);
                await sleep(scrollPauseMs);

                const currentRoot = getRoot();
                const currentHeight = Math.max(
                    currentRoot ? currentRoot.scrollHeight : 0,
                    document.documentElement ? document.documentElement.scrollHeight : 0,
                    document.body ? document.body.scrollHeight : 0
                );
                const scrollTop = currentRoot ? currentRoot.scrollTop : window.scrollY;
                const maxScrollTop = Math.max(0, currentHeight - viewportHeight);
                const nearBottom = scrollTop >= maxScrollTop - 5;

                if (nearBottom && currentHeight <= lastHeight) {
                    stableBottomChecks += 1;
                } else {
                    stableBottomChecks = 0;
                }

                lastHeight = currentHeight;

                if (stableBottomChecks >= 2) {
                    break;
                }
            }

            window.scrollTo(0, 0);
        }
    """, timing_profile['scroll_pause_ms'])
    await wait_for_stable_page_height(page, interval_ms=timing_profile['stable_height_interval_ms'])


async def process_url(
    browser: Browser,
    url: str,
    viewports: List[Tuple[str, int, int]],
    run_dir: str,
    report: List[Dict[str, Any]],
    sitemap_source: str,
    retries: int,
    timing_profile: Dict[str, int],
    block_third_party_media: bool,
    page_index: int,
    total_pages: int,
) -> None:
    """Capture screenshots for a single URL across all viewports."""
    slug = slugify(url)
    page_dir = os.path.join(run_dir, slug)
    os.makedirs(page_dir, exist_ok=True)
    print(f"[{page_index}/{total_pages}] Starting {url}")
    emit_event(
        'page_started',
        page_index=page_index,
        total_pages=total_pages,
        url=url,
        slug=slug,
    )

    page_successes = 0
    page_failures = 0

    for viewport_index, (vp_name, width, height) in enumerate(viewports, start=1):
        success = False
        final_url = None
        status_code: Optional[int] = None
        page_title: Optional[str] = None
        error_msg: Optional[str] = None
        result_flags: List[str] = []
        page_state: Dict[str, Any] = {}
        extra_stabilization_used = False
        blocked_hosts: Set[str] = set()
        screenshot_path = os.path.join(page_dir, f"{vp_name}.png")
        attempt = 0
        context = None

        print(
            f"[{page_index}/{total_pages}] {slug} -> viewport {viewport_index}/{len(viewports)}: "
            f"{vp_name} ({width}x{height})"
        )
        emit_event(
            'viewport_started',
            page_index=page_index,
            total_pages=total_pages,
            viewport_index=viewport_index,
            total_viewports=len(viewports),
            url=url,
            slug=slug,
            viewport=vp_name,
            width=width,
            height=height,
        )

        while attempt <= retries and not success:
            try:
                context = await browser.new_context(viewport={"width": width, "height": height})

                if block_third_party_media:
                    async def handle_route(route) -> None:
                        host = blocked_media_host(route.request.url)
                        if host:
                            blocked_hosts.add(host)
                            await route.abort()
                            return
                        await route.continue_()

                    await context.route('**/*', handle_route)
                page = await context.new_page()
                response: Optional[Response] = await page.goto(
                    url,
                    wait_until='domcontentloaded',
                    timeout=timing_profile['goto_timeout_ms'],
                )
                try:
                    await page.wait_for_load_state(
                        'networkidle',
                        timeout=timing_profile['initial_networkidle_timeout_ms'],
                    )
                except Exception:
                    pass
                final_url = page.url
                status_code = response.status if response else None
                page_title = await page.title()
                await hide_overlays_and_disable_animations(page)
                await scroll_to_bottom(page, timing_profile)
                try:
                    await page.wait_for_load_state(
                        'networkidle',
                        timeout=timing_profile['post_scroll_networkidle_timeout_ms'],
                    )
                except Exception:
                    pass
                await page.wait_for_timeout(timing_profile['final_wait_ms'])
                page_state = await collect_page_state(page)
                result_flags = analyze_page_state(url, final_url, status_code, page_title, page_state)
                if block_third_party_media and blocked_hosts:
                    result_flags.append('third_party_media_blocked')
                if any(flag in SECOND_PASS_FLAGS for flag in result_flags):
                    extra_stabilization_used = True
                    print(
                        f"[{page_index}/{total_pages}] {slug} [{vp_name}] looked unstable "
                        f"({', '.join(result_flags)}). Applying an extra stabilization pass."
                    )
                    await run_additional_stabilization_pass(page, timing_profile)
                    page_state = await collect_page_state(page)
                    result_flags = analyze_page_state(url, final_url, status_code, page_title, page_state)
                    if block_third_party_media and blocked_hosts:
                        result_flags.append('third_party_media_blocked')
                if block_third_party_media and blocked_hosts:
                    unique_flags: List[str] = []
                    for flag in result_flags:
                        if flag not in unique_flags:
                            unique_flags.append(flag)
                    result_flags = unique_flags
                    print(
                        f"[{page_index}/{total_pages}] {slug} [{vp_name}] blocked third-party media: "
                        f"{', '.join(sorted(blocked_hosts))}"
                    )
                await page.screenshot(path=screenshot_path, full_page=True)
                success = True
                page_successes += 1
                if result_flags:
                    print(
                        f"[{page_index}/{total_pages}] {slug} [{vp_name}] flags: "
                        f"{', '.join(result_flags)}"
                    )
                print(f"[{page_index}/{total_pages}] Saved {vp_name}: {os.path.relpath(screenshot_path, run_dir)}")
                emit_event(
                    'viewport_saved',
                    page_index=page_index,
                    total_pages=total_pages,
                    viewport_index=viewport_index,
                    total_viewports=len(viewports),
                    url=url,
                    slug=slug,
                    viewport=vp_name,
                    screenshot_path=os.path.relpath(screenshot_path, run_dir),
                    final_url=final_url,
                    result_flags=result_flags,
                )
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
            'redirected': 'yes' if has_meaningful_redirect(url, final_url) else 'no',
            'result_flags': ', '.join(result_flags),
            'extra_stabilization_pass': 'yes' if extra_stabilization_used else 'no',
            'error': error_msg,
        })

    print(
        f"[{page_index}/{total_pages}] Finished {url} | "
        f"successful viewports: {page_successes}, failed viewports: {page_failures}"
    )
    emit_event(
        'page_finished',
        page_index=page_index,
        total_pages=total_pages,
        url=url,
        slug=slug,
        successful_viewports=page_successes,
        failed_viewports=page_failures,
    )


def generate_html_index(report: List[Dict[str, Any]], run_dir: str, date_str: str) -> None:
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


def preview_urls(
    urls: List[str],
    only_failed: bool,
    include_terms: List[str],
    exclude_terms: List[str],
    filter_summary: Dict[str, int],
    max_urls: Optional[int],
    large_run_threshold: int = 100,
) -> bool:
    """Print a short pre-run summary and confirm very large runs."""
    total_urls = len(urls)
    source_label = 'previously failed URLs' if only_failed else 'URLs from sitemap'
    preview_count = min(5, total_urls)

    print(f"Preparing to process {total_urls} {source_label}.")
    if include_terms:
        print(f"Include filters: {', '.join(include_terms)}")
    if exclude_terms:
        print(f"Exclude filters: {', '.join(exclude_terms)}")
    if filter_summary['filtered_out'] > 0:
        print(f"Filtered out {filter_summary['filtered_out']} URLs with include/exclude rules.")
    if max_urls is not None and filter_summary['limited_out'] > 0:
        print(f"Limiting this run to the first {max_urls} URLs after filtering.")
    if preview_count > 0:
        print('URL preview:')
        for preview_url in urls[:preview_count]:
            print(f" - {preview_url}")
        if total_urls > preview_count:
            print(f" ... and {total_urls - preview_count} more")

    if total_urls >= large_run_threshold:
        print(f"Warning: this is a large run ({total_urls} URLs).")
        emit_event('large_run_warning', total_urls=total_urls)
        if sys.stdin.isatty():
            choice = input('Continue? [y/N]: ').strip().lower()
            if choice not in ('y', 'yes'):
                print('Aborted before starting screenshots.')
                emit_event('preview_aborted', total_urls=total_urls)
                return False
        else:
            print('Non-interactive session detected, continuing without confirmation.')

    return True


def open_output_target(run_dir: str, index_path: str, should_open_index: bool, no_open: bool) -> None:
    """Open the HTML index or run folder on macOS after a successful run."""
    if no_open:
        return
    if sys.platform != 'darwin':
        return
    if not sys.stdin.isatty():
        return

    target_path = index_path if should_open_index and os.path.exists(index_path) else run_dir
    try:
        subprocess.run(['open', target_path], check=False)
        print(f"Opened output: {target_path}")
    except Exception as exc:
        print(f"Could not open output automatically: {exc}", file=sys.stderr)


async def run_for_site(
    browser: Browser,
    raw_input_url: str,
    args: argparse.Namespace,
    viewports: List[Tuple[str, int, int]],
    date_str: str,
    include_terms: List[str],
    exclude_terms: List[str],
    timing_profile: Dict[str, int],
    should_open_output: bool,
    site_index: int,
    total_sites: int,
) -> Dict[str, object]:
    """Run the screenshot flow for a single site input."""
    normalized_input_url = normalize_input_url(raw_input_url)
    paths = build_output_paths(args.output, normalized_input_url, date_str)
    os.makedirs(paths['domain_dir'], exist_ok=True)
    os.makedirs(paths['run_dir'], exist_ok=True)

    site_label = f"[Site {site_index}/{total_sites}]"
    print()
    print(f"{site_label} Starting input: {raw_input_url}")
    print(f"{site_label} Output folder for this domain: {paths['domain_dir']}")
    print(f"{site_label} Run folder for today: {paths['run_dir']}")
    emit_event(
        'site_started',
        site_index=site_index,
        total_sites=total_sites,
        input=raw_input_url,
        normalized_input=normalized_input_url,
        domain=domain_slug(normalized_input_url),
        output_folder=paths['domain_dir'],
        run_folder=paths['run_dir'],
    )
    if normalized_input_url != raw_input_url.strip():
        print(f"{site_label} Normalized input: {normalized_input_url}")
        emit_event(
            'site_normalized',
            site_index=site_index,
            total_sites=total_sites,
            input=raw_input_url,
            normalized_input=normalized_input_url,
        )

    urls: List[str] = []
    sitemap_source = normalized_input_url
    if args.only_failed:
        report_path = paths['report_json']
        if not os.path.exists(report_path):
            print(f"{site_label} No report.json found for this domain. Cannot use --only-failed.", file=sys.stderr)
            emit_event(
                'site_failed',
                site_index=site_index,
                total_sites=total_sites,
                input=raw_input_url,
                normalized_input=normalized_input_url,
                domain=domain_slug(normalized_input_url),
                reason='missing_report',
            )
            return {
                'input': raw_input_url,
                'normalized_input': normalized_input_url,
                'domain': domain_slug(normalized_input_url),
                'status': 'failed',
                'pages_processed': 0,
                'reason': 'missing_report',
            }
        with open(report_path, 'r', encoding='utf-8') as f:
            past_report = json.load(f)
        failed_urls: Set[str] = {entry['url'] for entry in past_report if entry['status'] != 'success'}
        urls = sorted(failed_urls)
        print(f"{site_label} Rerunning {len(urls)} previously failed URLs for this domain...")
        emit_event(
            'site_urls_loaded',
            site_index=site_index,
            total_sites=total_sites,
            source='failed_report',
            total_urls=len(urls),
        )
    else:
        print(f"{site_label} Fetching sitemap(s)...")
        sitemap_urls, resolved_sitemap_source = await parse_sitemaps(
            normalized_input_url,
            timing_profile['request_timeout_ms'],
        )
        if resolved_sitemap_source:
            sitemap_source = resolved_sitemap_source
            print(f"{site_label} Using sitemap source: {resolved_sitemap_source}")
        print(f"{site_label} Found {len(sitemap_urls)} URLs in sitemap(s).")
        emit_event(
            'site_urls_loaded',
            site_index=site_index,
            total_sites=total_sites,
            source='sitemap',
            sitemap_source=sitemap_source,
            total_urls=len(sitemap_urls),
        )
        urls = sorted(sitemap_urls)

    urls, filter_summary = apply_url_filters(urls, include_terms, exclude_terms, args.max_urls)
    emit_event(
        'site_urls_filtered',
        site_index=site_index,
        total_sites=total_sites,
        total_urls=len(urls),
        filtered_out=filter_summary['filtered_out'],
        limited_out=filter_summary['limited_out'],
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        max_urls=args.max_urls,
    )

    total_pages = len(urls)
    if total_pages == 0:
        print(f"{site_label} No URLs to process.", file=sys.stderr)
        emit_event(
            'site_failed',
            site_index=site_index,
            total_sites=total_sites,
            input=raw_input_url,
            normalized_input=normalized_input_url,
            domain=domain_slug(normalized_input_url),
            reason='no_urls',
        )
        return {
            'input': raw_input_url,
            'normalized_input': normalized_input_url,
            'domain': domain_slug(normalized_input_url),
            'status': 'failed',
            'pages_processed': 0,
            'reason': 'no_urls',
        }
    if not preview_urls(urls, args.only_failed, include_terms, exclude_terms, filter_summary, args.max_urls):
        emit_event(
            'site_skipped',
            site_index=site_index,
            total_sites=total_sites,
            input=raw_input_url,
            normalized_input=normalized_input_url,
            domain=domain_slug(normalized_input_url),
            reason='aborted_by_user',
        )
        return {
            'input': raw_input_url,
            'normalized_input': normalized_input_url,
            'domain': domain_slug(normalized_input_url),
            'status': 'skipped',
            'pages_processed': 0,
            'reason': 'aborted_by_user',
        }

    report: List[Dict[str, Any]] = []
    if args.concurrency > 1:
        semaphore = asyncio.Semaphore(args.concurrency)

        async def worker(page_index: int, page_url: str) -> None:
            async with semaphore:
                await process_url(
                    browser, page_url, viewports, paths['run_dir'], report,
                    sitemap_source, args.retries, timing_profile, args.block_third_party_media, page_index, total_pages
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
                sitemap_source, args.retries, timing_profile, args.block_third_party_media, index, total_pages
            )

    with open(paths['report_json'], 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"{site_label} Wrote JSON report to {paths['report_json']}")

    with open(paths['report_csv'], 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'url', 'final_url', 'status', 'http_status', 'page_title', 'viewport',
                'sitemap_source', 'screenshot_path', 'redirected', 'result_flags',
                'extra_stabilization_pass', 'error'
            ]
        )
        writer.writeheader()
        for row in report:
            writer.writerow(row)
    print(f"{site_label} Wrote CSV report to {paths['report_csv']}")

    if args.generate_index:
        generate_html_index(report, paths['run_dir'], date_str)

    if should_open_output:
        open_output_target(paths['run_dir'], paths['index_html'], args.generate_index, args.no_open)

    status_counts = Counter(entry['status'] for entry in report)
    successful_pages = len({entry['url'] for entry in report if entry['status'] == 'success'})
    failed_pages = len({entry['url'] for entry in report if entry['status'] == 'failed'})
    print(f"{site_label} Run complete.")
    print(
        f"{site_label} Pages processed: {total_pages} | Pages with at least one successful viewport: {successful_pages} | "
        f"Pages with failed viewports: {failed_pages}"
    )
    print(
        f"{site_label} Viewport results -> success: {status_counts.get('success', 0)}, failed: {status_counts.get('failed', 0)}"
    )
    emit_event(
        'site_finished',
        site_index=site_index,
        total_sites=total_sites,
        input=raw_input_url,
        normalized_input=normalized_input_url,
        domain=domain_slug(normalized_input_url),
        pages_processed=total_pages,
        successful_pages=successful_pages,
        failed_pages=failed_pages,
        successful_viewports=status_counts.get('success', 0),
        failed_viewports=status_counts.get('failed', 0),
        run_folder=paths['run_dir'],
        index_html=paths['index_html'] if args.generate_index else '',
    )

    return {
        'input': raw_input_url,
        'normalized_input': normalized_input_url,
        'domain': domain_slug(normalized_input_url),
        'status': 'success',
        'pages_processed': total_pages,
        'successful_pages': successful_pages,
        'failed_pages': failed_pages,
    }


async def main() -> None:
    global ACTIVE_EVENT_STREAM
    parser = argparse.ArgumentParser(description='Website screenshotter using Playwright.')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--url', help='Root URL, bare domain, or sitemap URL (e.g. example.com or https://example.com/sitemap.xml).')
    input_group.add_argument('--url-file', help='Path to a text file with one website or sitemap entry per line.')
    parser.add_argument('--variant', choices=['basic', 'extended'], default='basic',
                        help='Screenshot set to use (default: basic).')
    parser.add_argument('--output', default='screenshots', help='Base output directory for screenshots and reports.')
    parser.add_argument('--retries', type=int, default=2, help='Number of retries for each page/viewport (default: 2).')
    parser.add_argument('--include', action='append',
                        help='Only process URLs containing these path fragments. Repeat or separate multiple values with commas.')
    parser.add_argument('--exclude', action='append',
                        help='Skip URLs containing these path fragments. Repeat or separate multiple values with commas.')
    parser.add_argument('--max-urls', type=int,
                        help='Process at most this many URLs after filtering. Useful for safer sample runs.')
    parser.add_argument('--timeout-profile', choices=['normal', 'slow'], default='normal',
                        help='Timing profile for page loading and waits (default: normal). Use slow for heavier sites.')
    parser.add_argument('--block-third-party-media', action='store_true',
                        help='Block known third-party video/embed hosts such as YouTube during capture. This may reduce browser prompts but can change layout.')
    parser.add_argument('--event-stream', choices=['jsonl'],
                        help='Emit machine-readable progress events for app integrations.')
    parser.add_argument('--only-failed', action='store_true',
                        help='Reprocess only pages marked as failed in the last report.json file for this domain.')
    parser.add_argument('--generate-index', action='store_true',
                        help='Generate an HTML index page to browse the screenshots.')
    parser.add_argument('--no-open', action='store_true',
                        help='Do not open the output folder or HTML index automatically after a successful run.')
    parser.add_argument('--concurrency', type=int, default=1,
                        help='Number of pages to process concurrently (default: 1). Concurrency >1 may increase memory usage.')
    args = parser.parse_args()

    if args.retries < 0:
        parser.error('--retries must be 0 or higher.')
    if args.concurrency < 1:
        parser.error('--concurrency must be 1 or higher.')
    if args.max_urls is not None and args.max_urls < 1:
        parser.error('--max-urls must be 1 or higher.')

    if args.url_file and not os.path.exists(args.url_file):
        parser.error(f'--url-file not found: {args.url_file}')

    include_terms = parse_filter_terms(args.include)
    exclude_terms = parse_filter_terms(args.exclude)
    timing_profile = TIMEOUT_PROFILES[args.timeout_profile]
    ACTIVE_EVENT_STREAM = args.event_stream

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

    if args.url_file:
        site_inputs = load_url_inputs(args.url_file)
        if not site_inputs:
            parser.error(f'--url-file contains no usable entries: {args.url_file}')
        print(f"Loaded {len(site_inputs)} site entries from {args.url_file}")
    else:
        site_inputs = [args.url]

    should_open_output = len(site_inputs) == 1
    emit_event(
        'run_started',
        input_mode='url_file' if args.url_file else 'url',
        total_sites=len(site_inputs),
        variant=args.variant,
        timeout_profile=args.timeout_profile,
        only_failed=args.only_failed,
        generate_index=args.generate_index,
        block_third_party_media=args.block_third_party_media,
    )
    if len(site_inputs) > 1 and not args.no_open:
        print('Batch mode detected: automatic opening is skipped to avoid opening many windows.')
    print(f"Using timeout profile: {args.timeout_profile}")

    site_results: List[Dict[str, object]] = []

    print('Starting Playwright...')
    emit_event('playwright_starting')
    try:
        pw_context = async_playwright()
        pw = await asyncio.wait_for(
            pw_context.__aenter__(),
            timeout=timing_profile['playwright_start_timeout_ms'],
        )
        try:
            print('Launching Chromium...')
            emit_event('browser_launch_started')
            browser = await pw.chromium.launch(
                headless=True,
                timeout=timing_profile['browser_launch_timeout_ms'],
            )
            print('Chromium launched.')
            emit_event('browser_launch_finished')
            try:
                for site_index, site_input in enumerate(site_inputs, start=1):
                    result = await run_for_site(
                        browser,
                        site_input,
                        args,
                        viewports,
                        date_str,
                        include_terms,
                        exclude_terms,
                        timing_profile,
                        should_open_output,
                        site_index,
                        len(site_inputs),
                    )
                    site_results.append(result)
                    emit_event('site_result', **result)
                    if result['status'] == 'skipped':
                        print('Batch run aborted by user.')
                        emit_event('run_aborted', reason='aborted_by_user')
                        break
            finally:
                await browser.close()
        finally:
            await pw_context.__aexit__(None, None, None)
    except asyncio.TimeoutError:
        print(
            f"Playwright failed to start within {timing_profile['playwright_start_timeout_ms']} ms.",
            file=sys.stderr,
        )
        emit_event(
            'run_failed',
            stage='playwright_start',
            error=f"Timed out after {timing_profile['playwright_start_timeout_ms']} ms",
        )
        raise
    except Exception as exc:
        print(f"Playwright failed to start or launch Chromium: {exc}", file=sys.stderr)
        emit_event('run_failed', stage='playwright_or_browser_launch', error=str(exc))
        raise

    if len(site_results) > 1:
        success_count = sum(1 for result in site_results if result['status'] == 'success')
        failed_count = sum(1 for result in site_results if result['status'] == 'failed')
        skipped_count = sum(1 for result in site_results if result['status'] == 'skipped')
        total_pages = sum(int(result.get('pages_processed', 0)) for result in site_results)
        print()
        print('Batch summary:')
        print(
            f"Sites processed: {len(site_results)} | Successful: {success_count} | "
            f"Failed: {failed_count} | Skipped: {skipped_count}"
        )
        print(f"Total pages processed across sites: {total_pages}")
        for result in site_results:
            print(
                f" - {result['domain']}: {result['status']} "
                f"({result.get('pages_processed', 0)} pages)"
            )
    emit_event(
        'run_finished',
        total_sites=len(site_results),
        successful_sites=sum(1 for result in site_results if result['status'] == 'success'),
        failed_sites=sum(1 for result in site_results if result['status'] == 'failed'),
        skipped_sites=sum(1 for result in site_results if result['status'] == 'skipped'),
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        emit_event('run_aborted', reason='keyboard_interrupt')
        print('Aborted by user')
