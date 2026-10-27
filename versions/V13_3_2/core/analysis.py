from __future__ import annotations
import time
import pandas as pd
from .llm_clients import call_ollama, call_openai, call_anthropic, call_gemini
from .enrichment import query_nvd_cve
from .quality_v133 import risk_assessment, relevant_documents, validate_response
from .risk_engine_v1332 import evaluate_dataframe, evaluate



# === EMCALI_PATCH_V6_ENTERPRISE_LLM_REQUESTS_WRAPPER ===
try:
    import requests as _emcali_requests_v6
    from core.llm_runtime import load_config as _emcali_load_config_v6
    if not hasattr(_emcali_requests_v6, "_emcali_original_post_v6"):
        _emcali_requests_v6._emcali_original_post_v6 = _emcali_requests_v6.post
        def _emcali_post_v6(url, *args, **kwargs):
            try:
                cfg = _emcali_load_config_v6()
                url_s = str(url)
                if ("11434" in url_s) or ("/api/generate" in url_s) or ("/api/chat" in url_s):
                    kwargs["timeout"] = int(cfg.get("ollama_timeout", 900))
                    payload = kwargs.get("json")
                    if isinstance(payload, dict):
                        payload["stream"] = bool(cfg.get("enable_streaming", False))
                        payload["model"] = cfg.get("model_name", "phi3:mini")
                        if isinstance(payload.get("prompt"), str) and len(payload["prompt"]) > 5000:
                            payload["prompt"] = payload["prompt"][:5000] + "\n\n[Contexto recortado por EMCALI Patch V6.]"
                        options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
                        options["num_predict"] = int(cfg.get("ollama_num_predict", 256))
                        options["num_ctx"] = int(cfg.get("ollama_num_ctx", 2048))
                        options["temperature"] = float(cfg.get("temperature", 0.1))
                        payload["options"] = options
                        kwargs["json"] = payload
            except Exception:
                pass
            return _emcali_requests_v6._emcali_original_post_v6(url, *args, **kwargs)
        _emcali_requests_v6.post = _emcali_post_v6
except Exception:
    pass
# === FIN EMCALI_PATCH_V6_ENTERPRISE_LLM_REQUESTS_WRAPPER ===

SEVERITY_WEIGHT = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
EXPLOIT_WEIGHT = {'High': 1.3, 'Medium': 1.0, 'Low': 0.7}


def compute_priority_score(row: pd.Series) -> float | None:
    return evaluate(row)["score"]


def classify_business_impact(score: float) -> str:
    if score is None or pd.isna(score):
        return "Pendiente de evaluación"
    if score >= 35:
        return 'Muy alto'
    if score >= 22:
        return 'Alto'
    if score >= 12:
        return 'Medio'
    return 'Bajo'


def search_knowledge_base(knowledge_base: list[dict], query: str, top_k: int = 3) -> list[dict]:
    tokens = {tok.lower() for tok in query.replace(',', ' ').split() if tok.strip()}
    results = []
    for doc in knowledge_base:
        haystack = ' '.join([doc['title'], doc['category'], doc['content'], ' '.join(doc.get('tags', []))]).lower()
        score = sum(1 for tok in tokens if tok in haystack)
        if score > 0:
            enriched = dict(doc)
            enriched['score'] = score
            results.append(enriched)
    results.sort(key=lambda item: item['score'], reverse=True)
    return results[:top_k]


