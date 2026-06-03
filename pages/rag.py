from __future__ import annotations
import streamlit as st
from core.analysis import search_knowledge_base
from core.enrichment import query_nvd_cve


def render():
    st.title('RAG local y enriquecimiento externo')
    query = st.text_input('Consulta', value='priorización de vulnerabilidades críticas')
    top_k = st.slider('Top-K', 1, 5, st.session_state.settings['rag_top_k'])
    docs = search_knowledge_base(st.session_state.knowledge_base, query, top_k=top_k)
    for doc in docs:
        with st.expander(f"{doc['title']} | {doc['category']} | score {doc['score']}"):
            st.write(doc['content'])
    st.subheader('Consulta puntual a NVD por CVE')
    cve = st.text_input('CVE', value='CVE-2020-0796')
    if st.button('Consultar NVD'):
        result = query_nvd_cve(cve)
        if result:
            st.json(result)
        else:
            st.warning('No se obtuvo información externa para ese CVE.')
