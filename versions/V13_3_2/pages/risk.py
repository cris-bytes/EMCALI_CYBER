from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from core.analysis import risk_matrix


def prepare_risk_plot(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Select only records with valid quantitative risk, without imputing missing scores."""
    plot = df.copy()
    for field in ('likelihood', 'impact_score', 'priority_score'):
        plot[field] = pd.to_numeric(plot[field], errors='coerce')
    eligible = (
        plot[['likelihood', 'impact_score', 'priority_score']].notna().all(axis=1)
        & (plot['priority_score'] > 0)
        & (plot['likelihood'] >= 0)
        & (plot['impact_score'] >= 0)
    )
    valid = plot.loc[eligible].copy()
    return valid, int((~eligible).sum())


def render():
    st.title('Riesgo')
    findings = st.session_state.get('findings_df')
    if findings is None or findings.empty:
        st.warning('No hay hallazgos cargados. Utilice primero Ingesta.')
        return
    work = risk_matrix(findings)
    st.caption('V13.3.2: score ponderado 0–100 únicamente con los seis factores completos. Los valores faltantes no se imputan.')
    columns = ['finding_id', 'asset', 'severity', 'cvss', 'priority_score', 'risk_coverage_pct', 'risk_min', 'risk_max', 'risk_missing_factors',
               'asset_criticality', 'exposure', 'operational_impact', 'cisa_kev', 'impact', 'likelihood', 'impact_score', 'business_service', 'epss', 'epss_date', 'cvss_version', 'cvss_source', 'nvd_status']
    st.dataframe(work[[c for c in columns if c in work.columns]], use_container_width=True)

    st.metric('Puntuaciones completas', f"{int(work['priority_score'].notna().sum())}/{len(work)}")
    valid, pending = prepare_risk_plot(work)
    if pending:
        st.warning(
            f'{pending} hallazgo(s) sin puntuación de riesgo cuantitativa válida: '
            'se mantienen pendientes y no se representan como riesgo bajo. Revise risk_missing_factors.'
        )
    if valid.empty:
        st.info('No hay puntuaciones cuantitativas suficientes para construir la matriz de riesgo.')
        return
    fig = px.scatter(
        valid,
        x='likelihood', y='impact_score', color='severity',
        size='priority_score', hover_name='finding_id',
        title='Matriz experimental: EPSS (%) frente a CVSS (0–100), tamaño = riesgo ponderado'
    )
    st.plotly_chart(fig, use_container_width=True)
