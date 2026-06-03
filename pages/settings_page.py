# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path

import requests
import streamlit as st

try:
    import psutil
except Exception:
    psutil = None

CONFIG_PATH = Path(__file__).resolve().parents[1] / ".emcali_llm_config.json"

DEFAULT_CONFIG = {
    "organization": "EMCALI EICE ESP",
    "deployment_mode": "OnPremise / Local",
    "backend": "ollama",
    "model_name": "phi3:mini",
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_timeout": 900,
    "ollama_num_predict": 256,
    "ollama_num_ctx": 2048,
    "temperature": 0.1,
    "top_k_rag": 3,
    "enable_cache": True,
    "enable_async_queue": True,
    "enable_streaming": False,
    "fallback_local": True,
    "fallback_gemini": False,
    "fallback_openai": False,
    "gemini_model": "gemini-1.5-flash",
    "openai_model": "gpt-4o-mini",
    "gemini_api_key": "",
    "openai_api_key": ""
}


def load_llm_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except Exception:
            pass
    # compatibilidad con session_state anterior
    old = st.session_state.get("settings")
    if isinstance(old, dict):
        cfg.update({k: v for k, v in old.items() if k in cfg})
    return cfg


def save_llm_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    st.session_state["settings"] = cfg.copy()


def get_ollama_models(base_url: str = "http://127.0.0.1:11434") -> list[str]:
    models: list[str] = []
    # 1) API Ollama
    try:
        response = requests.get(base_url.rstrip("/") + "/api/tags", timeout=5)
        if response.ok:
            for item in response.json().get("models", []):
                name = item.get("name")
                if name:
                    models.append(name)
    except Exception:
        pass
    # 2) CLI Ollama
    if not models:
        try:
            result = subprocess.check_output(["ollama", "list"], stderr=subprocess.STDOUT, timeout=8, text=True)
            for line in result.splitlines()[1:]:
                parts = line.split()
                if parts:
                    models.append(parts[0])
        except Exception:
            pass
    defaults = ["phi3:mini", "tinyllama", "gemma:2b", "mistral:7b", "llama3.1:8b"]
    for model in defaults:
        if model not in models:
            models.append(model)
    return models


def ollama_health(base_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(base_url.rstrip("/") + "/api/tags", timeout=5)
        if response.ok:
            return True, "Ollama activo y respondiendo en /api/tags."
        return False, f"Ollama responde con HTTP {response.status_code}."
    except Exception as exc:
        return False, f"Ollama no responde: {exc}"


def gpu_info() -> str:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
            stderr=subprocess.STDOUT,
            timeout=4,
            text=True,
        )
        rows = [x.strip() for x in out.splitlines() if x.strip()]
        return " | ".join(rows) if rows else "GPU NVIDIA no detectada."
    except Exception:
        return "GPU NVIDIA no detectada o nvidia-smi no disponible."


