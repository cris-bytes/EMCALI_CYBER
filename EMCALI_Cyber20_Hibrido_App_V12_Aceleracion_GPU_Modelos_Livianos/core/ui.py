from __future__ import annotations
from pathlib import Path
import base64
import streamlit as st


def apply_theme() -> None:
    st.set_page_config(page_title='EMCALI Cyber 2.0 Híbrido', page_icon='🛡️', layout='wide', initial_sidebar_state='expanded')
    st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    .hero {background: linear-gradient(90deg, #007d4f, #0b5c8e); color: white; padding: 2rem 1.5rem; border-radius: 24px; margin-bottom: 1rem; box-shadow: 0 10px 24px rgba(0,0,0,.12);}
    .pill {display:inline-block; padding:.35rem .8rem; border-radius:999px; margin-right:.4rem; margin-top:.35rem; border:1px solid rgba(255,255,255,.35); background: rgba(255,255,255,.08);}
    .section-card {border: 1px solid #d8ddcf; border-radius: 18px; padding: 1rem 1.1rem; background: #fbfcf8;}
    .pipeline {display:flex; gap:.7rem; align-items:center; flex-wrap:wrap;}
    .step {padding:.7rem 1rem; border-radius:14px; border:2px solid #c5d3f0; background:#fff; font-weight:600;}
    .arrow {font-size:1.5rem; color:#455a64;}
    .smallnote {font-size:.92rem; color:#445;}
    </style>
    """, unsafe_allow_html=True)


def get_logo_data_uri() -> str:
    logo_path = Path(__file__).resolve().parents[1] / 'assets' / 'logo_emcali.jfif'
    if not logo_path.exists():
        return ''
    encoded = base64.b64encode(logo_path.read_bytes()).decode('utf-8')
    return f'data:image/jpeg;base64,{encoded}'


def hero(settings: dict) -> None:
    logo_uri = get_logo_data_uri()
    logo_html = f'<img src="{logo_uri}" alt="Logo EMCALI" style="height:92px; width:auto; background:white; padding:8px; border-radius:16px; box-shadow:0 6px 16px rgba(0,0,0,.18);">' if logo_uri else ''
    st.markdown(f"""
    <div class="hero" style="display:flex; justify-content:space-between; align-items:center; gap:1.5rem;">
        <div style="flex:1; min-width:0;">
            <h1 style="margin:0;">EMCALI Cyber 2.0 Híbrido</h1>
            <p style="margin:.8rem 0 0 0; font-size:1.02rem;">Agente consultor para gestión defensiva de vulnerabilidades con backend local y cloud controlado.</p>
            <div>
                <span class="pill">Backend activo: {settings.get('backend')}</span>
                <span class="pill">Modelo: {settings.get('model_name')}</span>
                <span class="pill">RAG Top-K: {settings.get('rag_top_k')}</span>
                <span class="pill">Internet enrichment: {'Sí' if settings.get('internet_enrichment') else 'No'}</span>
            </div>
        </div>
        <div style="display:flex; align-items:center; justify-content:center; min-width:130px;">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)


def architecture_pipeline() -> None:
    st.markdown("""
    <div class="section-card">
        <h3 style="margin-top:0;">Pipeline híbrido propuesto</h3>
        <div class="pipeline">
            <div class="step" style="border-color:#4c8bf5;">Qualys / Tenable / CSV</div>
            <div class="arrow">→</div>
            <div class="step" style="border-color:#ff9f43;">Normalizador JSON</div>
            <div class="arrow">→</div>
            <div class="step" style="border-color:#9b59b6;">RAG local + NVD opcional</div>
            <div class="arrow">→</div>
            <div class="step" style="border-color:#27ae60;">Ollama local o Cloud API</div>
            <div class="arrow">→</div>
            <div class="step" style="border-color:#5b6b82;">Reporte validado</div>
        </div>
        <p class="smallnote">El backend cloud solo se usa cuando el analista lo configura o como fallback controlado.</p>
    </div>
    """, unsafe_allow_html=True)


def image_if_exists(path: Path, caption: str) -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
