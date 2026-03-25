#!/usr/bin/env python3
"""
Scrape movie titles from IMDB event pages (e.g. Academy Awards).

Example:
  python scrape_imdb_event.py --out titles.json
  python scrape_imdb_event.py --event-id ev0000003 --year 2026 --delay 1.5
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections import OrderedDict
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

IMDB_ORIGIN = "https://www.imdb.com"
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
TT_ID_RE = re.compile(r"^tt\d+$")
SEGMENT_PATH_RE_TEMPLATE = r"/event/{event}/{year}/(\d+)/?"


def segment_link_pattern(event_id: str, year: str) -> re.Pattern[str]:
    return re.compile(
        SEGMENT_PATH_RE_TEMPLATE.format(
            event=re.escape(event_id),
            year=re.escape(year),
        )
    )


def normalize_imdb_url(href: str) -> str | None:
    if not href:
        return None
    if href.startswith("//"):
        href = "https:" + href
    path = urlparse(href).path if "://" in href else href
    m = re.search(r"(/event/[^?#]+)", path)
    if not m:
        return None
    p = m.group(1).rstrip("/") + "/"
    return urljoin(IMDB_ORIGIN, p)


def discover_urls_from_html(html: str, event_id: str, year: str) -> set[str]:
    found: set[str] = set()
    pat = segment_link_pattern(event_id, year)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if pat.search(href):
            u = normalize_imdb_url(href)
            if u:
                found.add(u)
    for m in pat.finditer(html):
        seg = m.group(1)
        found.add(f"{IMDB_ORIGIN}/event/{event_id}/{year}/{seg}/")
    return found


def numeric_fallback_urls(
    client: httpx.Client,
    event_id: str,
    year: str,
    delay: float,
    max_segments: int,
    consecutive_404: int,
    existing: set[str],
) -> set[str]:
    out = set(existing)
    misses = 0
    for n in range(1, max_segments + 1):
        url = f"{IMDB_ORIGIN}/event/{event_id}/{year}/{n}/"
        if url in out:
            misses = 0
            continue
        time.sleep(delay)
        try:
            r = client.head(url, follow_redirects=True)
            if r.status_code in (405, 501):
                r = client.get(url, follow_redirects=True)
        except httpx.HTTPError:
            logging.warning("Probe failed for %s", url)
            misses += 1
            continue
        if r.status_code == 200:
            out.add(url)
            misses = 0
        elif r.status_code == 404:
            misses += 1
        else:
            logging.debug("Probe %s -> %s", url, r.status_code)
            misses = 0
        if misses >= consecutive_404:
            break
    return out


def load_next_data(html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__", attrs={"type": "application/json"})
    if tag is None or not tag.string:
        return None
    try:
        return json.loads(tag.string)
    except json.JSONDecodeError:
        logging.warning("Could not parse __NEXT_DATA__ JSON")
        return None


def _title_text_from_node(node: dict[str, Any]) -> str | None:
    for key in ("titleText", "originalTitleText", "text"):
        v = node.get(key)
        if isinstance(v, dict):
            t = v.get("text")
            if isinstance(t, str) and t.strip():
                return t.strip()
        elif isinstance(v, str) and v.strip():
            return v.strip()
    return None


def titles_from_json(obj: Any, out: OrderedDict[str, str]) -> None:
    """Collect (imdb_id -> title) from nested JSON; IMDB uses id 'tt…' with titleText."""
    if isinstance(obj, dict):
        tid = obj.get("id")
        if isinstance(tid, str) and TT_ID_RE.match(tid):
            title = _title_text_from_node(obj)
            if title:
                if tid not in out:
                    out[tid] = title
        for v in obj.values():
            titles_from_json(v, out)
    elif isinstance(obj, list):
        for item in obj:
            titles_from_json(item, out)


def titles_from_html_links(html: str, out: OrderedDict[str, str]) -> None:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        parsed = urlparse(href)
        path = parsed.path if parsed.scheme else href.split("?")[0]
        m = re.search(r"/title/(tt\d+)/?", path)
        if not m:
            continue
        tid = m.group(1)
        text = a.get_text(separator=" ", strip=True)
        if not text or len(text) > 500:
            continue
        if tid not in out:
            out[tid] = text


def extract_titles_from_page(html: str) -> OrderedDict[str, str]:
    merged: OrderedDict[str, str] = OrderedDict()
    data = load_next_data(html)
    if data is not None:
        titles_from_json(data, merged)
    titles_from_html_links(html, merged)
    return merged


def sort_segment_urls(urls: Iterable[str], event_id: str, year: str) -> list[str]:
    pat = segment_link_pattern(event_id, year)

    def sort_key(u: str) -> tuple[int, str]:
        m = pat.search(urlparse(u).path)
        if m:
            return (int(m.group(1)), u)
        return (10**9, u)

    return sorted(set(urls), key=sort_key)


def scrape_event(
    client: httpx.Client,
    event_id: str,
    year: str,
    seed_url: str | None,
    delay: float,
    max_segments: int,
    consecutive_404: int,
) -> tuple[list[str], OrderedDict[str, str], int]:
    index_urls = [
        f"{IMDB_ORIGIN}/event/{event_id}/{year}/",
        f"{IMDB_ORIGIN}/event/{event_id}/{year}",
    ]
    discovered: set[str] = set()
    for idx in index_urls:
        time.sleep(delay)
        try:
            r = client.get(idx, follow_redirects=True)
        except httpx.HTTPError as e:
            logging.warning("Index GET failed %s: %s", idx, e)
            continue
        if r.status_code != 200:
            logging.warning("Index %s returned %s", idx, r.status_code)
            continue
        discovered |= discover_urls_from_html(r.text, event_id, year)

    discovered = numeric_fallback_urls(
        client,
        event_id,
        year,
        delay,
        max_segments,
        consecutive_404,
        discovered,
    )
    if seed_url:
        normalized = normalize_imdb_url(seed_url) or seed_url.rstrip("/") + "/"
        discovered.add(normalized)

    segment_urls = sort_segment_urls(discovered, event_id, year)
    if not segment_urls:
        return [], OrderedDict(), 0

    global_titles: OrderedDict[str, str] = OrderedDict()
    pages_ok = 0
    for url in segment_urls:
        time.sleep(delay)
        try:
            r = client.get(url, follow_redirects=True)
        except httpx.HTTPError as e:
            logging.warning("GET failed %s: %s", url, e)
            continue
        if r.status_code != 200:
            logging.warning("GET %s -> %s", url, r.status_code)
            continue
        pages_ok += 1
        page_titles = extract_titles_from_page(r.text)
        for tid, title in page_titles.items():
            if tid not in global_titles:
                global_titles[tid] = title

    return segment_urls, global_titles, pages_ok


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--event-id", default="ev0000003", help="IMDB event id (default: Oscars)")
    p.add_argument("--year", default="2026", help="Ceremony year segment in URL")
    p.add_argument(
        "--seed-url",
        default="https://www.imdb.com/event/ev0000003/2026/1/",
        help="Always include this segment URL if not discovered",
    )
    p.add_argument("--out", default="", help="Write JSON to this file (default: stdout)")
    p.add_argument("--delay", type=float, default=1.0, help="Seconds between HTTP calls")
    p.add_argument(
        "--max-segments",
        type=int,
        default=50,
        help="Max segment number to probe when using numeric fallback",
    )
    p.add_argument(
        "--consecutive-404",
        type=int,
        default=3,
        help="Stop numeric probe after this many consecutive 404 HEAD responses",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    p.add_argument(
        "--no-env-proxy",
        action="store_true",
        help="Ignore HTTP_PROXY / HTTPS_PROXY (use a direct connection to IMDB)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    headers = {
        "User-Agent": DEFAULT_UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    }
    with httpx.Client(
        headers=headers,
        timeout=60.0,
        follow_redirects=True,
        trust_env=not args.no_env_proxy,
    ) as client:
        segment_urls, titles, pages_ok = scrape_event(
            client,
            args.event_id,
            args.year,
            args.seed_url or None,
            args.delay,
            args.max_segments,
            args.consecutive_404,
        )

    if not segment_urls:
        logging.error("No segment URLs discovered; check event id, year, and network.")
        return 1
    if pages_ok == 0:
        logging.error("No event pages returned HTTP 200; check network, proxy, or try --no-env-proxy.")
        return 1

    movies = [{"imdb_id": tid, "title": title} for tid, title in titles.items()]
    payload = {
        "event_id": args.event_id,
        "year": args.year,
        "segment_urls": segment_urls,
        "title_count": len(movies),
        "movies": movies,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