def render(*args, **kwargs):
    st.title("Configuración")
    st.caption("Centro de configuración LLM para EMCALI Cyber 2.0 Híbrido: OnPremise, nube, fallback, rendimiento y monitoreo.")

    cfg = load_llm_config()

    with st.form("llm_enterprise_settings_form"):
        st.subheader("1. Plataforma y backend")
        cfg["organization"] = st.text_input("Organización", value=str(cfg.get("organization", "EMCALI EICE ESP")))
        cfg["deployment_mode"] = st.selectbox(
            "Tipo de despliegue",
            ["OnPremise / Local", "Nube", "Híbrido", "Offline heurístico"],
            index=["OnPremise / Local", "Nube", "Híbrido", "Offline heurístico"].index(cfg.get("deployment_mode", "OnPremise / Local"))
            if cfg.get("deployment_mode", "OnPremise / Local") in ["OnPremise / Local", "Nube", "Híbrido", "Offline heurístico"] else 0,
        )
        cfg["backend"] = st.selectbox(
            "Backend LLM principal",
            ["ollama", "gemini", "openai", "offline"],
            index=["ollama", "gemini", "openai", "offline"].index(cfg.get("backend", "ollama"))
            if cfg.get("backend", "ollama") in ["ollama", "gemini", "openai", "offline"] else 0,
        )

        st.subheader("2. Ollama local / OnPremise")
        cfg["ollama_base_url"] = st.text_input("URL Ollama", value=str(cfg.get("ollama_base_url", "http://127.0.0.1:11434")))
        models = get_ollama_models(cfg["ollama_base_url"])
        current_model = str(cfg.get("model_name", "phi3:mini"))
        if current_model not in models:
            models.insert(0, current_model)
        cfg["model_name"] = st.selectbox("Modelo Ollama activo", models, index=models.index(current_model))

        col1, col2, col3 = st.columns(3)
        with col1:
            cfg["ollama_timeout"] = st.number_input("Timeout Ollama (segundos)", 30, 1800, int(cfg.get("ollama_timeout", 900)), step=30)
        with col2:
            cfg["ollama_num_predict"] = st.number_input("Máximo tokens respuesta", 32, 2048, int(cfg.get("ollama_num_predict", 256)), step=32)
        with col3:
            cfg["ollama_num_ctx"] = st.number_input("Contexto num_ctx", 512, 8192, int(cfg.get("ollama_num_ctx", 2048)), step=512)

        col4, col5 = st.columns(2)
        with col4:
            cfg["temperature"] = st.slider("Temperatura", 0.0, 1.0, float(cfg.get("temperature", 0.1)), 0.05)
        with col5:
            cfg["top_k_rag"] = st.slider("Top K RAG", 1, 10, int(cfg.get("top_k_rag", 3)))

        st.subheader("3. Nube y fallback")
        col6, col7, col8 = st.columns(3)
        with col6:
            cfg["fallback_local"] = st.checkbox("Fallback local/offline", value=bool(cfg.get("fallback_local", True)))
        with col7:
            cfg["fallback_gemini"] = st.checkbox("Fallback Gemini", value=bool(cfg.get("fallback_gemini", False)))
        with col8:
            cfg["fallback_openai"] = st.checkbox("Fallback OpenAI", value=bool(cfg.get("fallback_openai", False)))

        cfg["gemini_model"] = st.selectbox(
            "Modelo Gemini",
            ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"],
            index=0 if cfg.get("gemini_model", "gemini-1.5-flash") not in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"] else ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"].index(cfg.get("gemini_model", "gemini-1.5-flash")),
        )
        cfg["openai_model"] = st.selectbox(
            "Modelo OpenAI",
            ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4o"],
            index=0 if cfg.get("openai_model", "gpt-4o-mini") not in ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4o"] else ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4o"].index(cfg.get("openai_model", "gpt-4o-mini")),
        )
        cfg["gemini_api_key"] = st.text_input("Gemini API Key", value=str(cfg.get("gemini_api_key", "")), type="password")
        cfg["openai_api_key"] = st.text_input("OpenAI API Key", value=str(cfg.get("openai_api_key", "")), type="password")

        st.subheader("4. Ejecución y rendimiento")
        col9, col10, col11 = st.columns(3)
        with col9:
            cfg["enable_cache"] = st.checkbox("Cache de inferencia", value=bool(cfg.get("enable_cache", True)))
        with col10:
            cfg["enable_async_queue"] = st.checkbox("Cola async", value=bool(cfg.get("enable_async_queue", True)))
        with col11:
            cfg["enable_streaming"] = st.checkbox("Streaming de respuesta", value=bool(cfg.get("enable_streaming", False)))

        saved = st.form_submit_button("Guardar configuración", type="primary")

    if saved:
        save_llm_config(cfg)
        st.success("Configuración guardada correctamente. Reinicia Streamlit si algún módulo ya estaba cargado en memoria.")

    st.subheader("5. Healthcheck y monitoreo")
    ok, msg = ollama_health(str(cfg.get("ollama_base_url", "http://127.0.0.1:11434")))
    if ok:
        st.success(msg)
    else:
        st.warning(msg)

    c1, c2 = st.columns(2)
    with c1:
        if psutil:
            mem = psutil.virtual_memory()
            st.metric("RAM usada", f"{mem.percent:.1f}%")
            st.caption(f"Disponible: {mem.available / (1024**3):.2f} GB de {mem.total / (1024**3):.2f} GB")
        else:
            st.info("psutil no está instalado; no se puede medir RAM desde la app.")
    with c2:
        st.metric("GPU", gpu_info())

    st.subheader("6. Resumen activo")
    st.json({k: ("***" if "api_key" in k and v else v) for k, v in cfg.items()})
    return cfg
