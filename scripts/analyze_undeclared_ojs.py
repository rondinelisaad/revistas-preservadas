#!/usr/bin/env python3
"""Create a conservative passive analysis of journals with no software declaration."""

from __future__ import annotations

import csv
import json
import re
import urllib.parse
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "miguilim_revistas_2026-10-29.csv"
DETECTION = ROOT / "data" / "ojs_instance_detection_2026-10-29.json"
OUTPUT = ROOT / "data" / "ojs_nao_declarado_analise_passiva_2026-10-29.csv"
SUMMARY = ROOT / "data" / "ojs_nao_declarado_analise_passiva_resumo_2026-10-29.json"


def installation_key(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    marker = path.lower().find("/index.php/")
    prefix = path[:marker] if marker >= 0 else ""
    return f"{parsed.netloc.lower()}{prefix.rstrip('/').lower()}"


def main() -> None:
    detected_payload = json.loads(DETECTION.read_text(encoding="utf-8"))
    installations = {item["instance_key"]: item for item in detected_payload["instances"]}
    output_rows: list[dict[str, object]] = []

    with SOURCE.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["dc.description.software[pt_BR]"].strip():
                continue
            url = row["dc.identifier.url[pt_BR]"].split("||")[0].strip()
            parsed = urllib.parse.urlsplit(url)
            key = installation_key(url) if parsed.netloc else ""
            shared = installations.get(key)

            classification = "Não classificado — requer consulta técnica"
            confidence = "Indeterminada"
            version = ""
            evidence = ""
            next_step = "Consultar uma URL representativa da instalação e procurar o meta generator do OJS."

            if not parsed.netloc:
                classification = "Sem URL válida para análise"
                next_step = "Localizar ou corrigir a URL oficial da revista."
            elif shared:
                classification = "OJS provável — instalação compartilhada com declaração explícita"
                confidence = "Alta"
                version = str(shared.get("version") or "")
                if version:
                    evidence = f"Mesma instalação de revista OJS; generator observado: {shared.get('evidence', '')}"
                    next_step = "Validar por amostragem; a versão já foi observada na instalação compartilhada."
                elif shared.get("error"):
                    evidence = f"Mesma instalação declarada como OJS; acesso falhou: {shared.get('error')}"
                    next_step = "Usar o diagnóstico de acesso da instalação compartilhada."
                else:
                    evidence = "Mesma instalação de revista que declara OJS; versão não exposta."
                    next_step = "Confirmar OJS por assinatura HTML/rotas/assets, sem inferir versão."
            else:
                signals: list[str] = []
                if "/index.php/" in parsed.path.lower():
                    signals.append("URL contém /index.php/")
                if "ojs" in parsed.netloc.lower():
                    signals.append("hostname contém ojs")
                if re.search(r"(periodic|revista|journal|seer)", parsed.netloc, re.IGNORECASE):
                    signals.append("hostname sugere portal editorial")
                if signals:
                    confidence = "Baixa — indício, não confirmação"
                    evidence = "; ".join(signals)

            output_rows.append(
                {
                    "titulo": row["dc.title[pt_BR]"],
                    "issn": row["dc.identifier.issn[pt_BR]"],
                    "situacao": row["dc.description.situation[pt_BR]"],
                    "url": url,
                    "installation_key": key,
                    "classificacao_passiva": classification,
                    "confianca": confidence,
                    "versao_ojs_inferida_da_instalacao": version,
                    "evidencia": evidence,
                    "proxima_etapa": next_step,
                    "id_miguilim": row["id"],
                }
            )

    fields = list(output_rows[0])
    with OUTPUT.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    classification_counts = Counter(str(row["classificacao_passiva"]) for row in output_rows)
    version_count = sum(bool(row["versao_ojs_inferida_da_instalacao"]) for row in output_rows)
    low_signal_count = sum(str(row["confianca"]).startswith("Baixa") for row in output_rows)
    unique_remaining = {
        str(row["installation_key"])
        for row in output_rows
        if row["classificacao_passiva"] == "Não classificado — requer consulta técnica"
        and row["installation_key"]
    }
    summary = {
        "total_sem_declaracao": len(output_rows),
        "classificacao": dict(classification_counts),
        "com_versao_inferida_de_instalacao_confirmada": version_count,
        "com_indicios_fracos_de_url": low_signal_count,
        "instalacoes_restantes_para_consulta": len(unique_remaining),
        "method_note": (
            "A inferência de alta confiança exige a mesma chave de instalação de uma revista com declaração "
            "explícita de OJS. Padrões de URL são apenas indícios e não foram convertidos em confirmação."
        ),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