def build_prompt(row: pd.Series, retrieved_docs: list[dict], user_query: str, system_prompt_template: str, nvd_context: dict | None = None) -> str:
    evidence_block = '\n\n'.join([f"[{doc['title']}]\n{doc['content']}" for doc in retrieved_docs[:3]]) if retrieved_docs else 'Sin evidencia documental adicional.'
    nvd_block = ''
    if nvd_context:
        nvd_block = f"Contexto externo NVD:\n- CVE: {nvd_context.get('cve_id')}\n- Published: {nvd_context.get('published')}\n- Last Modified: {nvd_context.get('last_modified')}\n- Description: {nvd_context.get('description')}"
    return f"{system_prompt_template}\n\nREGLAS DE CALIDAD: CVSS/EPSS no disponibles no equivalen a cero; no inventes datos. Si hay versiones corregidas en NVD, no afirmes que no existe parche. Usa solo documentos RAG pertinentes al CVE/producto y marca incertidumbres. Un servicio no clasificado NO significa que no sea crítico. No asegures que hay parche ni recomiendes uno concreto sin verificar disponibilidad y versión afectada en fuentes oficiales. Distingue hechos documentados de hipótesis. No afirmes que la validación de la remediación ya se completó.\n\n\n\nSolicitud del analista:\n{user_query}\n\nHallazgo:\n- ID: {row.get('finding_id')}\n- Fuente: {row.get('source')}\n- Activo: {row.get('asset')}\n- IP: {row.get('ip')}\n- Sistema operativo: {row.get('os')}\n- Severidad: {row.get('severity')}\n- CVSS: {'No disponible' if pd.isna(row.get('cvss')) else row.get('cvss')}\n- CVE: {row.get('cve')}\n- Título: {row.get('title')}\n- Estado: {row.get('status')}\n- Explotabilidad: {row.get('exploitability')}\n- Servicio de negocio: {row.get('business_service')}\n- Parche disponible: {'Sin verificar' if row.get('patch_available') is None else row.get('patch_available')}\n- Recomendación base: {row.get('recommendation')}\n\nEvidencia recuperada por RAG:\n{evidence_block}\n\n{nvd_block}\n\nResponde con esta estructura:\n1. Resumen ejecutivo\n2. Impacto técnico\n3. Impacto de negocio\n4. Priorización\n5. Plan de remediación defensiva\n6. Validaciones posteriores"


def _call_backend(prompt: str, settings: dict) -> dict:
    backend = settings['backend']
    if backend == 'ollama':
        return call_ollama(prompt, settings['model_name'], settings['ollama_base_url'], settings['ollama_timeout_sec'])
    if backend == 'openai':
        return call_openai(prompt, settings.get('openai_model', settings['model_name']))
    if backend == 'anthropic':
        return call_anthropic(prompt, settings.get('anthropic_model', settings['model_name']))
    if backend == 'gemini':
        return call_gemini(prompt, settings.get('gemini_model', settings['model_name']))
    return {'text': '', 'raw': None, 'usage': None}


def analyze_finding(row: pd.Series, retrieved_docs: list[dict], settings: dict, user_query: str) -> dict:
    risk = risk_assessment(row)
    score = risk["score"]
    impact = risk["band"]
    retrieved_docs, excluded_docs = relevant_documents(retrieved_docs, row)
    evidence = '; '.join(doc['title'] for doc in retrieved_docs[:3]) if retrieved_docs else 'Sin evidencia recuperada'
    summary = f"Hallazgo {row['finding_id']} en {row['asset']}: {impact}. CVSS: {'no disponible' if score is None else row.get('cvss')}. Requiere revisión del analista."
    result = {'backend_used': settings['backend'], 'model_name': settings['model_name'], 'priority_score': score, 'business_impact': impact, 'executive_summary': summary, 'recommended_actions': [row['recommendation'], 'Confirmar ventana de cambio y responsable técnico.', 'Ejecutar reescaneo posterior y cerrar evidencia en reporte.'], 'retrieved_evidence': evidence, 'validated_output': False, 'risk_assessment': risk, 'excluded_rag_documents': excluded_docs, 'quality_validation': None, 'llm_response': None, 'llm_error': None, 'prompt_used': None, 'external_context': None, 'elapsed_sec': None, 'fallback_used': None}
    external_context = query_nvd_cve(str(row.get('cve', ''))) if settings.get('internet_enrichment', False) else None
    result['external_context'] = external_context
    prompt = build_prompt(row, retrieved_docs, user_query, settings.get('system_prompt_template', ''), external_context)
    result['prompt_used'] = prompt
    if settings['backend'] == 'mock':
        result['llm_response'] = 'Modo mock activo. La aplicación puede conectarse a Ollama o a un backend cloud cuando se configure una credencial válida.'
        return result
    start = time.time()
    try:
        llm = _call_backend(prompt, settings)
        result['llm_response'] = llm.get('text')
        result['raw_usage'] = llm.get('usage')
        result['quality_validation'] = validate_response(result['llm_response'], risk, retrieved_docs)
        result['validated_output'] = bool(result['quality_validation']['structure_valid']) and not result['quality_validation']['review_flags']
    except Exception as exc:
        result['llm_error'] = f'No fue posible consultar {settings["backend"]}: {exc}'
        if settings.get('cloud_fallback_enabled') and settings['backend'] == 'ollama':
            fallback_settings = dict(settings)
            fallback_settings['backend'] = settings.get('cloud_fallback_backend', 'gemini')
            fallback_settings['model_name'] = settings.get('cloud_fallback_model', fallback_settings['model_name'])
            try:
                llm = _call_backend(prompt, fallback_settings)
                result['llm_response'] = llm.get('text')
                result['fallback_used'] = f"{fallback_settings['backend']}:{fallback_settings['model_name']}"
                result['llm_error'] = None
                result['raw_usage'] = llm.get('usage')
                result['quality_validation'] = validate_response(result['llm_response'], risk, retrieved_docs)
                result['validated_output'] = bool(result['quality_validation']['structure_valid']) and not result['quality_validation']['review_flags']
            except Exception as fallback_exc:
                result['llm_error'] = f"{result['llm_error']} | Fallback falló: {fallback_exc}"
    result['elapsed_sec'] = round(time.time() - start, 2)
    usage = result.get('raw_usage') or {}
    if isinstance(usage, dict):
        duration = usage.get('eval_duration') or 0
        result['tokens_per_sec'] = round(usage.get('eval_count', 0) / (duration / 1e9), 2) if duration else None
    return result


