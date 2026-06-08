# EMCALI Cyber 2.0 Híbrido V8 - Métricas LLM Enterprise

Este paquete integra un nuevo módulo de Métricas LLM Enterprise.

## Archivos modificados

- `core/llm_metrics.py`: motor de cálculo de métricas.
- `pages/metrics_eval.py`: interfaz Streamlit del módulo Métricas LLM.
- `core/analysis.py`: wrapper de compatibilidad para `evaluation_metrics`.

## Métricas implementadas

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 Score = 2 * Precision * Recall / (Precision + Recall)
- Hallucination Rate = respuestas no confiables / respuestas totales
- Pass@1 = respuestas válidas al primer intento / consultas totales
- Latencia promedio = sum(latencia_i) / N
- Latencia P95 = percentil 95 de las latencias
- Fallback Rate = consultas con fallback / consultas totales
- Attack Success Rate = ataques exitosos / pruebas adversariales
- CVE Accuracy = CVE interpretados correctamente / CVE analizados
- MITRE ATT&CK Accuracy = técnicas correctas / técnicas evaluadas
- Remediation Accuracy = remediaciones correctas / remediaciones evaluadas
- EPSS Correlation = correlación Spearman entre EPSS y prioridad
- KEV Detection Rate = KEV detectadas / KEV presentes
- Tokens de entrada/salida
- Costo estimado
- Recursos CPU/RAM/GPU cuando existan columnas de monitoreo

## Nota técnica

Cuando el dataset no trae columnas etiquetadas, el módulo no inventa métricas exactas: marca la fuente como ESTIMADO, SIN DATOS o SIN COLUMNA DE VALIDACIÓN. Para métricas completamente reales se recomienda cargar columnas como:

- `ground_truth_label`, `predicted_label`
- `is_hallucination`
- `cve_correct`
- `mitre_correct`
- `remediation_correct`
- `epss_score`, `priority_score`
- `kev_present`, `kev_detected`
- `input_tokens`, `output_tokens`, `cost_usd`
- `cpu_pct`, `ram_pct`, `gpu_pct`
