from __future__ import annotations
import streamlit as st
from core.normalizer import normalize_uploaded_file
from core.sample_data import sample_findings_df


def render():
    st.title('Ingesta y normalización')
    st.write('Cargue datos demo o suba archivos CSV, JSON o Excel para producir un esquema uniforme para el resto de módulos.')
    st.caption('Formatos soportados: Qualys, Tenable/Nessus, Unified JSON Schema y datasets enriquecidos tipo NVD + CISA KEV + EPSS como cve_cisa_epss_enriched_dataset.csv y cve_corpus.csv.')
    c1, c2 = st.columns([0.35, 0.65])
    with c1:
        if st.button('Cargar dataset demo'):
            st.session_state.findings_df = sample_findings_df()
            st.session_state.findings_df.attrs['detected_format'] = 'Demo'
            st.session_state.findings_df.attrs['normalization_notes'] = ['Se cargó el dataset demostrativo institucional.']
            st.success('Dataset demo cargado.')

        uploaded = st.file_uploader('Subir CSV, JSON o Excel', type=['csv', 'json', 'xlsx', 'xls'])
        if uploaded is not None:
            try:
                normalized = normalize_uploaded_file(uploaded)
                st.session_state.findings_df = normalized
                st.success('Archivo normalizado correctamente.')
                detected = normalized.attrs.get('detected_format', 'Formato genérico')
                st.info(f'Se detectó el formato: {detected}')
                notes = normalized.attrs.get('normalization_notes', [])
                for note in notes:
                    st.caption(f'• {note}')
            except Exception as exc:
                st.error(f'No fue posible normalizar el archivo: {exc}')
    with c2:
        st.subheader('Hallazgos normalizados')
        st.dataframe(st.session_state.findings_df, use_container_width=True)
        if not st.session_state.findings_df.empty:
            st.subheader('Vista previa Unified Schema')
            st.json(st.session_state.findings_df.iloc[0].to_dict())
            with st.expander('Metadatos de normalización'):
                st.write('Formato detectado:', st.session_state.findings_df.attrs.get('detected_format', 'N/D'))
                st.write('Columnas originales:', st.session_state.findings_df.attrs.get('original_columns', []))
                st.write('Notas:', st.session_state.findings_df.attrs.get('normalization_notes', []))
