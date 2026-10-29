#!/usr/bin/env python3
"""Conservatively scan undeclared journal sites for public OJS signatures."""

from __future__ import annotations

import csv
import hashlib
import http.client
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "miguilim_revistas_2026-10-29.csv"
KNOWN = ROOT / "data" / "ojs_instance_detection_2026-10-29.json"
CACHE_DIR = ROOT / "data" / "ojs_undeclared_scan_cache"
OUTPUT = ROOT / "data" / "ojs_undeclared_active_scan_2026-10-29.json"
CSV_OUTPUT = ROOT / "data" / "ojs_undeclared_active_scan_2026-10-29.csv"
MAX_HOST_WORKERS = 3
TIMEOUT_SECONDS = 20
MAX_BYTES = 1_000_000
SAME_HOST_DELAY_SECONDS = 1.5
USER_AGENT = "Mozilla/5.0 preservation-research/1.0"
VERSION_RE = re.compile(
    r"(?:Open\s+Journal\s+Systems|\bOJS\b)\s*(?:\(OJS\))?\s*(?:version\s*)?"
    r"([0-9]+(?:\.[0-9]+){1,3})",
    re.IGNORECASE,
)


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.generators: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        if values.get("name", "").lower() == "generator" and values.get("content"):
            self.generators.append(values["content"].strip())


