from __future__ import annotations
from pathlib import Path
import streamlit as st
from core.ui import apply_theme
from core.state import init_session_state
from pages import analyze, dashboard, ingest, metrics_eval, rag, remediate, reports, risk, settings_page, acceleration

PAGES = {
    'dashboard': ('📊 Tablero', dashboard.render),
    'ingest': ('📥 Ingesta', ingest.render),
    'analyze': ('🧠 Análisis LLM', analyze.render),
    'risk': ('📈 Riesgo', risk.render),
    'remediate': ('🛠️ Remediación', remediate.render),
    'rag': ('📚 RAG Local', rag.render),
    'reports': ('📄 Informes', reports.render),
    'metrics eval': ('🧪 Métricas LLM', metrics_eval.render),
    'acceleration': ('🖥️ Aceleración IA/GPU', acceleration.render),
    'settings page': ('⚙️ Configuración', settings_page.render),
}


def main():
    apply_theme()
    init_session_state()
    logo_path = Path(__file__).resolve().parent / 'assets' / 'logo_emcali.jfif'
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)
    st.sidebar.markdown('## Navegación')
    selected_key = st.sidebar.radio('Seleccione módulo', list(PAGES.keys()), format_func=lambda k: PAGES[k][0], index=0)
    st.sidebar.markdown('---')
    st.sidebar.caption('EMCALI Cyber 2.0 · Proyecto IA aplicada a Ciberseguridad')
    st.sidebar.write(f"Backend: {st.session_state.settings['backend']}")
    st.sidebar.write(f"Modelo: {st.session_state.settings['model_name']}")
    PAGES[selected_key][1]()


if __name__ == '__main__':
    main()
