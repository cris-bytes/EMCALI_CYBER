# EMCALI Cyber V13.3.2 — Motor de riesgo experimental

Copia independiente de V13.3.1. No modifica V12.

## Fórmula (0–100)
R = 0.25 × (CVSS × 10) + 0.20 × (EPSS × 100) + 0.20 × KEV + 0.15 × criticidad + 0.10 × exposición + 0.10 × impacto.

KEV: sí=100, no=0, desconocido=pendiente. Criticidad/impacto: Low=25, Medium=50, High=75, Critical=100. Exposición: Isolated=0, Internal/LAN=25, DMZ=75, Internet/Public=100. Son escalas **propuestas**, no calibradas ni aprobadas por EMCALI.

**Sin imputación**: si falta cualquier factor, `priority_score` queda vacío; se muestran cobertura e intervalo mínimo–máximo. Una etiqueta de riesgo no sustituye un BIA. Las fuentes oficiales de CVSS/EPSS se toman del archivo enriquecido importado; este paquete no vuelve a verificarlas en línea.

## Prueba
1. Extraer el ZIP en carpeta nueva; verificar que `models/cybersecurity` sea carpeta (no archivo).
2. Ejecutar `python -m streamlit run app.py` desde la raíz.
3. En Ingesta cargar `01_Smoke_KEV_50.xlsx`; después importar `hallazgos_50_enriquecidos.xlsx` y aplicar.
4. Ir a Riesgo. Deben aparecer `risk_coverage_pct`, `risk_min`, `risk_max` y `risk_missing_factors`.
5. Cambiar de módulos y volver a Riesgo: no debe perderse el enriquecimiento al volver a Ingesta.

Nota: valores `priority_score` en informes y LLM cambian a esta escala experimental; se requiere regresión funcional integral en HP Victus y validación de políticas empresariales antes de despliegue.