def installation_key(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    marker = path.lower().find("/index.php/")
    prefix = path[:marker] if marker >= 0 else ""
    return f"{parsed.netloc.lower()}{prefix.rstrip('/').lower()}"


def cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{digest}.json"


def classify_network_error(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}", str(exc)
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            return "TLS/certificado inválido", str(reason)
        if isinstance(reason, ssl.SSLError):
            return "TLS/SSL", str(reason)
        if isinstance(reason, socket.gaierror):
            return "DNS não resolvido", str(reason)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "Timeout", str(reason)
        if isinstance(reason, ConnectionRefusedError):
            return "Conexão recusada", str(reason)
        return "Erro de conexão", str(reason)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "Timeout", str(exc)
    if isinstance(exc, ssl.SSLError):
        return "TLS/SSL", str(exc)
    if isinstance(exc, socket.gaierror):
        return "DNS não resolvido", str(exc)
    if isinstance(exc, ConnectionRefusedError):
        return "Conexão recusada", str(exc)
    if isinstance(exc, ConnectionResetError):
        return "Conexão reiniciada", str(exc)
    if isinstance(exc, http.client.RemoteDisconnected):
        return "Conexão encerrada pelo servidor", str(exc)
    return type(exc).__name__, str(exc)


def detect_signatures(page: str, headers: object) -> tuple[str, str, str, list[str]]:
    parser = MetaParser()
    parser.feed(page)
    generator = next(
        (item for item in parser.generators if re.search(r"Open Journal Systems|\bOJS\b", item, re.I)),
        "",
    )
    signatures: list[str] = []
    if generator:
        signatures.append(f"meta generator: {generator}")
    if re.search(r"Open Journal Systems", page, re.I):
        signatures.append("texto Open Journal Systems")
    signature_patterns = [
        (r"(?:/|\\)lib/pkp(?:/|\\)", "asset /lib/pkp/"),
        (r"(?:/|\\)plugins/themes(?:/|\\)", "asset /plugins/themes/"),
        (r"(?:/|\\)plugins/generic(?:/|\\)", "asset /plugins/generic/"),
        (r"pkp-lib|pkp/pkp-lib", "referência pkp-lib"),
        (r"class=[\"'][^\"']*pkp_", "classe HTML pkp_*"),
    ]
    for pattern, label in signature_patterns:
        if re.search(pattern, page, re.I):
            signatures.append(label)
    set_cookie = "\n".join(headers.get_all("Set-Cookie") or []) if hasattr(headers, "get_all") else ""
    if re.search(r"\bOJSSID=", set_cookie, re.I):
        signatures.append("cookie OJSSID")

    version_match = VERSION_RE.search(generator) if generator else VERSION_RE.search(page)
    explicit = bool(generator or re.search(r"Open Journal Systems", page, re.I) or version_match)
    technical_count = sum(
        label.startswith(("asset", "referência", "classe", "cookie")) for label in signatures
    )
    if explicit:
        classification = "OJS confirmado"
    elif technical_count >= 2 or "cookie OJSSID" in signatures:
        classification = "OJS provável"
    else:
        classification = "OJS não identificado"

    version = version_match.group(1) if version_match else ""
    if version_match and not generator and not re.search(r"Open Journal Systems", page, re.I):
        signatures.append("texto OJS acompanhado de versão")
    return classification, version, generator, signatures


def check(key: str, urls: list[str]) -> dict[str, object]:
    target = cache_path(key)
    if target.exists():
        return json.loads(target.read_text(encoding="utf-8"))

    url = sorted(set(urls), key=lambda item: (len(item), item))[0]
    result: dict[str, object] = {
        "instance_key": key,
        "representative_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "classification": "",
        "version": "",
        "generator": "",
        "signatures": [],
        "network_error": "",
        "error_detail": "",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
            context=ssl.create_default_context(),
        ) as response:
            result["http_status"] = response.status
            result["final_url"] = response.geturl()
            result["content_type"] = response.headers.get("Content-Type", "")
            raw = response.read(MAX_BYTES + 1)[:MAX_BYTES]
            charset = response.headers.get_content_charset() or "utf-8"
            page = raw.decode(charset, errors="replace")
            classification, version, generator, signatures = detect_signatures(page, response.headers)
            result["classification"] = classification
            result["version"] = version
            result["generator"] = generator
            result["signatures"] = signatures
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["final_url"] = exc.geturl()
        result["classification"] = "Acesso não concluído"
        result["network_error"], result["error_detail"] = classify_network_error(exc)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        http.client.HTTPException,
    ) as exc:
        result["classification"] = "Acesso não concluído"
        result["network_error"], result["error_detail"] = classify_network_error(exc)

    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def process_host(items: list[tuple[str, list[str]]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for index, (key, urls) in enumerate(items):
        if index and not cache_path(key).exists():
            time.sleep(SAME_HOST_DELAY_SECONDS)
        results.append(check(key, urls))
    return results


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    known_payload = json.loads(KNOWN.read_text(encoding="utf-8"))
    known_keys = {str(item["instance_key"]) for item in known_payload["instances"]}

    groups: defaultdict[str, list[str]] = defaultdict(list)
    journal_counts: Counter[str] = Counter()
    with SOURCE.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["dc.description.software[pt_BR]"].strip():
                continue
            url = row["dc.identifier.url[pt_BR]"].split("||")[0].strip()
            if not urllib.parse.urlsplit(url).netloc:
                continue
            key = installation_key(url)
            if key in known_keys:
                continue
            groups[key].append(url)
            journal_counts[key] += 1

    by_host: defaultdict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for key, urls in groups.items():
        host = urllib.parse.urlsplit(urls[0]).netloc.lower()
        by_host[host].append((key, urls))

    cached = sum(cache_path(key).exists() for key in groups)
    print(
        f"Instalações: {len(groups)} em {len(by_host)} hosts; "
        f"cache: {cached}; consultas novas: {len(groups) - cached}",
        flush=True,
    )
    results: list[dict[str, object]] = []
    completed = 0
    total = len(groups)
    with ThreadPoolExecutor(max_workers=MAX_HOST_WORKERS) as pool:
        futures = [pool.submit(process_host, items) for items in by_host.values()]
        for future in as_completed(futures):
            host_results = future.result()
            for item in host_results:
                if item.get("version") and item.get("classification") == "OJS não identificado":
                    item["classification"] = "OJS confirmado"
                    signatures = list(item.get("signatures") or [])
                    signatures.append("texto OJS acompanhado de versão")
                    item["signatures"] = signatures
                item["journals_affected"] = journal_counts[str(item["instance_key"])]
            results.extend(host_results)
            completed += len(host_results)
            if completed % 50 < len(host_results) or completed == total:
                confirmed = sum(item["classification"] == "OJS confirmado" for item in results)
                probable = sum(item["classification"] == "OJS provável" for item in results)
                print(
                    f"  concluídas {completed}/{total}; confirmadas {confirmed}; prováveis {probable}",
                    flush=True,
                )

    results.sort(key=lambda item: str(item["instance_key"]))
    installation_summary = Counter(str(item["classification"]) for item in results)
    journal_summary: Counter[str] = Counter()
    version_journals: Counter[str] = Counter()
    network_errors: Counter[str] = Counter()
    for item in results:
        count = int(item["journals_affected"])
        journal_summary[str(item["classification"])] += count
        if item.get("version"):
            version_journals[str(item["version"])] += count
        if item.get("network_error"):
            network_errors[str(item["network_error"])] += count

    output = {
        "source": SOURCE.name,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_policy": {
            "scope": "uma URL representativa por instalação sem declaração e ainda não analisada",
            "hosts": len(by_host),
            "installations": len(groups),
            "max_parallel_hosts": MAX_HOST_WORKERS,
            "same_host_delay_seconds": SAME_HOST_DELAY_SECONDS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "max_response_bytes": MAX_BYTES,
            "retries": 0,
        },
        "summary_by_installation": dict(installation_summary.most_common()),
        "summary_by_journal": dict(journal_summary.most_common()),
        "network_errors_by_journal": dict(network_errors.most_common()),
        "versions_by_journal": dict(version_journals.most_common()),
        "instances": results,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = [
        "instance_key",
        "representative_url",
        "journals_affected",
        "http_status",
        "classification",
        "version",
        "generator",
        "signatures",
        "network_error",
        "error_detail",
        "final_url",
        "content_type",
        "checked_at_utc",
    ]
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for item in results:
            row = {field: item.get(field, "") for field in fields}
            row["signatures"] = "||".join(str(value) for value in item.get("signatures", []))
            writer.writerow(row)

    print(json.dumps(output["summary_by_installation"], ensure_ascii=False, indent=2), flush=True)
    print(json.dumps(output["summary_by_journal"], ensure_ascii=False, indent=2), flush=True)
    print(json.dumps(output["network_errors_by_journal"], ensure_ascii=False, indent=2), flush=True)
    print(json.dumps(dict(version_journals.most_common(20)), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
