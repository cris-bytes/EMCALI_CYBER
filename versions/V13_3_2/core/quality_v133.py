"""V13.3 experimental: evidence-aware, conservative defensive validation."""
import math
import re
from .risk_engine_v1332 import evaluate

HEADINGS = ["resumen ejecutivo", "impacto técnico", "impacto de negocio", "priorización", "plan de remediación", "validaciones posteriores"]

def numeric(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None

def truthy(value):
    return str(value).strip().lower() in {"true", "1", "yes", "si", "sí", "actively exploited"}

def risk_assessment(row):
    cvss = numeric(row.get("cvss"))
    epss = numeric(row.get("epss"))
    kev = truthy(row.get("cisa_kev"))
    status = str(row.get("status") or "").lower()
    active = kev or "actively exploited" in status
    criticality = str(row.get("business_service") or "") in {"Finanzas", "Facturación", "Operación OT"}
    if active:
        band = "Atención prioritaria (explotación reportada)"
    elif cvss is None:
        band = "Pendiente de evaluación (CVSS desconocido)"
    elif cvss >= 9:
        band = "Crítico"
    elif cvss >= 7:
        band = "Alto"
    elif cvss >= 4:
        band = "Medio"
    else:
        band = "Bajo (provisional)"
    assessment = evaluate(row)
    return {"score": assessment["score"], "band": assessment["band"],
            "cisa_kev": kev, "active_exploitation_signal": active,
            "cvss_missing": cvss is None, "epss_missing": epss is None,
            "missing_factors": assessment["missing_factors"],
            "coverage_pct": assessment["coverage_pct"],
            "method": assessment["method"]}

def relevant_documents(docs, row):
    cve = str(row.get("cve") or "").lower()
    title = str(row.get("title") or "").lower()
    terms = {t for t in re.findall(r"[a-z0-9]+", title) if len(t) >= 4 and t not in {"multiple", "products", "vulnerability"}}
    selected, excluded = [], []
    for doc in docs:
        body = (str(doc.get("title", "")) + " " + str(doc.get("content", ""))).lower()
        # Cross-product remediation is excluded; general playbooks are allowed as policy only.
        is_specific = bool(cve and cve in body) or any(t in body for t in terms)
        generic = any(k in body for k in ("priorización de vulnerabilidades", "gestión de vulnerabilidades", "risk management"))
        if is_specific or generic:
            selected.append(doc)
        else:
            excluded.append(str(doc.get("title", "sin título")))
    return selected[:3], excluded

def validate_response(text, risk, docs):
    content = (text or "").lower()
    headings = {h: h in content for h in HEADINGS}
    complete = bool(content.strip()) and all(headings.values())
    flags = []
    if not complete: flags.append("Estructura incompleta")
    if risk["cvss_missing"]: flags.append("CVSS oficial no disponible")
    if risk["active_exploitation_signal"] and risk["score"] is None: flags.append("Riesgo cuantitativo pendiente; explotación reportada")
    if "java" in content or "log4j" in content: flags.append("Revisar posible contaminación RAG Java/Log4j")
    return {"execution_success": bool(content.strip()), "structure_valid": complete,
            "risk_consistent": None, "evidence_grounded": None,
            "headings_present": headings, "review_flags": flags,
            "human_review_required": True}
