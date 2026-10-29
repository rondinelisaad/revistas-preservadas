#!/usr/bin/env python3
"""Collect Brazilian Keepers Registry agency memberships conservatively.

The collector uses the public country/agency result pages, caches every page,
and honors the site's published Crawl-delay of 10 seconds.  It intentionally
does not request one detail page per ISSN.
"""

from __future__ import annotations

import csv
import html
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "keepers_cache"
OUTPUT_CSV = ROOT / "data" / "keepers_brazil_agencies_2026-10-29.csv"
OUTPUT_META = ROOT / "data" / "keepers_brazil_collection_metadata_2026-10-29.json"
BASE_URL = "https://publishers.issn.org/"
CRAWL_DELAY_SECONDS = 10.5
PAGE_SIZE = 100
USER_AGENT = "Mozilla/5.0 preservation-research/1.0"

# Counts were read from the public Keepers Registry facet for Country: Brazil
# on 2026-10-29.  Two source facets represent the same Chinese programme; they
# are queried separately and merged under one canonical agency name.
AGENCY_FACETS = [
    ("Cariniana Network", "Cariniana Network", 2274),
    ("Public Knowledge Project PLN", "Public Knowledge Project PLN", 1129),
    ("Internet Archive", "Internet Archive", 170),
    ("Portico", "Portico", 65),
    ("National Library of the Netherlands", "National Library of the Netherlands", 60),
    ("LOCKSS Archive", "LOCKSS Archive", 33),
    (
        "<![CDATA[National Digital Preservation Program, China]]>",
        "National Digital Preservation Program, China",
        18,
    ),
    ("HathiTrust", "HathiTrust", 17),
    ("Library of Congress", "Library of Congress", 15),
    (
        "National Digital Preservation Program, China",
        "National Digital Preservation Program, China",
        11,
    ),
    (
        "ZBW - Leibniz Information Centre for Economics",
        "ZBW - Leibniz Information Centre for Economics",
        6,
    ),
    ("Scholars Portal", "Scholars Portal", 1),
]

ISSN_RE = re.compile(
    r'id="titleRecord"\s+href="/resource/ISSN/(\d{4}-\d{3}[\dXx])"',
    re.IGNORECASE,
)
CANONICAL_ISSN_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="https://publishers\.issn\.org/resource/ISSN/(\d{4}-\d{3}[\dXx])"',
    re.IGNORECASE,
)


def cache_name(facet_value: str, page: int) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", facet_value.lower()).strip("-")
    return CACHE_DIR / f"{slug}-page-{page:03d}.html"


def build_url(facet_value: str, page: int) -> str:
    params = [
        ("q", "api/search"),
        ("search[]", "MUST=country=BRA"),
        ("search[]", "MUST_EXIST=keepers"),
        ("facet[]", f"keepersAgency={facet_value}"),
        ("size", str(PAGE_SIZE)),
        ("role[]", "17"),
        ("currentpage", str(page)),
    ]
    return BASE_URL + "?" + urllib.parse.urlencode(params)


def fetch_page(url: str, target: Path) -> str:
    if target.exists() and target.stat().st_size > 10_000:
        return target.read_text(encoding="utf-8")

    for attempt in range(1, 4):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8", errors="replace")
            target.write_text(body, encoding="utf-8")
            return body
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError(f"Falha após 3 tentativas: {url}") from exc
            retry_wait = 20 * attempt
            print(f"  tentativa {attempt} falhou; nova tentativa em {retry_wait}s", flush=True)
            time.sleep(retry_wait)
        finally:
            # Honor the published robots.txt Crawl-delay: 10.
            time.sleep(CRAWL_DELAY_SECONDS)
    raise AssertionError("unreachable")


def extract_issns(body: str) -> set[str]:
    values = {html.unescape(value).upper() for value in ISSN_RE.findall(body)}
    # A one-result facet may redirect directly to the record page.
    if not values:
        values = {
            html.unescape(value).upper()
            for value in CANONICAL_ISSN_RE.findall(body)
        }
    return values


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    memberships: dict[str, set[str]] = {}
    audit: list[dict[str, object]] = []

    for facet_value, canonical_name, expected_count in AGENCY_FACETS:
        pages = math.ceil(expected_count / PAGE_SIZE)
        agency_issns: set[str] = set()
        print(f"{canonical_name}: {pages} página(s), {expected_count} registros esperados", flush=True)
        for page in range(1, pages + 1):
            target = cache_name(facet_value, page)
            body = fetch_page(build_url(facet_value, page), target)
            found = extract_issns(body)
            agency_issns.update(found)
            print(f"  página {page}/{pages}: {len(found)} ISSNs; acumulado {len(agency_issns)}", flush=True)

        audit.append(
            {
                "facet": facet_value,
                "agency": canonical_name,
                "expected_records": expected_count,
                "unique_issns_collected": len(agency_issns),
            }
        )
        if len(agency_issns) != expected_count:
            raise RuntimeError(
                f"Contagem divergente para {facet_value}: "
                f"esperado {expected_count}, coletado {len(agency_issns)}"
            )
        for issn in agency_issns:
            memberships.setdefault(issn, set()).add(canonical_name)

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["issn", "agency_count", "agencies"])
        for issn in sorted(memberships):
            agencies = sorted(memberships[issn])
            writer.writerow([issn, len(agencies), "||".join(agencies)])

    metadata = {
        "source": "https://keepers.issn.org/advancedsearch",
        "source_country_filter": "Brazil",
        "source_requires_keeper": True,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "crawl_delay_seconds": CRAWL_DELAY_SECONDS,
        "page_size": PAGE_SIZE,
        "unique_preserved_issns": len(memberships),
        "agency_facets": audit,
    }
    OUTPUT_META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Concluído: {len(memberships)} ISSNs preservados em {OUTPUT_CSV}", flush=True)


if __name__ == "__main__":
    main()
