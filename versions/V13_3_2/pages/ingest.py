from __future__ import annotations
import streamlit as st
import pandas as pd
import hashlib
from pathlib import Path
from core.enrichment_bridge import integrate_enriched_file, summarize_provenance
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
        if uploaded is not None and st.session_state.get('v1332_uploaded_sha') != hashlib.sha256(uploaded.getvalue()).hexdigest():
            try:
                normalized = normalize_uploaded_file(uploaded)
                st.session_state.findings_df = normalized
                st.session_state['v1332_uploaded_sha'] = hashlib.sha256(uploaded.getvalue()).hexdigest()
                st.session_state.pop('enrichment_summary_v1331', None)
                st.success(f'Archivo normalizado: {len(normalized)} registros.')
                if 'data_quality_flags' in normalized.columns:
                    st.warning(f"Registros con advertencias de calidad: {int(normalized['data_quality_flags'].astype(bool).sum())}. CVSS/EPSS ausentes se conservan como desconocidos.")
                detected = normalized.attrs.get('detected_format', 'Formato genérico')
                st.info(f'Se detectó el formato: {detected}')
                notes = normalized.attrs.get('normalization_notes', [])
                for note in notes:
                    st.caption(f'• {note}')
            except Exception as exc:
                st.session_state.findings_df = st.session_state.findings_df.iloc[0:0].copy()
                st.error(f'No fue posible normalizar el archivo: {exc}. Se retiraron los datos previos para evitar confusión.')
        st.divider()
        st.subheader('NVD + FIRST EPSS')
        st.caption('Importe el Excel generado por core.probar_enriquecimiento. No se realizan consultas externas al importar.')
        enriched_upload = st.file_uploader('Excel enriquecido', type=['xlsx', 'csv'], key='enriched_upload_v1331')
        if enriched_upload is not None and st.button('Aplicar enriquecimiento a los hallazgos', key='apply_enrichment_v1331'):
            try:
                if enriched_upload.name.lower().endswith('.csv'):
                    enriched_data = pd.read_csv(enriched_upload)
                else:
                    enriched_data = pd.read_excel(enriched_upload)
                base = st.session_state.findings_df
                updated, summary = integrate_enriched_file(base, enriched_data)
                st.session_state.findings_df = updated
                st.session_state['enrichment_summary_v1331'] = summary
                st.success(f"Integrados {summary['matched']} hallazgos de {len(base)}. CVSS verificados: {summary['cvss_verified']}; EPSS verificados: {summary['epss_verified']}.")
                if summary['unmatched']:
                    st.warning(f"{summary['unmatched']} hallazgos no encontraron CVE en el archivo enriquecido.")
            except Exception as exc:
                st.error(f'No se aplicó el enriquecimiento: {exc}')
        if st.session_state.get('enrichment_summary_v1331'):
            st.json(st.session_state['enrichment_summary_v1331'])
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
