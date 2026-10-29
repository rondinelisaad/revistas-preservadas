#!/usr/bin/env python3
"""Cross Miguilim journals with Brazilian Keepers Registry memberships."""

from __future__ import annotations

import csv
import json
import re
import urllib.parse
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGUILIM_CSV = ROOT / "data" / "miguilim_revistas_2026-10-29.csv"
KEEPERS_CSV = ROOT / "data" / "keepers_brazil_agencies_2026-10-29.csv"
DETAIL_CSV = ROOT / "data" / "revistas_preservacao_detalhe_2026-10-29.csv"
DETAIL_JSON = ROOT / "data" / "revistas_preservacao_detalhe_2026-10-29.json"
SUMMARY_JSON = ROOT / "data" / "revistas_preservacao_resumo_2026-10-29.json"
OJS_DETECTION_JSON = ROOT / "data" / "ojs_instance_detection_2026-10-29.json"
OJS_ACTIVE_SCAN_JSON = ROOT / "data" / "ojs_undeclared_active_scan_2026-10-29.json"
OJS_REVALIDATION_JSON = ROOT / "data" / "ojs_access_revalidation_2026-10-29.json"
OJS_DECLARATION_RE = re.compile(r"(?:Open Journal Systems|\bOJS\b)", re.IGNORECASE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def pct(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def installation_key(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    marker = path.lower().find("/index.php/")
    prefix = path[:marker] if marker >= 0 else ""
    return f"{parsed.netloc.lower()}{prefix.rstrip('/').lower()}"


def main() -> None:
    keepers = {row["issn"].upper(): row for row in read_csv(KEEPERS_CSV)}
    ojs_payload = json.loads(OJS_DETECTION_JSON.read_text(encoding="utf-8"))
    ojs_by_instance = {row["instance_key"]: row for row in ojs_payload["instances"]}
    active_payload = json.loads(OJS_ACTIVE_SCAN_JSON.read_text(encoding="utf-8"))
    active_by_instance = {row["instance_key"]: row for row in active_payload["instances"]}
    revalidation_payload = json.loads(OJS_REVALIDATION_JSON.read_text(encoding="utf-8"))
    revalidation_by_instance = {
        row["instance_key"]: row for row in revalidation_payload["instances"]
    }
    source_rows = read_csv(MIGUILIM_CSV)
    detail: list[dict[str, object]] = []

    for source in source_rows:
        issn = source["dc.identifier.issn[pt_BR]"].strip().upper()
        keeper = keepers.get(issn)
        preserved = keeper is not None
        situation_raw = source["dc.description.situation[pt_BR]"].strip()
        situation = "Descontinuada" if situation_raw.startswith("Descontinuada") else "Vigente"
        agency_count = int(keeper["agency_count"]) if keeper else 0
        agencies = keeper["agencies"] if keeper else ""
        software_declared = source["dc.description.software[pt_BR]"].strip()
        journal_url = source["dc.identifier.url[pt_BR]"].split("||")[0].strip()
        uses_ojs = bool(OJS_DECLARATION_RE.search(software_declared))
        valid_url = bool(journal_url and urllib.parse.urlsplit(journal_url).netloc)
        key = installation_key(journal_url) if valid_url else ""
        ojs_result = ojs_by_instance.get(key) if key else None
        active_result = active_by_instance.get(key) if key else None
        revalidation_result = revalidation_by_instance.get(key) if key else None
        technical_result = ""
        error_code = ""
        consulted_url = ""
        evidence = ""
        if uses_ojs:
            ojs_use_status = "Sim"
            technical_result = "OJS declarado no Miguilim"
            consulted_url = str(ojs_result["representative_url"]) if ojs_result else journal_url
            evidence = str(ojs_result.get("evidence", "")) if ojs_result else ""
            if ojs_result and ojs_result.get("version"):
                ojs_verification = "Versão detectada no site"
                ojs_version = str(ojs_result["version"])
            elif ojs_result and ojs_result.get("error"):
                if revalidation_result and revalidation_result.get("classification") == "HTTP 200":
                    ojs_verification = "Site respondeu na revalidação; versão não reavaliada"
                else:
                    ojs_verification = "OJS declarado; acesso não concluído"
                error_code = (
                    str(revalidation_result.get("classification", ""))
                    if revalidation_result
                    else str(ojs_result.get("error", ""))
                )
                ojs_version = ""
            elif ojs_result:
                ojs_verification = "OJS declarado; versão não exposta"
                ojs_version = ""
            else:
                ojs_verification = "OJS declarado; URL inválida ou ausente"
                ojs_version = ""
        elif software_declared:
            ojs_use_status = "Outro software declarado"
            technical_result = "Outro software declarado"
            ojs_verification = "Não se aplica"
            ojs_version = ""
        else:
            ojs_use_status = "Não identificado no Miguilim"
            if ojs_result:
                technical_result = "OJS provável — instalação compartilhada"
                consulted_url = str(ojs_result.get("representative_url", journal_url))
                evidence = str(ojs_result.get("evidence", ""))
                ojs_version = str(ojs_result.get("version", ""))
                if ojs_version:
                    ojs_verification = "Versão inferida da instalação compartilhada"
                elif ojs_result.get("error"):
                    ojs_verification = "Instalação compartilhada; acesso não concluído"
                    error_code = (
                        str(revalidation_result.get("classification", ""))
                        if revalidation_result
                        else str(ojs_result.get("error", ""))
                    )
                else:
                    ojs_verification = "Instalação compartilhada; versão não exposta"
            elif active_result:
                classification = str(active_result.get("classification", ""))
                technical_result = {
                    "OJS confirmado": "OJS confirmado tecnicamente",
                    "OJS provável": "OJS provável por assinaturas técnicas",
                    "OJS não identificado": "OJS não identificado na página consultada",
                    "Acesso não concluído": "Consulta técnica não concluída",
                }.get(classification, classification or "Consulta técnica sem resultado")
                ojs_verification = technical_result
                ojs_version = str(active_result.get("version", ""))
                consulted_url = str(active_result.get("representative_url", journal_url))
                evidence = "||".join(str(item) for item in active_result.get("signatures", []))
                error_code = str(active_result.get("network_error", ""))
            else:
                technical_result = "Sem URL válida para análise"
                ojs_verification = "Sem URL válida para análise"
                ojs_version = ""

        detail.append(
            {
                "titulo": source["dc.title[pt_BR]"].strip(),
                "issn": issn,
                "issn_l": source["dc.identifier.issnl[pt_BR]"].strip().upper(),
                "situacao": situation,
                "estado_preservacao": (
                    "Com registro em agência no Keepers" if preserved else "Sem registro em agência no Keepers"
                ),
                "quantidade_agencias": agency_count,
                "agencias": agencies,
                "estrategia_declarada_miguilim": source[
                    "dc.description.digitalpreservation[pt_BR]"
                ].strip(),
                "software_declarado_miguilim": software_declared,
                "usa_ojs": ojs_use_status,
                "resultado_analise_ojs": technical_result,
                "versao_ojs_detectada": ojs_version,
                "estado_verificacao_ojs": ojs_verification,
                "codigo_erro_site": error_code,
                "url_consultada_ojs": consulted_url,
                "evidencia_ojs": evidence,
                "instituicao_editora": source["dc.publisher.name[pt_BR]"].strip(),
                "uf": source["dc.description.state[pt_BR]"].strip(),
                "cidade": source["dc.description.city[pt_BR]"].strip(),
                "ano_inicio": source["dc.date.startyear[pt_BR]"].strip(),
                "ano_fim": source["dc.date.endyear[pt_BR]"].strip(),
                "url_miguilim": source["dc.identifier.uri[pt_BR]"].strip(),
                "url_archival_status": f"https://keepers.issn.org/resource/ISSN/{issn}",
                "data_atualizacao_miguilim": source["dc.date.update[pt_BR]"].strip(),
                "id_miguilim": source["id"].strip(),
            }
        )

    fieldnames = list(detail[0])
    with DETAIL_CSV.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detail)
    DETAIL_JSON.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")

    total_by_status = Counter(row["situacao"] for row in detail)
    preserved_rows = [row for row in detail if row["quantidade_agencias"] > 0]
    preserved_by_status = Counter(row["situacao"] for row in preserved_rows)
    agency_count_distribution = Counter(row["quantidade_agencias"] for row in preserved_rows)
    agency_coverage: Counter[str] = Counter()
    for row in preserved_rows:
        for agency in str(row["agencias"]).split("||"):
            if agency:
                agency_coverage[agency] += 1
    ojs_use_counts = Counter(str(row["usa_ojs"]) for row in detail)
    ojs_analysis_counts = Counter(str(row["resultado_analise_ojs"]) for row in detail)
    ojs_verification_counts = Counter(str(row["estado_verificacao_ojs"]) for row in detail if row["usa_ojs"] == "Sim")
    ojs_version_counts = Counter(str(row["versao_ojs_detectada"]) for row in detail if row["versao_ojs_detectada"])
    ojs_family_counts = Counter(
        ".".join(str(row["versao_ojs_detectada"]).split(".")[:2])
        for row in detail
        if row["versao_ojs_detectada"]
    )

    status_summary = []
    for situation in ("Vigente", "Descontinuada"):
        total = total_by_status[situation]
        preserved = preserved_by_status[situation]
        status_summary.append(
            {
                "situacao": situation,
                "total": total,
                "com_registro_keepers": preserved,
                "sem_registro_keepers": total - preserved,
                "percentual_com_registro": pct(preserved, total),
            }
        )

    summary = {
        "total_revistas": len(detail),
        "com_registro_keepers": len(preserved_rows),
        "sem_registro_keepers": len(detail) - len(preserved_rows),
        "percentual_com_registro": pct(len(preserved_rows), len(detail)),
        "com_duas_ou_mais_agencias": sum(
            count for agency_count, count in agency_count_distribution.items() if agency_count >= 2
        ),
        "status_summary": status_summary,
        "agency_count_distribution": [
            {"quantidade_agencias": count, "revistas": agency_count_distribution[count]}
            for count in sorted(agency_count_distribution)
        ],
        "agency_coverage": [
            {"agencia": agency, "revistas_miguilim": count}
            for agency, count in agency_coverage.most_common()
        ],
        "ojs_summary": {
            "use_status": [
                {"status": status, "revistas": count}
                for status, count in ojs_use_counts.most_common()
            ],
            "verification_status": [
                {"status": status, "revistas": count}
                for status, count in ojs_verification_counts.most_common()
            ],
            "analysis_status": [
                {"status": status, "revistas": count}
                for status, count in ojs_analysis_counts.most_common()
            ],
            "versions": [
                {"versao": version, "revistas": count}
                for version, count in ojs_version_counts.most_common()
            ],
            "version_families": [
                {"familia": family, "revistas": count}
                for family, count in ojs_family_counts.most_common()
            ],
        },
        "method": {
            "miguilim_source": "https://miguilim.ibict.br/simple-search (coleção Revistas científicas)",
            "keepers_source": "https://keepers.issn.org/advancedsearch (Country: Brazil; The Keepers: yes)",
            "match_key": "ISSN do campo dc.identifier.issn do Miguilim",
            "definition": (
                "Com registro em agência no Keepers significa que o ISSN aparece em pelo menos uma "
                "faceta de agência do Archival Status. A contagem considera agências distintas."
            ),
            "retrieval_date": "2026-10-29",
            "ojs_definition": (
                "A declaração explícita vem do campo Software utilizado do Miguilim. Nos registros sem "
                "declaração, a análise técnica usa uma página representativa por instalação, assinaturas "
                "públicas do OJS e correlação com instalações compartilhadas."
            ),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
