#!/usr/bin/env python3
"""Revalidate failed OJS installations with one conservative GET per installation."""

from __future__ import annotations

import csv
import http.client
import json
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "miguilim_revistas_2026-10-29.csv"
INPUT = ROOT / "data" / "ojs_instance_detection_2026-10-29.json"
OUTPUT = ROOT / "data" / "ojs_access_revalidation_2026-10-29.json"
CSV_OUTPUT = ROOT / "data" / "ojs_access_revalidation_2026-10-29.csv"
MAX_WORKERS = 3
TIMEOUT_SECONDS = 25
MAX_BYTES = 65_536
USER_AGENT = "Mozilla/5.0 preservation-research/1.0"


def installation_key(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    marker = path.lower().find("/index.php/")
    prefix = path[:marker] if marker >= 0 else ""
    return f"{parsed.netloc.lower()}{prefix.rstrip('/').lower()}"


def classify_exception(exc: BaseException) -> tuple[str, str]:
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


def check(item: dict[str, object]) -> dict[str, object]:
    url = str(item["representative_url"])
    result: dict[str, object] = {
        "instance_key": item["instance_key"],
        "url": url,
        "previous_http_status": item.get("http_status"),
        "previous_error": item.get("error", ""),
        "http_status": None,
        "final_url": "",
        "classification": "",
        "detail": "",
        "content_type": "",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Range": f"bytes=0-{MAX_BYTES - 1}",
        },
        method="GET",
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
            response.read(MAX_BYTES)
            result["classification"] = f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["final_url"] = exc.geturl()
        result["classification"], result["detail"] = classify_exception(exc)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        http.client.HTTPException,
    ) as exc:
        result["classification"], result["detail"] = classify_exception(exc)
    return result


def main() -> None:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    failed = [item for item in payload["instances"] if item.get("error")]

    journal_counts: Counter[str] = Counter()
    with SOURCE.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            software = row["dc.description.software[pt_BR]"]
            if "Open Journal Systems" not in software and "OJS" not in software:
                continue
            url = row["dc.identifier.url[pt_BR]"].split("||")[0].strip()
            if urllib.parse.urlsplit(url).netloc:
                journal_counts[installation_key(url)] += 1

    print(f"Revalidando {len(failed)} instalações; uma requisição por instalação.", flush=True)
    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(check, item) for item in failed]
        for index, future in enumerate(as_completed(futures), 1):
            result = future.result()
            result["journals_affected"] = journal_counts[str(result["instance_key"])]
            results.append(result)
            if index % 10 == 0 or index == len(failed):
                print(f"  concluídas {index}/{len(failed)}", flush=True)

    results.sort(key=lambda item: str(item["instance_key"]))
    installation_summary = Counter(str(item["classification"]) for item in results)
    journal_summary: defaultdict[str, int] = defaultdict(int)
    for item in results:
        journal_summary[str(item["classification"])] += int(item["journals_affected"])

    output = {
        "source": str(INPUT.name),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_policy": {
            "scope": "somente instalações que falharam na primeira consulta",
            "requests": len(failed),
            "max_workers": MAX_WORKERS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "retries": 0,
            "max_response_bytes": MAX_BYTES,
        },
        "summary_by_installation": dict(installation_summary.most_common()),
        "summary_by_journal": dict(sorted(journal_summary.items(), key=lambda pair: -pair[1])),
        "instances": results,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = [
        "instance_key",
        "url",
        "journals_affected",
        "previous_http_status",
        "previous_error",
        "http_status",
        "classification",
        "detail",
        "final_url",
        "content_type",
        "checked_at_utc",
    ]
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: item.get(field, "") for field in fields} for item in results)

    print(json.dumps(output["summary_by_installation"], ensure_ascii=False, indent=2), flush=True)
    print(json.dumps(output["summary_by_journal"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
