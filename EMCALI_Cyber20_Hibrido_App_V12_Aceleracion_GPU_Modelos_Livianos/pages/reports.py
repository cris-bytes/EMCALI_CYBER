from __future__ import annotations
import json
import streamlit as st
from core.analysis import executive_report_text, risk_matrix


def render():
    st.title('Informes')
    report_text = executive_report_text(st.session_state.findings_df, st.session_state.settings)
    risk_df = risk_matrix(st.session_state.findings_df)
    st.text_area('Resumen ejecutivo', value=report_text, height=240)
    st.download_button('Descargar resumen TXT', report_text, file_name='informe_ejecutivo_emcali_cyber20.txt')
    st.download_button('Descargar riesgo CSV', risk_df.to_csv(index=False), file_name='registro_riesgo_emcali_cyber20.csv', mime='text/csv')
    if st.session_state.analysis_history:
        history_json = json.dumps(st.session_state.analysis_history, ensure_ascii=False, default=str, indent=2)
        st.download_button('Descargar historial JSON', history_json, file_name='historial_analisis_emcali_cyber20.json')
