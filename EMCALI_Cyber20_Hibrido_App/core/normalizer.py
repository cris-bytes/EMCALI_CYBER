from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

UNIFIED_COLUMNS = [
    "finding_id", "source", "asset", "ip", "os", "severity", "cvss", "cve", "title",
    "status", "exploitability", "business_service", "patch_available", "description", "recommendation",
    "epss", "epss_percentile", "cisa_kev", "published_date", "modified_date", "raw_source_type"
]

ALIASES = {
    "qid": "external_id",
    "plugin_id": "external_id",
    "host": "asset",
    "hostname": "asset",
    "dns": "asset",
    "severity_level": "severity",
    "cve_id": "cve",
    "cveid": "cve",
    "cve-id": "cve",
    "service": "business_service",
    "basescore": "cvss",
    "cvssscore": "cvss",
    "cvss_v3": "cvss",
    "cvss_v3_score": "cvss",
    "cvssv3": "cvss",
    "cvss_v31": "cvss",
    "cvss_v2": "cvss_v2",
    "base_score": "cvss",
    "epss_score": "epss",
    "epsspercentile": "epss_percentile",
    "percentile": "epss_percentile",
    "is_kev": "cisa_kev",
    "known_exploited": "cisa_kev",
    "datepublished": "published_date",
    "published": "published_date",
    "datemodified": "modified_date",
    "modified": "modified_date",
    "summary": "description",
    "details": "description",
    "vendorproject": "vendor_project",
    "product": "product_name",
    "cwe": "cwe_id",
    "cwe_id": "cwe_id",
    "attackvector": "attack_vector",
    "attackcomplexity": "attack_complexity",
    "privilegesrequired": "privileges_required",
    "userinteraction": "user_interaction",
}

SEVERITY_NORMALIZATION = {
    "5": "Critical", "4": "High", "3": "Medium", "2": "Low", "1": "Low",
    "critical": "Critical", "high": "High", "medium": "Medium", "low": "Low",
    "crITICAL": "Critical",
}


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    clean_map = {}
    for col in work.columns:
        clean = str(col).strip()
        normalized = clean.lower().replace(" ", "_")
        normalized = normalized.replace("/", "_").replace("-", "_")
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        clean_map[col] = normalized
    work = work.rename(columns=clean_map)
    work = work.rename(columns={c: ALIASES.get(c, c) for c in work.columns})
    return work


def _safe_str(value, default: str = "") -> str:
    if pd.isna(value):
        return default
    text = str(value).strip()
    return text if text else default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "si", "sí", "yes", "y", "kev", "known_exploited", "actively exploited"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def _severity_from_cvss(cvss: float) -> str:
    if cvss >= 9.0:
        return "Critical"
    if cvss >= 7.0:
        return "High"
    if cvss >= 4.0:
        return "Medium"
    return "Low"


def _exploitability_from_signals(cvss: float, epss: float, cisa_kev: bool) -> str:
    if cisa_kev or epss >= 0.7 or cvss >= 9.0:
        return "High"
    if epss >= 0.2 or cvss >= 6.0:
        return "Medium"
    return "Low"


def _pick_first(row: pd.Series, candidates: list[str], default=None):
    for candidate in candidates:
        if candidate in row and not pd.isna(row[candidate]) and str(row[candidate]).strip() != "":
            return row[candidate]
    return default


def _infer_source_type(filename: str, columns: list[str]) -> tuple[str, list[str]]:
    notes = []
    lower_name = filename.lower()
    cols = set(columns)

    if "cve_cisa_epss_enriched_dataset" in lower_name or {"epss", "cisa_kev"}.issubset(cols):
        notes.append("Se detectó formato enriquecido NVD + CISA KEV + EPSS.")
        return "Kaggle:NVD+CISA+EPSS", notes
    if "cve_corpus" in lower_name:
        notes.append("Se detectó un corpus de CVEs orientado a texto/descripción.")
        return "Kaggle:CVE Corpus", notes
    if {"qid", "severity"}.intersection(cols) or "qualys" in lower_name:
        notes.append("Se detectó exportación tipo Qualys.")
        return "Qualys", notes
    if {"plugin_id", "cvss"}.intersection(cols) or "tenable" in lower_name or "nessus" in lower_name:
        notes.append("Se detectó exportación tipo Tenable / Nessus.")
        return "Tenable", notes
    notes.append("Se aplicó normalización genérica de columnas.")
    return "CSV/JSON", notes