def build_validation_script(row: pd.Series) -> str:
    cve = row.get('cve', 'N/A')
    title = row.get('title', 'Hallazgo')
    asset = row.get('asset', 'Activo')
    if 'SMB' in title.upper():
        return f'# Script de validación defensiva para {asset}\nGet-SmbServerConfiguration | Select-Object EnableSMB1Protocol, EnableSMB2Protocol\nGet-HotFix | Where-Object {{$_.HotFixID -match "KB"}} | Select-Object -First 10\nWrite-Host "Validación orientada a {cve}"'
    if 'LOG4' in title.upper():
        return f'# Script Bash de verificación para {asset}\nfind / -type f \\( -name "log4j-core*.jar" -o -name "log4j*.jar" \\) 2>/dev/null\necho "Validación orientada a {cve}"'
    return f'# Script genérico de verificación para {asset}\necho "Activo: {asset}"\necho "Hallazgo: {title}"\necho "CVE: {cve}"\necho "Validar versión instalada, puertos expuestos y estado de parche."'


def evaluation_metrics(df: pd.DataFrame, history: list[dict]) -> pd.DataFrame:
    # Módulo V8: métricas LLM Enterprise con fórmulas reales y soporte para datos etiquetados.
    from .llm_metrics import evaluation_metrics as _enterprise_evaluation_metrics
    return _enterprise_evaluation_metrics(df, history)


def risk_matrix(df: pd.DataFrame) -> pd.DataFrame:
    work = evaluate_dataframe(df)
    work['impact'] = work['risk_band_v1332']
    # Axis values are explicit indicators, not invented values for missing inputs.
    work['likelihood'] = pd.to_numeric(work.get('epss'), errors='coerce') * 100
    work['impact_score'] = pd.to_numeric(work.get('cvss'), errors='coerce') * 10
    return work


def executive_report_text(df: pd.DataFrame, settings: dict) -> str:
    work = risk_matrix(df)
    total = len(work)
    critical = int((work['severity'] == 'Critical').sum())
    high = int((work['severity'] == 'High').sum())
    top = work.sort_values('priority_score', ascending=False).head(3)
    lines = [f"Informe ejecutivo - {settings.get('organization', 'EMCALI EICE ESP')}", f"Backend LLM configurado: {settings.get('backend', 'mock')} / {settings.get('model_name', 'phi3:mini')}", f"Hallazgos analizados: {total}", f"Críticos: {critical} | Altos: {high}", 'Top prioridades:']
    for _, row in top.iterrows():
        lines.append(f"- {row['finding_id']} | {row['asset']} | {row['title']} | Score {row['priority_score']} | Impacto {row['impact']}")
    lines.append('Recomendación gerencial: operar con backend local para privacidad y activar fallback cloud controlado para consultas complejas o equipos sin GPU.')
    return '\n'.join(lines)
