from __future__ import annotations
from pathlib import Path
import plotly.express as px
import streamlit as st
from core.ui import hero, architecture_pipeline, image_if_exists


def render():
    settings = st.session_state.settings
    df = st.session_state.findings_df.copy()
    hero(settings)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Hallazgos', len(df), 'Fuente demo/cargada')
    c2.metric('Críticas', int((df['severity'] == 'Critical').sum()), 'Atención 0-24h')
    c3.metric('Altas', int((df['severity'] == 'High').sum()), 'Atención 2-7 días')
    c4.metric('Backend', settings['backend'], settings['model_name'])
    st.subheader('Arquitectura EMCALI Cyber 2.0 Híbrido')
    architecture_pipeline()
    sev = df.groupby('severity', as_index=False).size()
    svc = df.groupby('business_service', as_index=False).size().sort_values('size', ascending=False)
    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(px.pie(sev, names='severity', values='size', title='Vulnerabilidades por severidad'), use_container_width=True)
    with c6:
        st.plotly_chart(px.bar(svc, x='business_service', y='size', title='Activos / servicios impactados'), use_container_width=True)
    base = Path(__file__).resolve().parents[1] / 'assets'
    tabs = st.tabs(['Modelo híbrido', 'Despliegue', 'Pantalla actual'])
    with tabs[0]:
        image_if_exists(base / 'modelo_unico_foundation_sec_8b.png', 'Diagrama del modelo local / híbrido')
    with tabs[1]:
        image_if_exists(base / 'arquitectura_despliegue_local.png', 'Arquitectura de despliegue local')
    with tabs[2]:
        image_if_exists(base / 'pantalla_actual.png', 'Vista de referencia de la aplicación')