def _normalize_generic_records(df: pd.DataFrame, source_hint: str, detected_type: str) -> pd.DataFrame:
    records = []
    for idx, row in df.iterrows():
        cvss = _safe_float(_pick_first(row, ["cvss", "cvss_v31", "cvss_v3", "cvss_v2"], 0.0), 0.0)
        epss = _safe_float(_pick_first(row, ["epss"], 0.0), 0.0)
        epss_percentile = _safe_float(_pick_first(row, ["epss_percentile"], 0.0), 0.0)
        cisa_kev = _safe_bool(_pick_first(row, ["cisa_kev"], False), False)

        severity_value = _pick_first(row, ["severity", "base_severity", "cvss_v3_severity", "cvss_v31_severity"])
        severity = _safe_str(severity_value, "")
        severity = SEVERITY_NORMALIZATION.get(severity.lower(), severity.title() if severity else "")
        if not severity:
            severity = _severity_from_cvss(cvss)

        asset = _safe_str(_pick_first(row, ["asset", "vendor_project", "product_name", "cve"], "Activo no identificado"), "Activo no identificado")
        title = _safe_str(_pick_first(row, ["title", "product_name", "description", "cve"], "Hallazgo sin título"), "Hallazgo sin título")
        description = _safe_str(_pick_first(row, ["description", "title", "product_name"], "Sin descripción"), "Sin descripción")
        cve = _safe_str(_pick_first(row, ["cve", "cve_id"], "N/A"), "N/A")
        recommendation = _safe_str(_pick_first(row, ["recommendation"], "Validar criticidad, priorizar tratamiento y documentar plan de remediación."), "Validar criticidad, priorizar tratamiento y documentar plan de remediación.")
        exploitability = _safe_str(_pick_first(row, ["exploitability", "attack_complexity"], ""), "")
        if not exploitability or exploitability.lower() in {"low", "high", "medium"}:
            exploitability = _exploitability_from_signals(cvss, epss, cisa_kev)
        else:
            exploitability = _exploitability_from_signals(cvss, epss, cisa_kev)

        record = {
            "finding_id": _safe_str(_pick_first(row, ["finding_id", "external_id"], f"N-{idx+1:05d}"), f"N-{idx+1:05d}"),
            "source": _safe_str(_pick_first(row, ["source"], source_hint), source_hint),
            "asset": asset,
            "ip": _safe_str(_pick_first(row, ["ip", "ip_address"], "N/A"), "N/A"),
            "os": _safe_str(_pick_first(row, ["os"], "N/A"), "N/A"),
            "severity": severity,
            "cvss": cvss,
            "cve": cve,
            "title": title[:180],
            "status": _safe_str(_pick_first(row, ["status"], "Actively Exploited" if cisa_kev else "Open"), "Open"),
            "exploitability": exploitability,
            "business_service": _safe_str(_pick_first(row, ["business_service"], "Servicio no clasificado"), "Servicio no clasificado"),
            "patch_available": _safe_bool(_pick_first(row, ["patch_available"], False), False),
            "description": description,
            "recommendation": recommendation,
            "epss": epss,
            "epss_percentile": epss_percentile,
            "cisa_kev": cisa_kev,
            "published_date": _safe_str(_pick_first(row, ["published_date", "first_seen"], ""), ""),
            "modified_date": _safe_str(_pick_first(row, ["modified_date", "last_seen"], ""), ""),
            "raw_source_type": detected_type,
        }
        records.append(record)

    normalized = pd.DataFrame(records)
    for col in UNIFIED_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = "" if col not in {"cvss", "epss", "epss_percentile", "patch_available", "cisa_kev"} else 0.0
    return normalized[UNIFIED_COLUMNS]


def _normalize_unified_json(payload: dict) -> tuple[pd.DataFrame, str, list[str]]:
    rows = []
    for idx, item in enumerate(payload.get("vulnerability_report", []), start=1):
        asset = item.get("asset_identifier", {})
        vuln = item.get("vulnerability_details", {})
        rows.append({
            "finding_id": f"J-{idx:05d}",
            "source": payload.get("scan_metadata", {}).get("source_tool", "JSON"),
            "asset": asset.get("hostname") or asset.get("ip") or "Activo no identificado",
            "ip": asset.get("ip", "N/A"),
            "os": asset.get("os", "N/A"),
            "severity": vuln.get("severity", "Medium"),
            "cvss": vuln.get("cvss_v3_score", 5.0),
            "cve": ", ".join(vuln.get("cve_ids", [])) if isinstance(vuln.get("cve_ids", []), list) else vuln.get("cve_ids", "N/A"),
            "title": vuln.get("name", "Hallazgo sin título"),
            "status": "Open",
            "exploitability": "Medium",
            "business_service": "Servicio no clasificado",
            "patch_available": False,
            "description": vuln.get("description", "Sin descripción"),
            "recommendation": vuln.get("solution", "Validar tratamiento"),
            "epss": 0.0,
            "epss_percentile": 0.0,
            "cisa_kev": False,
            "published_date": "",
            "modified_date": "",
            "raw_source_type": "Unified JSON Schema",
        })
    df = pd.DataFrame(rows)
    notes = ["Se detectó JSON en esquema unificado de la aplicación."]
    return df[UNIFIED_COLUMNS], payload.get("scan_metadata", {}).get("source_tool", "JSON"), notes


def normalize_uploaded_file(uploaded_file) -> pd.DataFrame:
    filename = uploaded_file.name
    suffix = Path(filename).suffix.lower()

    if suffix == ".csv":
        raw_df = pd.read_csv(uploaded_file)
    elif suffix == ".json":
        payload = json.load(uploaded_file)
        if isinstance(payload, dict) and isinstance(payload.get("vulnerability_report"), list):
            df, source_hint, notes = _normalize_unified_json(payload)
            df.attrs["detected_format"] = "Unified JSON Schema"
            df.attrs["normalization_notes"] = notes
            df.attrs["original_columns"] = list(df.columns)
            return df
        raw_df = pd.DataFrame(payload if isinstance(payload, list) else [payload])
    elif suffix in {".xlsx", ".xls"}:
        raw_df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Formato no soportado. Use CSV, JSON o Excel (XLSX/XLS).")

    cleaned = _clean_columns(raw_df)
    source_hint, notes = _infer_source_type(filename, list(cleaned.columns))
    normalized = _normalize_generic_records(cleaned, source_hint=source_hint, detected_type=source_hint)

    if "severity" not in raw_df.columns and "cvss" in normalized.columns:
        notes.append("La severidad no venía explícita; se calculó automáticamente a partir de CVSS.")
    if "epss" in cleaned.columns:
        notes.append("Se conservó EPSS como señal de explotabilidad.")
    if "cisa_kev" in cleaned.columns:
        notes.append("Se conservó la bandera CISA KEV para priorización operativa.")

    normalized.attrs["detected_format"] = source_hint
    normalized.attrs["normalization_notes"] = notes
    normalized.attrs["original_columns"] = list(raw_df.columns)
    return normalized
