from __future__ import annotations
import streamlit as st
from core.analysis import analyze_finding, search_knowledge_base


def render():
    st.title('Análisis LLM de vulnerabilidades')
    df = st.session_state.findings_df.copy()
    settings = st.session_state.settings
    if df.empty:
        st.warning('No hay hallazgos cargados. Utiliza primero el módulo Ingesta.')
        return
    st.info(f"Backend activo: {settings['backend']} | Modelo activo: {settings['model_name']} | URL/endpoint: {settings.get('ollama_base_url', 'cloud')}")
    selected_id = st.selectbox('Seleccione hallazgo', df['finding_id'].tolist())
    row = df[df['finding_id'] == selected_id].iloc[0]
    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.subheader('Detalle técnico')
        st.json(row.to_dict())
    with c2:
        st.subheader('Consulta aumentada por RAG')
        query = st.text_area('Consulta de análisis', value=settings.get('default_user_prompt', 'Analiza este hallazgo, prioriza el riesgo, explica impacto de negocio y propone remediación defensiva.'), height=160)
        docs = search_knowledge_base(st.session_state.knowledge_base, query, top_k=settings['rag_top_k'])
        for doc in docs:
            with st.expander(f"{doc['title']} (score {doc['score']})"):
                st.write(doc['content'])
    if st.button('Ejecutar análisis'):
        docs = search_knowledge_base(st.session_state.knowledge_base, query, top_k=settings['rag_top_k'])
        result = analyze_finding(row=row, retrieved_docs=docs, settings=settings, user_query=query)
        st.session_state.analysis_history.append({'finding_id': selected_id, **result})
        st.success('Análisis generado correctamente.')
        st.write(result['executive_summary'])
        st.metric('Priority Score', result['priority_score'], result['business_impact'])
        st.write('**Evidencia recuperada:**', result['retrieved_evidence'])
        for action in result['recommended_actions']:
            st.write(f'- {action}')
        if result.get('fallback_used'):
            st.warning(f"Se activó fallback cloud controlado: {result['fallback_used']}")
        if result.get('external_context'):
            with st.expander('Contexto externo NVD'):
                st.json(result['external_context'])
        if result.get('llm_response'):
            st.subheader('Respuesta del backend LLM')
            st.write(result['llm_response'])
        if result.get('llm_error'):
            st.error(result['llm_error'])
        with st.expander('Ver JSON completo del análisis'):
            st.json(result)
