from __future__ import annotations
import streamlit as st


def render():
    st.title('Configuración')
    settings = st.session_state.settings
    org = st.text_input('Organización', value=settings['organization'])
    backend = st.selectbox('Backend LLM', ['mock', 'ollama', 'openai', 'anthropic', 'gemini'], index=['mock','ollama','openai','anthropic','gemini'].index(settings['backend']))
    model_name = st.text_input('Modelo activo', value=settings['model_name'])
    ollama_base_url = st.text_input('URL Ollama', value=settings['ollama_base_url'])
    ollama_timeout_sec = st.number_input('Timeout Ollama (segundos)', min_value=30, max_value=1800, value=int(settings['ollama_timeout_sec']), step=30)
    rag_top_k = st.slider('Top K RAG', 1, 5, int(settings['rag_top_k']))
    critical_sla = st.slider('SLA críticos (horas)', 4, 48, int(settings['critical_sla_hours']))
    high_sla = st.slider('SLA altos (días)', 1, 15, int(settings['high_sla_days']))
    system_prompt_template = st.text_area('Plantilla del sistema', value=settings.get('system_prompt_template', ''), height=180)
    default_user_prompt = st.text_area('Prompt por defecto del analista', value=settings.get('default_user_prompt', ''), height=120)
    internet_enrichment = st.checkbox('Enriquecimiento externo controlado (NVD)', value=bool(settings.get('internet_enrichment', True)))
    cloud_fallback_enabled = st.checkbox('Fallback cloud cuando el backend local no responda', value=bool(settings.get('cloud_fallback_enabled', True)))
    cloud_fallback_backend = st.selectbox('Backend fallback', ['gemini', 'openai', 'anthropic'], index=['gemini','openai','anthropic'].index(settings.get('cloud_fallback_backend', 'gemini')))
    cloud_fallback_model = st.text_input('Modelo fallback', value=settings.get('cloud_fallback_model', 'gemini-2.5-flash-lite'))
    openai_model = st.text_input('Modelo OpenAI', value=settings.get('openai_model', 'gpt-4.1-mini'))
    anthropic_model = st.text_input('Modelo Anthropic', value=settings.get('anthropic_model', 'claude-sonnet-4-0'))
    gemini_model = st.text_input('Modelo Gemini', value=settings.get('gemini_model', 'gemini-2.5-flash-lite'))
    if st.button('Guardar configuración'):
        st.session_state.settings = {
            'organization': org,
            'backend': backend,
            'model_name': model_name,
            'ollama_base_url': ollama_base_url,
            'ollama_timeout_sec': int(ollama_timeout_sec),
            'rag_top_k': rag_top_k,
            'critical_sla_hours': critical_sla,
            'high_sla_days': high_sla,
            'theme': 'EMCALI Cyber 2.0 Híbrido',
            'system_prompt_template': system_prompt_template,
            'default_user_prompt': default_user_prompt,
            'internet_enrichment': internet_enrichment,
            'cloud_fallback_enabled': cloud_fallback_enabled,
            'cloud_fallback_backend': cloud_fallback_backend,
            'cloud_fallback_model': cloud_fallback_model,
            'openai_model': openai_model,
            'anthropic_model': anthropic_model,
            'gemini_model': gemini_model,
        }
        st.success('Configuración actualizada.')
    st.json(st.session_state.settings)
