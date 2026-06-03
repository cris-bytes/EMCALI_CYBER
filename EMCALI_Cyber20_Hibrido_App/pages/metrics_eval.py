from __future__ import annotations
import plotly.express as px
import streamlit as st
from core.analysis import evaluation_metrics


def render():
    st.title('Métricas LLM')
    metrics = evaluation_metrics(st.session_state.findings_df, st.session_state.analysis_history)
    st.dataframe(metrics, use_container_width=True)
    st.plotly_chart(px.bar(metrics, x='metric', y='value', title='Indicadores del agente'), use_container_width=True)
