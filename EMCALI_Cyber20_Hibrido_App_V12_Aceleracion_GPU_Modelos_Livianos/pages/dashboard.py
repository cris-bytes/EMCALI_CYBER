from __future__ import annotations
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from core.ui import hero, architecture_pipeline, image_if_exists

SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low', 'Info', 'Unknown']
SEVERITY_ALIASES = {
    'critical': 'Critical', 'critica': 'Critical', 'crítica': 'Critical', 'critico': 'Critical', 'crítico': 'Critical',
    'high': 'High', 'alta': 'High', 'alto': 'High',
    'medium': 'Medium', 'media': 'Medium', 'medio': 'Medium',
    'low': 'Low', 'baja': 'Low', 'bajo': 'Low',
    'info': 'Info', 'informational': 'Info', 'informativa': 'Info'
}


def _normalize_severity(value: object) -> str:
    if pd.isna(value):
        return 'Unknown'
    raw = str(value).strip()
    return SEVERITY_ALIASES.get(raw.lower(), raw.title() if raw else 'Unknown')


def _dashboard_dataset() -> pd.DataFrame:
    """Devuelve siempre el dataset activo de la consulta/ingesta más reciente."""
    df = st.session_state.get('findings_df', pd.DataFrame()).copy()
    if df is None or df.empty:
        return pd.DataFrame()

    if 'severity' not in df.columns:
        df['severity'] = 'Unknown'
    df['severity_norm'] = df['severity'].apply(_normalize_severity)

    if 'business_service' in df.columns:
        df['impact_target'] = df['business_service'].fillna('').astype(str).str.strip()
    elif 'asset' in df.columns:
        df['impact_target'] = df['asset'].fillna('').astype(str).str.strip()
    elif 'ip' in df.columns:
        df['impact_target'] = df['ip'].fillna('').astype(str).str.strip()
    else:
        df['impact_target'] = 'Sin servicio/activo'

    if 'asset' in df.columns:
        df['asset_label'] = df['asset'].fillna('').astype(str).str.strip()
    elif 'ip' in df.columns:
        df['asset_label'] = df['ip'].fillna('').astype(str).str.strip()
    else:
        df['asset_label'] = df['impact_target']

    df.loc[df['impact_target'] == '', 'impact_target'] = 'Sin servicio/activo'
    df.loc[df['asset_label'] == '', 'asset_label'] = df['impact_target']
    return df


def _severity_chart(df: pd.DataFrame):
    sev = (
        df.groupby('severity_norm', dropna=False)
        .size()
        .reindex(SEVERITY_ORDER, fill_value=0)
        .reset_index(name='hallazgos')
        .rename(columns={'severity_norm': 'severidad'})
    )
    sev = sev[sev['hallazgos'] > 0]
    if sev.empty:
        st.info('No hay datos de severidad para graficar.')
        return
    fig = px.pie(
        sev,
        names='severidad',
        values='hallazgos',
        title='Vulnerabilidades por severidad',
        hole=0.35,
    )
    fig.update_traces(textposition='inside', textinfo='percent+label+value')
    fig.update_layout(legend_title_text='Severidad')
    st.plotly_chart(fig, use_container_width=True)
    st.caption('Gráfico recalculado automáticamente desde el dataset activo de la última ingesta/consulta.')


def _services_chart(df: pd.DataFrame):
    svc = (
        df.groupby('impact_target', dropna=False)
        .agg(hallazgos=('impact_target', 'size'), activos=('asset_label', pd.Series.nunique))
        .reset_index()
        .sort_values(['hallazgos', 'activos'], ascending=False)
        .head(15)
    )
    if svc.empty:
        st.info('No hay datos de activos o servicios para graficar.')
        return
    fig = px.bar(
        svc,
        x='impact_target',
        y='hallazgos',
        hover_data={'activos': True, 'impact_target': False},
        title='Activos / servicios impactados',
        labels={'impact_target': 'Servicio o activo', 'hallazgos': 'Hallazgos', 'activos': 'Activos únicos'},
    )
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)
    st.caption('La gráfica se actualiza con cada archivo cargado o consulta normalizada en la sesión.')


def render():
    settings = st.session_state.settings
    df = _dashboard_dataset()
    hero(settings)

    critical = int((df['severity_norm'] == 'Critical').sum()) if not df.empty else 0
    high = int((df['severity_norm'] == 'High').sum()) if not df.empty else 0
    source_name = df.attrs.get('detected_format', 'Fuente demo/cargada') if hasattr(df, 'attrs') else 'Fuente demo/cargada'

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Hallazgos', len(df), source_name)
    c2.metric('Críticas', critical, 'Atención 0-24h')
    c3.metric('Altas', high, 'Atención 2-7 días')
    c4.metric('Backend', settings['backend'], settings['model_name'])

    st.subheader('Arquitectura EMCALI Cyber 2.0 Híbrido')
    architecture_pipeline()

    st.subheader('Indicadores dinámicos de la consulta activa')
    st.caption('Estas gráficas ya no son estáticas: toman los datos normalizados de `st.session_state.findings_df`, es decir, el dataset demo, archivo cargado o consulta vigente.')
    c5, c6 = st.columns(2)
    with c5:
        _severity_chart(df)
    with c6:
        _services_chart(df)

    base = Path(__file__).resolve().parents[1] / 'assets'
    tabs = st.tabs(['Modelo híbrido', 'Despliegue', 'Pantalla actual'])
    with tabs[0]:
        st.markdown('**Modelo híbrido actualizado:** fuentes de vulnerabilidades, normalización, RAG, motor LLM local/cloud, validación y métricas Enterprise.')
        image_if_exists(base / 'modelo_unico_foundation_sec_8b.png', 'Modelo híbrido actualizado de EMCALI Cyber 2.0')
    with tabs[1]:
        st.markdown('**Despliegue actualizado:** estación analista, Streamlit, backend Python, Ollama local, Anthropic/Gemini/OpenAI como fallback y enriquecimiento NVD/KEV/EPSS.')
        image_if_exists(base / 'arquitectura_despliegue_local.png', 'Arquitectura de despliegue actualizada')
    with tabs[2]:
        st.markdown('**Pantalla actual:** referencia visual actualizada del tablero con logo EMCALI y layout vigente.')
        image_if_exists(base / 'pantalla_actual.png', 'Vista actualizada del tablero EMCALI Cyber 2.0')
