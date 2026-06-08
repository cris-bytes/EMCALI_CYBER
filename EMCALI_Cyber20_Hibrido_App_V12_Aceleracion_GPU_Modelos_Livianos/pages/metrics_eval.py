from __future__ import annotations

import plotly.express as px
import streamlit as st
from core.llm_metrics import calculate_llm_metrics


def render():
    st.title('Métricas LLM Enterprise')
    st.caption('Evaluación técnica del agente LLM: calidad, confiabilidad, rendimiento, ciberseguridad, fallback, consumo y costo.')

    results = calculate_llm_metrics(
        st.session_state.findings_df,
        st.session_state.analysis_history,
        st.session_state.get('settings', {}),
    )
    metrics = results['metrics']
    perf = results['backend_performance']
    resources = results['resources']
    hist = results['history']

    if hist.empty:
        st.warning('Aún no hay historial de análisis LLM. Ejecute primero el módulo Análisis LLM para generar métricas reales de latencia, fallback y respuesta.')

    st.subheader('1. Indicadores principales')
    c1, c2, c3, c4 = st.columns(4)
    def val(name: str):
        row = metrics[metrics['metrica'] == name]
        return row.iloc[0]['valor'] if not row.empty else 0
    c1.metric('Precision', f"{val('Precision')}%")
    c2.metric('Recall', f"{val('Recall')}%")
    c3.metric('F1 Score', f"{val('F1 Score')}%")
    c4.metric('Fallback Rate', f"{val('Fallback Rate')}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric('Hallucination Rate', f"{val('Hallucination Rate')}%")
    c6.metric('Pass@1', f"{val('Pass@1')}%")
    c7.metric('Latencia promedio', f"{val('Latencia promedio')} s")
    c8.metric('Costo estimado', f"US$ {val('Costo estimado')}")

    st.subheader('2. Tabla completa con fórmula, numerador y denominador')
    st.dataframe(metrics, use_container_width=True, hide_index=True)

    st.subheader('3. Gráfica de métricas porcentuales')
    pct = metrics[metrics['unidad'] == '%'].copy()
    if not pct.empty:
        st.plotly_chart(
            px.bar(pct, x='metrica', y='valor', color='categoria', text='valor', title='Métricas LLM en porcentaje'),
            use_container_width=True,
        )

    st.subheader('4. Rendimiento por backend')
    if perf.empty:
        st.info('No hay datos suficientes por backend. Ejecute consultas con Ollama, Anthropic, Gemini u OpenAI.')
    else:
        st.dataframe(perf, use_container_width=True, hide_index=True)
        st.plotly_chart(px.bar(perf, x='backend_used', y='latencia_promedio_s', text='latencia_promedio_s', title='Latencia promedio por backend'), use_container_width=True)

    st.subheader('5. Recursos CPU/RAM/GPU')
    if resources.empty:
        st.info('No hay datos de CPU/RAM/GPU en el historial. Para activarlo, registre cpu_pct, ram_pct y gpu_pct en cada ejecución del LLM.')
    else:
        st.dataframe(resources, use_container_width=True, hide_index=True)

    st.subheader('6. Interpretación técnica')
    st.markdown('''
- **Precision** mide cuántos hallazgos marcados como vulnerabilidad por el LLM realmente lo son.
- **Recall** mide cuántas vulnerabilidades existentes fueron detectadas por el LLM.
- **F1 Score** resume Precision y Recall en una sola medida balanceada.
- **Hallucination Rate** mide respuestas inventadas, no verificables o no confiables.
- **Pass@1** mide si el LLM respondió correctamente al primer intento.
- **Fallback Rate** mide cuántas consultas tuvieron que pasar de backend local a nube.
- **CVE Accuracy, MITRE Accuracy y Remediation Accuracy** requieren columnas de validación o revisión del analista para ser completamente reales.
- **EPSS Correlation y KEV Detection Rate** se activan cuando los datos cargados incluyen EPSS y CISA KEV.
''')

    with st.expander('Ver historial bruto de análisis LLM'):
        if hist.empty:
            st.write('Sin historial.')
        else:
            st.dataframe(hist, use_container_width=True)
