from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


def _pct(x: float) -> float:
    return round(float(x) * 100, 2)


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default


def _boolish(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    s = str(x).strip().lower()
    return s in {"1", "true", "yes", "si", "sí", "y", "x", "correcto", "ok", "detected", "detectado"}


def _as_records(history: list[dict] | None) -> list[dict]:
    return [h for h in (history or []) if isinstance(h, dict)]


def _history_df(history: list[dict] | None) -> pd.DataFrame:
    records = _as_records(history)
    return pd.DataFrame(records) if records else pd.DataFrame()


def _has_cols(df: pd.DataFrame, cols: list[str]) -> bool:
    return all(c in df.columns for c in cols)


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def _estimate_confusion_from_available_data(findings: pd.DataFrame, hist: pd.DataFrame) -> tuple[int, int, int, str]:
    """Return TP, FP, FN and source label.

    Preferred: use explicit ground-truth/prediction columns if the user imports a labeled validation set.
    Fallback: estimate using analyzed findings with successful LLM output versus open/critical/high findings.
    """
    combined = hist.copy()
    if not findings.empty and not hist.empty and "finding_id" in findings.columns and "finding_id" in hist.columns:
        combined = hist.merge(findings, on="finding_id", how="left", suffixes=("", "_finding"))
    elif not findings.empty and hist.empty:
        combined = findings.copy()

    y_true_col = _first_col(combined, ["y_true", "ground_truth", "ground_truth_label", "actual_label", "actual_vulnerable", "is_vulnerability"])
    y_pred_col = _first_col(combined, ["y_pred", "prediction", "predicted_label", "llm_detected", "predicted_vulnerable"])
    if y_true_col and y_pred_col:
        y_true = combined[y_true_col].map(_boolish)
        y_pred = combined[y_pred_col].map(_boolish)
        tp = int(((y_true == True) & (y_pred == True)).sum())
        fp = int(((y_true == False) & (y_pred == True)).sum())
        fn = int(((y_true == True) & (y_pred == False)).sum())
        return tp, fp, fn, "REAL: columnas etiquetadas importadas"

    if findings.empty:
        return 0, 0, 0, "SIN DATOS"

    total_relevant = int(findings.get("severity", pd.Series(dtype=str)).isin(["Critical", "High"]).sum())
    if total_relevant == 0:
        total_relevant = len(findings)

    if hist.empty:
        return 0, 0, total_relevant, "ESTIMADO: no hay historial LLM"

    successful = hist[hist.get("llm_error", pd.Series([None] * len(hist))).isna()]
    if "llm_response" in successful.columns:
        successful = successful[successful["llm_response"].astype(str).str.len() > 0]
    analyzed_ids = set(successful.get("finding_id", pd.Series(dtype=str)).astype(str).tolist())

    relevant_ids = set(findings.loc[findings.get("severity", pd.Series(dtype=str)).isin(["Critical", "High"]), "finding_id"].astype(str).tolist()) if "finding_id" in findings.columns else set()
    if not relevant_ids and "finding_id" in findings.columns:
        relevant_ids = set(findings["finding_id"].astype(str).tolist())

    tp = len(analyzed_ids & relevant_ids) if relevant_ids else len(analyzed_ids)
    fp = len(analyzed_ids - relevant_ids) if relevant_ids else 0
    fn = max(len(relevant_ids - analyzed_ids), 0) if relevant_ids else max(total_relevant - tp, 0)
    return int(tp), int(fp), int(fn), "ESTIMADO: éxito LLM vs hallazgos Critical/High"


def _count_hallucinations(hist: pd.DataFrame) -> tuple[int, int, str]:
    if hist.empty:
        return 0, 0, "SIN DATOS"
    flag_col = _first_col(hist, ["is_hallucination", "hallucination", "hallucinated", "respuesta_inventada"])
    if flag_col:
        total = int(hist[flag_col].notna().sum())
        return int(hist[flag_col].map(_boolish).sum()), total, "REAL: columna is_hallucination"

    # Conservative automatic heuristic: an answer with explicit LLM error is invalid; otherwise not counted as hallucination.
    total = len(hist)
    errors = int(hist.get("llm_error", pd.Series([None] * len(hist))).notna().sum()) if "llm_error" in hist.columns else 0
    return errors, total, "ESTIMADO: errores LLM como respuestas no confiables"


def _accuracy_from_column(hist: pd.DataFrame, candidates: list[str], regex: str | None = None) -> tuple[int, int, str]:
    if hist.empty:
        return 0, 0, "SIN DATOS"
    col = _first_col(hist, candidates)
    if col:
        total = int(hist[col].notna().sum())
        return int(hist[col].map(_boolish).sum()), total, f"REAL: columna {col}"
    if regex and "llm_response" in hist.columns:
        mask = hist["llm_response"].fillna("").astype(str).str.contains(regex, flags=re.I, regex=True)
        total = int(hist["llm_response"].notna().sum())
        return int(mask.sum()), total, "ESTIMADO: detección por patrón textual"
    return 0, len(hist), "SIN COLUMNA DE VALIDACIÓN"


def _epss_correlation(findings: pd.DataFrame) -> tuple[float, str]:
    if findings.empty:
        return 0.0, "SIN DATOS"
    epss_col = _first_col(findings, ["epss", "epss_score", "probability", "epss_probability"])
    priority_col = _first_col(findings, ["priority_score", "llm_priority_score", "risk_score"])
    if epss_col and priority_col:
        tmp = findings[[epss_col, priority_col]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(tmp) >= 2:
            return round(float(tmp[epss_col].corr(tmp[priority_col], method="spearman")), 4), "REAL: Spearman EPSS vs prioridad"
    return 0.0, "SIN EPSS/priority_score"


def _kev_detection(findings: pd.DataFrame, hist: pd.DataFrame) -> tuple[int, int, str]:
    if findings.empty:
        return 0, 0, "SIN DATOS"
    kev_col = _first_col(findings, ["kev", "cisa_kev", "kev_present", "known_exploited", "in_kev"])
    if not kev_col:
        # approximate if Critical+High and CVE present, but keep denominator 0 to avoid fake metric
        return 0, 0, "SIN COLUMNA KEV"
    kev_df = findings[findings[kev_col].map(_boolish)]
    total = len(kev_df)
    if total == 0:
        return 0, 0, "REAL: no hay KEV presentes"
    detected_col = _first_col(hist, ["kev_detected", "llm_kev_detected"])
    if detected_col:
        return int(hist[detected_col].map(_boolish).sum()), total, "REAL: columna kev_detected"
    if "finding_id" in kev_df.columns and "finding_id" in hist.columns:
        detected = len(set(kev_df["finding_id"].astype(str)) & set(hist["finding_id"].astype(str)))
        return detected, total, "ESTIMADO: KEV analizadas por LLM"
    return 0, total, "SIN HISTORIAL LLM"


def _token_costs(hist: pd.DataFrame, settings: dict | None = None) -> tuple[int, int, float, str]:
    if hist.empty:
        return 0, 0, 0.0, "SIN DATOS"
    in_cols = ["input_tokens", "prompt_tokens", "tokens_input"]
    out_cols = ["output_tokens", "completion_tokens", "tokens_output"]
    ic = _first_col(hist, in_cols)
    oc = _first_col(hist, out_cols)
    input_tokens = int(hist[ic].map(_num).sum()) if ic else 0
    output_tokens = int(hist[oc].map(_num).sum()) if oc else 0

    # Some providers return raw_usage dict. Try common keys.
    if (input_tokens == 0 or output_tokens == 0) and "raw_usage" in hist.columns:
        for usage in hist["raw_usage"].dropna():
            if isinstance(usage, dict):
                input_tokens += int(_num(usage.get("input_tokens", usage.get("prompt_tokens", 0))))
                output_tokens += int(_num(usage.get("output_tokens", usage.get("completion_tokens", 0))))

    cost_col = _first_col(hist, ["cost_usd", "estimated_cost_usd"])
    if cost_col:
        cost = float(hist[cost_col].map(_num).sum())
        return input_tokens, output_tokens, round(cost, 6), "REAL: costo importado"

    # Conservative default: local Ollama cost 0. Cloud costs need configured rates.
    return input_tokens, output_tokens, 0.0, "ESTIMADO: costo local 0; configure tarifas cloud para cálculo financiero"


def calculate_llm_metrics(findings_df: pd.DataFrame | None, history: list[dict] | None, settings: dict | None = None) -> dict[str, pd.DataFrame]:
    findings = findings_df.copy() if isinstance(findings_df, pd.DataFrame) else pd.DataFrame()
    hist = _history_df(history)

    tp, fp, fn, cls_src = _estimate_confusion_from_available_data(findings, hist)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    hallucinations, halluc_total, hall_src = _count_hallucinations(hist)
    halluc_rate = _safe_div(hallucinations, halluc_total)

    total = len(hist)
    successful = 0
    if total:
        successful = total
        if "llm_error" in hist.columns:
            successful = int(hist["llm_error"].isna().sum())
        if "llm_response" in hist.columns:
            successful = int((hist["llm_response"].fillna("").astype(str).str.len() > 0).sum())
    pass_at_1 = _safe_div(successful, total)

    avg_latency = round(float(hist["elapsed_sec"].map(_num).mean()), 3) if (not hist.empty and "elapsed_sec" in hist.columns) else 0.0
    p95_latency = round(float(hist["elapsed_sec"].map(_num).quantile(0.95)), 3) if (not hist.empty and "elapsed_sec" in hist.columns) else 0.0
    fallback_rate = _safe_div(int(hist.get("fallback_used", pd.Series(dtype=object)).notna().sum()) if "fallback_used" in hist.columns else 0, total)

    attack_success_col = _first_col(hist, ["attack_success", "prompt_injection_success", "jailbreak_success"])
    if attack_success_col:
        attack_success = _safe_div(int(hist[attack_success_col].map(_boolish).sum()), int(hist[attack_success_col].notna().sum()))
        attack_src = f"REAL: columna {attack_success_col}"
    else:
        attack_success = 0.0
        attack_src = "SIN PRUEBAS ADVERSARIALES: valor 0 hasta ejecutar test set"

    cve_ok, cve_total, cve_src = _accuracy_from_column(hist, ["cve_correct", "cve_accuracy", "cve_validated"], r"CVE-\d{4}-\d{4,7}")
    mitre_ok, mitre_total, mitre_src = _accuracy_from_column(hist, ["mitre_correct", "mitre_accuracy", "attack_mapping_correct"], r"T\d{4}(\.\d{3})?")
    rem_ok, rem_total, rem_src = _accuracy_from_column(hist, ["remediation_correct", "remediation_accuracy", "remediacion_correcta"], r"parche|actualizar|mitigar|segmentar|hardening|reescaneo|validar")
    epss_corr, epss_src = _epss_correlation(findings)
    kev_detected, kev_total, kev_src = _kev_detection(findings, hist)
    input_tokens, output_tokens, cost_usd, cost_src = _token_costs(hist, settings)

    rows = [
        {"categoria": "Clasificación", "metrica": "Precision", "formula": "TP / (TP + FP)", "valor": _pct(precision), "unidad": "%", "numerador": tp, "denominador": tp + fp, "fuente": cls_src},
        {"categoria": "Clasificación", "metrica": "Recall", "formula": "TP / (TP + FN)", "valor": _pct(recall), "unidad": "%", "numerador": tp, "denominador": tp + fn, "fuente": cls_src},
        {"categoria": "Clasificación", "metrica": "F1 Score", "formula": "2*(Precision*Recall)/(Precision+Recall)", "valor": _pct(f1), "unidad": "%", "numerador": round(2 * precision * recall, 4), "denominador": round(precision + recall, 4), "fuente": cls_src},
        {"categoria": "Confiabilidad", "metrica": "Hallucination Rate", "formula": "Respuestas no confiables / Respuestas totales", "valor": _pct(halluc_rate), "unidad": "%", "numerador": hallucinations, "denominador": halluc_total, "fuente": hall_src},
        {"categoria": "Confiabilidad", "metrica": "Pass@1", "formula": "Respuestas válidas al primer intento / Consultas totales", "valor": _pct(pass_at_1), "unidad": "%", "numerador": successful, "denominador": total, "fuente": "REAL: historial analysis_history" if total else "SIN DATOS"},
        {"categoria": "Rendimiento", "metrica": "Latencia promedio", "formula": "SUM(latencia_i) / N", "valor": avg_latency, "unidad": "s", "numerador": round(float(hist["elapsed_sec"].map(_num).sum()), 3) if (not hist.empty and "elapsed_sec" in hist.columns) else 0, "denominador": total, "fuente": "REAL: elapsed_sec" if total else "SIN DATOS"},
        {"categoria": "Rendimiento", "metrica": "Latencia P95", "formula": "Percentil 95(latencia_i)", "valor": p95_latency, "unidad": "s", "numerador": "P95", "denominador": total, "fuente": "REAL: elapsed_sec" if total else "SIN DATOS"},
        {"categoria": "Arquitectura híbrida", "metrica": "Fallback Rate", "formula": "Consultas con fallback / Consultas totales", "valor": _pct(fallback_rate), "unidad": "%", "numerador": int(hist.get("fallback_used", pd.Series(dtype=object)).notna().sum()) if "fallback_used" in hist.columns else 0, "denominador": total, "fuente": "REAL: fallback_used" if total else "SIN DATOS"},
        {"categoria": "Seguridad LLM", "metrica": "Attack Success Rate", "formula": "Ataques exitosos / Pruebas adversariales", "valor": _pct(attack_success), "unidad": "%", "numerador": int(hist[attack_success_col].map(_boolish).sum()) if attack_success_col else 0, "denominador": int(hist[attack_success_col].notna().sum()) if attack_success_col else 0, "fuente": attack_src},
        {"categoria": "Ciberseguridad", "metrica": "CVE Accuracy", "formula": "CVE interpretados correctamente / CVE analizados", "valor": _pct(_safe_div(cve_ok, cve_total)), "unidad": "%", "numerador": cve_ok, "denominador": cve_total, "fuente": cve_src},
        {"categoria": "Ciberseguridad", "metrica": "MITRE ATT&CK Accuracy", "formula": "Técnicas MITRE correctas / Técnicas evaluadas", "valor": _pct(_safe_div(mitre_ok, mitre_total)), "unidad": "%", "numerador": mitre_ok, "denominador": mitre_total, "fuente": mitre_src},
        {"categoria": "Ciberseguridad", "metrica": "Remediation Accuracy", "formula": "Remediaciones correctas / Remediaciones evaluadas", "valor": _pct(_safe_div(rem_ok, rem_total)), "unidad": "%", "numerador": rem_ok, "denominador": rem_total, "fuente": rem_src},
        {"categoria": "Priorización", "metrica": "EPSS Correlation", "formula": "Spearman(EPSS, prioridad LLM)", "valor": epss_corr, "unidad": "rho", "numerador": "corr", "denominador": "N pares", "fuente": epss_src},
        {"categoria": "Priorización", "metrica": "KEV Detection Rate", "formula": "KEV detectadas / KEV presentes", "valor": _pct(_safe_div(kev_detected, kev_total)), "unidad": "%", "numerador": kev_detected, "denominador": kev_total, "fuente": kev_src},
        {"categoria": "Consumo", "metrica": "Tokens de entrada", "formula": "SUM(input_tokens)", "valor": input_tokens, "unidad": "tokens", "numerador": input_tokens, "denominador": "-", "fuente": cost_src},
        {"categoria": "Consumo", "metrica": "Tokens de salida", "formula": "SUM(output_tokens)", "valor": output_tokens, "unidad": "tokens", "numerador": output_tokens, "denominador": "-", "fuente": cost_src},
        {"categoria": "Costo", "metrica": "Costo estimado", "formula": "SUM((input/1M)*tarifa_in + (output/1M)*tarifa_out)", "valor": cost_usd, "unidad": "USD", "numerador": cost_usd, "denominador": "-", "fuente": cost_src},
    ]

    metrics = pd.DataFrame(rows)

    if not hist.empty and "backend_used" in hist.columns:
        backend = hist.copy()
        if "elapsed_sec" in backend.columns:
            backend["elapsed_sec"] = backend["elapsed_sec"].map(_num)
        perf = backend.groupby("backend_used", dropna=False).agg(
            consultas=("backend_used", "size"),
            latencia_promedio_s=("elapsed_sec", "mean") if "elapsed_sec" in backend.columns else ("backend_used", "size"),
        ).reset_index()
        if "elapsed_sec" in backend.columns:
            perf["latencia_promedio_s"] = perf["latencia_promedio_s"].round(3)
        if "fallback_used" in backend.columns:
            fb = backend.groupby("backend_used")["fallback_used"].apply(lambda s: s.notna().sum()).reset_index(name="fallbacks")
            perf = perf.merge(fb, on="backend_used", how="left")
            perf["fallback_rate_%"] = (perf["fallbacks"] / perf["consultas"] * 100).round(2)
        else:
            perf["fallbacks"] = 0
            perf["fallback_rate_%"] = 0.0
    else:
        perf = pd.DataFrame(columns=["backend_used", "consultas", "latencia_promedio_s", "fallbacks", "fallback_rate_%"])

    # Operational resources: uses columns if a monitoring process populates them.
    resource_cols = []
    for c in ["cpu_pct", "ram_pct", "gpu_pct"]:
        if c in hist.columns:
            resource_cols.append({"recurso": c, "promedio_%": round(float(hist[c].map(_num).mean()), 2), "max_%": round(float(hist[c].map(_num).max()), 2)})
    resources = pd.DataFrame(resource_cols)

    return {"metrics": metrics, "backend_performance": perf, "resources": resources, "history": hist}


def evaluation_metrics(findings_df: pd.DataFrame, history: list[dict]) -> pd.DataFrame:
    """Backward-compatible simple output for older pages."""
    data = calculate_llm_metrics(findings_df, history)["metrics"].copy()
    return data.rename(columns={"metrica": "metric", "valor": "value"})[["metric", "value", "formula", "fuente"]]
