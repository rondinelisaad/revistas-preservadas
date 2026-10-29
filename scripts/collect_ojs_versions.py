#!/usr/bin/env python3
"""Detect OJS versions with one cached request per declared OJS installation."""

from __future__ import annotations

import csv
import hashlib
import http.client
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "miguilim_revistas_2026-10-29.csv"
CACHE_DIR = ROOT / "data" / "ojs_detection_cache"
OUTPUT = ROOT / "data" / "ojs_instance_detection_2026-10-29.json"
MAX_WORKERS = 6
MAX_BYTES = 2_000_000
TIMEOUT_SECONDS = 20
USER_AGENT = "Mozilla/5.0 preservation-research/1.0"
OJS_DECLARATION_RE = re.compile(r"(?:Open Journal Systems|\bOJS\b)", re.IGNORECASE)
OJS_VERSION_RE = re.compile(
    r"(?:Open\s+Journal\s+Systems|\bOJS\b)\s*(?:\(OJS\))?\s*(?:version\s*)?"
    r"([0-9]+(?:\.[0-9]+){1,3})",
    re.IGNORECASE,
)


class GeneratorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.generators: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        if values.get("name", "").lower() == "generator" and values.get("content"):
            self.generators.append(values["content"].strip())


def read_rows() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def primary_url(value: str) -> str:
    return value.split("||")[0].strip()


def installation_key(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    marker = path.lower().find("/index.php/")
    prefix = path[:marker] if marker >= 0 else ""
    return f"{parsed.netloc.lower()}{prefix.rstrip('/').lower()}"


def cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{digest}.json"


def detect(key: str, urls: list[str]) -> dict[str, object]:
    target = cache_path(key)
    if target.exists():
        return json.loads(target.read_text(encoding="utf-8"))

    representative = sorted(urls, key=lambda item: (len(item), item))[0]
    result: dict[str, object] = {
        "instance_key": key,
        "representative_url": representative,
        "final_url": "",
        "http_status": None,
        "generator": "",
        "ojs_detected_in_page": False,
        "version": "",
        "evidence": "",
        "error": "",
    }
    request = urllib.request.Request(
        representative,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()) as response:
            result["http_status"] = response.status
            result["final_url"] = response.geturl()
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raw = raw[:MAX_BYTES]
            charset = response.headers.get_content_charset() or "utf-8"
            page = raw.decode(charset, errors="replace")

        parser = GeneratorParser()
        parser.feed(page)
        generator = next(
            (value for value in parser.generators if OJS_DECLARATION_RE.search(value)),
            "",
        )
        match = OJS_VERSION_RE.search(generator) if generator else OJS_VERSION_RE.search(page)
        result["generator"] = generator
        result["ojs_detected_in_page"] = bool(generator or re.search(r"Open Journal Systems", page, re.IGNORECASE))
        result["version"] = match.group(1) if match else ""
        if match:
            result["evidence"] = generator or match.group(0)
        elif generator:
            result["evidence"] = generator
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["final_url"] = exc.geturl()
        result["error"] = f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, ValueError, OSError, http.client.HTTPException) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[str]] = defaultdict(list)
    for row in read_rows():
        if not OJS_DECLARATION_RE.search(row["dc.description.software[pt_BR]"]):
            continue
        url = primary_url(row["dc.identifier.url[pt_BR]"])
        if not url or not urllib.parse.urlsplit(url).netloc:
            continue
        groups[installation_key(url)].append(url)

    results: list[dict[str, object]] = []
    total = len(groups)
    cached = sum(cache_path(key).exists() for key in groups)
    print(f"Instalações OJS: {total}; em cache: {cached}; consultas novas: {total - cached}", flush=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(detect, key, urls): key for key, urls in groups.items()}
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if index % 25 == 0 or index == total:
                versions = sum(bool(item.get("version")) for item in results)
                print(f"  concluídas {index}/{total}; versões detectadas: {versions}", flush=True)

    results.sort(key=lambda item: str(item["instance_key"]))
    payload = {
        "source": "sites das revistas declaradas como OJS no Miguilim",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_policy": {
            "scope": "uma URL representativa por instalação/host",
            "max_workers_across_distinct_hosts": MAX_WORKERS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "max_response_bytes": MAX_BYTES,
            "retries": 0,
        },
        "instances": results,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    detected = sum(bool(item["version"]) for item in results)
    errors = sum(bool(item["error"]) for item in results)
    print(f"Concluído: {detected}/{total} versões detectadas; {errors} falhas de acesso.", flush=True)


if __name__ == "__main__":
    main()
