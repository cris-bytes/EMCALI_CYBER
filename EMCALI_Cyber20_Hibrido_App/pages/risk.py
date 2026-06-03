from __future__ import annotations
import plotly.express as px
import streamlit as st
from core.analysis import risk_matrix


def render():
    st.title('Riesgo')
    work = risk_matrix(st.session_state.findings_df)
    st.dataframe(work[['finding_id','asset','severity','cvss','priority_score','impact','likelihood','impact_score','business_service']], use_container_width=True)
    fig = px.scatter(work, x='likelihood', y='impact_score', color='severity', size='priority_score', hover_name='finding_id', title='Matriz de riesgo operacional')
    st.plotly_chart(fig, use_container_width=True)
