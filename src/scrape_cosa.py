"""
Crawls City of San Antonio (COSA) emergency-preparedness pages with crawl4ai
(a real headless browser, which gets past the bot-blocking that a plain HTTP
fetch of sa.gov runs into) and writes results out in the ingestion.py JSONL
schema: {"source_url", "title", "record_type", "full_body"}.

It does a single breadth-first pass starting from SEED_URLS: fetch a page,
keep its content if there's enough of it, then queue up its in-domain,
in-scope links for the same treatment. That queue *is* the site tree map —
it's written to --tree-out for inspection alongside the JSONL output.

Setup (separate from the main app's requirements.txt — this is a one-off
scraping tool, not a runtime dependency):
    pip install -r requirements-scrape.txt
    crawl4ai-setup      # installs the Playwright browser crawl4ai drives

Usage:
    python src/scrape_cosa.py
    python src/scrape_cosa.py --max-pages 150 --out ../data/cosa_data/emergency_prep_sagov.jsonl
    python src/scrape_cosa.py --seeds https://www.sa.gov/Government/Emergency-Crisis-Response --domains sa.gov
"""

import argparse
import asyncio
import json
import os
from collections import deque

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

SEED_URLS = [
    "https://www.sa.gov/Directory/Departments/SAMHD/PHEP/Emergency-Management",
    "https://www.sa.gov/Directory/Departments/SAMHD/PHEP/Preparing-for-an-Emergency",
    "https://www.sa.gov/Government/Emergency-Crisis-Response",
    "https://www.sa.gov/Directory/Departments/SAMHD/PHEP",
]

ALLOWED_DOMAINS = ["sa.gov"]

# Only follow links whose URL contains one of these — keeps the crawl inside
# emergency/preparedness-relevant sections instead of the whole city site.
PATH_KEYWORDS = [
    "emergency", "disaster", "hazard", "prepare", "alert", "evacuat",
    "shelter", "flood", "storm", "crisis", "safety", "phep",
]

MIN_BODY_CHARS = 200  # skip pages that are basically just nav/boilerplate

# crawl4ai's density-based PruningContentFilter misjudges this site's nested CMS
# markup and prunes real content along with the nav (tested: it collapsed an
# 18,700-char page down to 115 chars of just the "skip to content" link). Instead,
# bracket the actual page content with marker strings scraped pages have in common.
# sa.gov mixes at least two CMS templates (the main site, and the older DNN-based
# saoemprepare.com microsite it proxies some /Departments/OEM/ pages from), each
# with its own header/footer boilerplate — so try each known pair in turn.
MARKER_PAIRS = [
    ("Select the Escape key to close the menu. Focus will then be set to the first menu item.", "[Back to top]("),
    ("210-206-8570", "Copyright ©"),
]

# Non-HTML files crawl4ai's markdown extractor can't meaningfully parse, and
# translated duplicates of pages we already have in English.
SKIP_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".jpg", ".jpeg", ".png", ".gif")


def record_type_for(url: str) -> str:
    path = url.lower()
    if "alert" in path:
        return "alerts"
    if "evacuat" in path:
        return "evacuation"
    if "shelter" in path:
        return "shelter"
    if "hazard" in path or "disaster" in path or "flood" in path or "storm" in path:
        return "hazard"
    if "plan" in path:
        return "plan"
    return "webpage"


def clean_body(raw: str) -> str:
    for header_marker, footer_marker in MARKER_PAIRS:
        header_idx = raw.find(header_marker)
        if header_idx == -1:
            continue
        text = raw[header_idx + len(header_marker):]
        footer_idx = text.find(footer_marker)
        if footer_idx != -1:
            text = text[:footer_idx]
        return text.strip()
    return raw.strip()


def normalize(url: str) -> str:
    # Drop the fragment and query string — oc_lang=xx language variants and other
    # query params would otherwise all count as distinct pages to crawl.
    return url.split("#")[0].split("?")[0].rstrip("/")


def in_scope(url: str, allowed_domains: list[str], path_keywords: list[str]) -> bool:
    if url.lower().endswith(SKIP_EXTENSIONS):
        return False
    if not any(d in url for d in allowed_domains):
        return False
    if path_keywords and not any(kw in url.lower() for kw in path_keywords):
        return False
    return True


async def crawl_site(seed_urls, allowed_domains, path_keywords, max_pages, out_path):
    # sa.gov renders its content client-side (SPA), so the crawler needs to wait
    # for the network to go idle before there's anything real to extract.
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        delay_before_return_html=2.0,
        page_timeout=60000,
    )

    visited = set()
    queue = deque(normalize(u) for u in seed_urls)
    tree = []
    written = 0

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        with open(out_path, "a", encoding="utf-8") as out_f:
            while queue and len(visited) < max_pages:
                url = queue.popleft()
                if url in visited:
                    continue
                visited.add(url)

                result = await crawler.arun(url=url, config=run_config)
                if not result.success:
                    tree.append({"url": url, "status": "failed"})
                    print(f"  failed: {url}")
                    continue

                markdown = result.markdown
                raw = ""
                if markdown:
                    raw = (getattr(markdown, "raw_markdown", None) or "").strip()
                body = clean_body(raw) if raw else ""
                raw_title = (result.metadata or {}).get("title")
                title = raw_title.strip() if raw_title else url

                if len(body) >= MIN_BODY_CHARS:
                    record = {
                        "source_url": url,
                        "title": title,
                        "record_type": record_type_for(url),
                        "full_body": body,
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1
                    tree.append({"url": url, "status": "written", "chars": len(body)})
                    print(f"  wrote ({len(body)} chars): {url}")
                else:
                    tree.append({"url": url, "status": "skipped_short", "chars": len(body)})
                    print(f"  skip (too short, {len(body)} chars): {url}")

                internal_links = (result.links or {}).get("internal", [])
                for link in internal_links:
                    href = normalize(link.get("href", ""))
                    if not href or href in visited:
                        continue
                    if in_scope(href, allowed_domains, path_keywords):
                        queue.append(href)

    return written, tree


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", nargs="*", default=SEED_URLS, help="Starting URLs for the crawl.")
    parser.add_argument("--domains", nargs="*", default=ALLOWED_DOMAINS, help="Only follow links containing one of these substrings.")
    parser.add_argument("--path-keywords", nargs="*", default=PATH_KEYWORDS, help="Only follow links whose URL contains one of these.")
    parser.add_argument("--max-pages", type=int, default=150)
    parser.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(__file__), "..", "data", "cosa_data", "emergency_prep_sagov.jsonl"),
        help="JSONL output file (appended to, not overwritten).",
    )
    parser.add_argument(
        "--tree-out",
        default=os.path.join(os.path.dirname(__file__), "..", "data", "cosa_data", "_url_tree_sagov.json"),
        help="Where to save the discovered URL tree map for inspection.",
    )
    args = parser.parse_args()

    print(f"Crawling from {len(args.seeds)} seed URL(s), domains={args.domains}, max_pages={args.max_pages}...")
    written, tree = asyncio.run(
        crawl_site(args.seeds, args.domains, args.path_keywords, args.max_pages, args.out)
    )

    os.makedirs(os.path.dirname(args.tree_out), exist_ok=True)
    with open(args.tree_out, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2)

    print(f"\nVisited {len(tree)} page(s), wrote {written} record(s) to {args.out}")
    print(f"URL tree map saved to {args.tree_out}")


if __name__ == "__main__":
    main()
