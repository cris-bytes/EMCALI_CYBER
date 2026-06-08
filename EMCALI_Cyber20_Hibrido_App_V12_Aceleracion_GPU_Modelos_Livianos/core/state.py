from __future__ import annotations
import streamlit as st
from dotenv import load_dotenv
from .sample_data import sample_findings_df, sample_knowledge_base

load_dotenv()


def init_session_state() -> None:
    if 'findings_df' not in st.session_state:
        st.session_state.findings_df = sample_findings_df()
    if 'knowledge_base' not in st.session_state:
        st.session_state.knowledge_base = sample_knowledge_base()
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []
    if 'reports_history' not in st.session_state:
        st.session_state.reports_history = []
    if 'settings' not in st.session_state:
        st.session_state.settings = {
            'organization': 'EMCALI EICE ESP',
            'backend': 'ollama',
            'model_name': 'phi3:mini',
            'ollama_base_url': 'http://127.0.0.1:11434',
            'ollama_timeout_sec': 600,
            'rag_top_k': 1,
            'critical_sla_hours': 24,
            'high_sla_days': 7,
            'theme': 'EMCALI Cyber 2.0 Híbrido',
            'system_prompt_template': 'Eres un analista senior de ciberseguridad de EMCALI Cyber 2.0. Responde en español técnico claro, prioriza riesgo, impacto de negocio, acciones defensivas y validaciones posteriores.',
            'default_user_prompt': 'Analiza este hallazgo, prioriza el riesgo, explica impacto de negocio y propone remediación defensiva.',
            'internet_enrichment': True,
            'cloud_fallback_enabled': True,
            'cloud_fallback_backend': 'gemini',
            'cloud_fallback_model': 'gemini-2.5-flash-lite',
            'openai_model': 'gpt-4.1-mini',
            'anthropic_model': 'claude-sonnet-4-6',
            'anthropic_api_key': '',
            'gemini_model': 'gemini-2.5-flash-lite',
        }
