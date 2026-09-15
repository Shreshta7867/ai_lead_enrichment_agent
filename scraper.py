from __future__ import annotations

import logging
from urllib.parse import urlparse

from playwright.sync_api import Playwright, sync_playwright

from models import PageContent
from utils import (
    clean_text,
    deduplicate_text,
    is_internal_url,
    is_relevant_internal_path,
    normalize_domain,
    safe_url_join,
    should_skip_navigation_url,
)

LOGGER = logging.getLogger(__name__)

MAX_PAGES_PER_DOMAIN = 8
MAX_NAVIGATION_TIMEOUT_MS = 15000


class CompanyCrawler:
    def __init__(self, domain: str):
        self.domain = normalize_domain(domain)
        self.base_url = f"https://{self.domain}"

    def crawl(self) -> list[PageContent]:
        results: list[PageContent] = []
        visited: set[str] = set()
        queue: list[str] = [self.base_url]

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = context.new_page()
            try:
                for url in queue:
                    if len(results) >= MAX_PAGES_PER_DOMAIN:
                        break
                    if url in visited:
                        continue
                    visited.add(url)
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=MAX_NAVIGATION_TIMEOUT_MS)
                        page.wait_for_timeout(1200)
                    except Exception as exc:
                        LOGGER.warning("Page load failed for %s: %s", url, exc)
                        continue

                    text = self._extract_visible_text(page)
                    if text:
                        results.append(PageContent(url=url, title=page.title(), text=text))

                    try:
                        links = self._discover_candidate_links(page)
                    except Exception as exc:
                        LOGGER.warning("Link discovery failed for %s: %s", url, exc)
                        links = []

                    for link in links:
                        if len(results) >= MAX_PAGES_PER_DOMAIN:
                            break
                        if link in visited:
                            continue
                        queue.append(link)
            finally:
                browser.close()

        return self._finalize_content(results)

    def _discover_candidate_links(self, page) -> list[str]:
        hrefs = page.locator("a[href]").evaluate_all(
            """
            (elements) => elements.map((el) => el.href).filter(Boolean)
            """
        )

        candidates: list[tuple[int, str]] = []
        for href in hrefs:
            if should_skip_navigation_url(href):
                continue
            absolute = safe_url_join(self.base_url, href)
            if not absolute:
                continue
            parsed = urlparse(absolute)
            if not is_internal_url(absolute, self.domain):
                continue
            if parsed.path.lower() in ("", "/"):
                continue
            score = 0
            lowered = parsed.path.lower()
            if is_relevant_internal_path(lowered):
                score += 10
            if any(token in lowered for token in ("about", "team", "leadership", "contact", "pricing", "company")):
                score += 5
            if "/blog" in lowered:
                score -= 3
            if "/docs" in lowered:
                score -= 2
            if score >= 0:
                candidates.append((score, absolute))

        unique_links = []
        seen: set[str] = set()
        for _, link in sorted(candidates, reverse=True):
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        return unique_links[:6]

    def _extract_visible_text(self, page) -> str:
        text = page.evaluate(
            """
            () => {
                const root = document.body || document.documentElement;
                if (!root) return "";
                const selectors = [
                    'script','style','svg','iframe','noscript','template',
                    'nav','footer','header','aside','form','button'
                ];
                selectors.forEach((selector) => {
                    root.querySelectorAll(selector).forEach((el) => el.remove());
                });
                const visibleText = (root.innerText || '').replace(/\s+/g, ' ').trim();
                return visibleText;
            }
            """
        )
        return clean_text(text)

    def _finalize_content(self, pages: list[PageContent]) -> list[PageContent]:
        combined: list[PageContent] = []
        seen_urls: set[str] = set()
        for page in pages:
            if page.url in seen_urls:
                continue
            seen_urls.add(page.url)
            page.text = clean_text(page.text)
            combined.append(page)

        return combined


def crawl_company_domain(domain: str) -> list[PageContent]:
    crawler = CompanyCrawler(domain)
    return crawler.crawl()
