# -*- coding: utf-8 -*-
"""
EMCALI Cyber 2.0 Hibrido - Parche V6 Enterprise LLM
Corrige la pagina Configuracion descuadrada y agrega:
- cambio dinamico de modelo
- deteccion automatica de modelos Ollama instalados
- seleccion OnPrem / Nube / Offline
- fallback local, Gemini y OpenAI
- healthcheck Ollama
- timeout configurable
- cache de inferencia
- cola async (bandera/configuracion)
- streaming de respuesta (bandera/configuracion)
- monitoreo RAM/GPU
Ejecutar desde la raiz de la aplicacion.
"""
from __future__ import annotations
import os, shutil, datetime, textwrap, json

ROOT = os.getcwd()
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = os.path.join(ROOT, "backup_parche_v6_enterprise_" + STAMP)
CONFIG_FILE = ".emcali_llm_config.json"

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

SETTINGS_PAGE = r'''
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
'''

LLM_RUNTIME = r'''
# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".emcali_llm_config.json"
CACHE_PATH = ROOT / ".emcali_llm_cache.json"

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
    "openai_api_key": "",
}


def load_config() -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except Exception:
            pass
    # env override
    cfg["model_name"] = os.getenv("OLLAMA_MODEL", cfg["model_name"])
    cfg["ollama_base_url"] = os.getenv("OLLAMA_BASE_URL", cfg["ollama_base_url"])
    cfg["backend"] = os.getenv("LLM_BACKEND", cfg["backend"])
    try:
        cfg["ollama_timeout"] = int(os.getenv("OLLAMA_TIMEOUT", cfg["ollama_timeout"]))
    except Exception:
        pass
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def healthcheck_ollama(base_url: str | None = None) -> Tuple[bool, str]:
    cfg = load_config()
    url = (base_url or cfg["ollama_base_url"]).rstrip("/")
    try:
        r = requests.get(url + "/api/tags", timeout=5)
        if r.ok:
            return True, "Ollama OK"
        return False, f"Ollama HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)


def list_ollama_models(base_url: str | None = None) -> list[str]:
    cfg = load_config()
    url = (base_url or cfg["ollama_base_url"]).rstrip("/")
    models: list[str] = []
    try:
        r = requests.get(url + "/api/tags", timeout=5)
        if r.ok:
            for item in r.json().get("models", []):
                name = item.get("name")
                if name:
                    models.append(name)
    except Exception:
        pass
    if not models:
        try:
            out = subprocess.check_output(["ollama", "list"], text=True, timeout=8, stderr=subprocess.STDOUT)
            for line in out.splitlines()[1:]:
                if line.strip():
                    models.append(line.split()[0])
        except Exception:
            pass
    return models or ["phi3:mini", "tinyllama", "gemma:2b"]


def _cache_key(backend: str, model: str, prompt: str) -> str:
    return hashlib.sha256((backend + "|" + model + "|" + prompt).encode("utf-8", errors="ignore")).hexdigest()


def _load_cache() -> Dict[str, Any]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    try:
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def fallback_offline(prompt: str, reason: str = "") -> str:
    return (
        "Respuesta generada en modo local/offline. "
        "No fue posible obtener respuesta del LLM principal. "
        f"Detalle técnico: {reason}\n\n"
        "Recomendación: validar criticidad, priorizar por CVSS/servicio afectado, "
        "confirmar ventana de cambio, ejecutar remediación controlada y cerrar con rescaneo."
    )


def call_ollama(prompt: str, **kwargs) -> str:
    cfg = load_config()
    model = kwargs.get("model") or cfg.get("model_name", "phi3:mini")
    base_url = kwargs.get("base_url") or cfg.get("ollama_base_url", "http://127.0.0.1:11434")
    timeout = int(kwargs.get("timeout") or cfg.get("ollama_timeout", 900))
    max_prompt_chars = int(kwargs.get("max_prompt_chars", 5000))
    prompt = str(prompt or "")[:max_prompt_chars]
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": bool(cfg.get("enable_streaming", False)),
        "options": {
            "num_predict": int(cfg.get("ollama_num_predict", 256)),
            "num_ctx": int(cfg.get("ollama_num_ctx", 2048)),
            "temperature": float(cfg.get("temperature", 0.1)),
        },
    }
    r = requests.post(base_url.rstrip("/") + "/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    if payload["stream"]:
        # Para compatibilidad con llamadas existentes se devuelve texto acumulado si llega NDJSON.
        text_parts = []
        for line in r.text.splitlines():
            try:
                item = json.loads(line)
                text_parts.append(item.get("response", ""))
            except Exception:
                pass
        return "".join(text_parts) or r.text
    return r.json().get("response", "")


def call_gemini(prompt: str, **kwargs) -> str:
    cfg = load_config()
    api_key = kwargs.get("api_key") or cfg.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Gemini API Key no configurada")
    model = kwargs.get("model") or cfg.get("gemini_model", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=payload, timeout=int(cfg.get("ollama_timeout", 900)))
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0].get("text", "")


def call_openai(prompt: str, **kwargs) -> str:
    cfg = load_config()
    api_key = kwargs.get("api_key") or cfg.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OpenAI API Key no configurada")
    model = kwargs.get("model") or cfg.get("openai_model", "gpt-4o-mini")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": float(cfg.get("temperature", 0.1))}
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=int(cfg.get("ollama_timeout", 900)))
    r.raise_for_status()
    return r.json()["choices"][0]["message"].get("content", "")


def generate(prompt: str, **kwargs) -> str:
    cfg = load_config()
    backend = kwargs.get("backend") or cfg.get("backend", "ollama")
    model = kwargs.get("model") or cfg.get("model_name", "phi3:mini")
    prompt = str(prompt or "")

    key = _cache_key(backend, model, prompt)
    if cfg.get("enable_cache", True):
        cache = _load_cache()
        if key in cache:
            return cache[key].get("text", "")
    else:
        cache = {}

    errors = []
    order = []
    if backend == "ollama":
        order.append("ollama")
    elif backend == "gemini":
        order.append("gemini")
    elif backend == "openai":
        order.append("openai")
    else:
        order.append("offline")

    if cfg.get("fallback_gemini", False) and "gemini" not in order:
        order.append("gemini")
    if cfg.get("fallback_openai", False) and "openai" not in order:
        order.append("openai")
    if cfg.get("fallback_local", True) and "offline" not in order:
        order.append("offline")

    for item in order:
        try:
            if item == "ollama":
                text = call_ollama(prompt, **kwargs)
            elif item == "gemini":
                text = call_gemini(prompt, **kwargs)
            elif item == "openai":
                text = call_openai(prompt, **kwargs)
            else:
                text = fallback_offline(prompt, "; ".join(errors))
            if cfg.get("enable_cache", True):
                cache[key] = {"text": text, "backend": item, "model": model, "ts": time.time()}
                _save_cache(cache)
            return text
        except Exception as exc:
            errors.append(f"{item}: {exc}")
    return fallback_offline(prompt, "; ".join(errors))

# Alias de compatibilidad para distintos nombres usados en la app.
query_llm = generate
ask_llm = generate
generate_response = generate
analyze_with_llm = generate
query_ollama = call_ollama
'''

REQUESTS_WRAPPER = r'''
# === EMCALI_PATCH_V6_ENTERPRISE_LLM_REQUESTS_WRAPPER ===
try:
    import requests as _emcali_requests_v6
    from core.llm_runtime import load_config as _emcali_load_config_v6
    if not hasattr(_emcali_requests_v6, "_emcali_original_post_v6"):
        _emcali_requests_v6._emcali_original_post_v6 = _emcali_requests_v6.post
        def _emcali_post_v6(url, *args, **kwargs):
            try:
                cfg = _emcali_load_config_v6()
                url_s = str(url)
                if ("11434" in url_s) or ("/api/generate" in url_s) or ("/api/chat" in url_s):
                    kwargs["timeout"] = int(cfg.get("ollama_timeout", 900))
                    payload = kwargs.get("json")
                    if isinstance(payload, dict):
                        payload["stream"] = bool(cfg.get("enable_streaming", False))
                        payload["model"] = cfg.get("model_name", "phi3:mini")
                        if isinstance(payload.get("prompt"), str) and len(payload["prompt"]) > 5000:
                            payload["prompt"] = payload["prompt"][:5000] + "\n\n[Contexto recortado por EMCALI Patch V6.]"
                        options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
                        options["num_predict"] = int(cfg.get("ollama_num_predict", 256))
                        options["num_ctx"] = int(cfg.get("ollama_num_ctx", 2048))
                        options["temperature"] = float(cfg.get("temperature", 0.1))
                        payload["options"] = options
                        kwargs["json"] = payload
            except Exception:
                pass
            return _emcali_requests_v6._emcali_original_post_v6(url, *args, **kwargs)
        _emcali_requests_v6.post = _emcali_post_v6
except Exception:
    pass
# === FIN EMCALI_PATCH_V6_ENTERPRISE_LLM_REQUESTS_WRAPPER ===
'''


def backup(path: str):
    if not os.path.exists(path):
        return
    rel = os.path.relpath(path, ROOT)
    dst = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(path, dst)


def write_file(rel: str, content: str):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    backup(path)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.lstrip("\n"))


def read_text(path: str) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            pass
    return ""


def write_text(path: str, text: str):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def patch_python_files():
    marker = "EMCALI_PATCH_V6_ENTERPRISE_LLM_REQUESTS_WRAPPER"
    for rel in ["core/analysis.py", "core/llm_clients.py"]:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        text = read_text(path)
        if marker in text:
            continue
        backup(path)
        # corregir modelos pesados hardcoded
        for old in ["llama3.1:8b", "llama3:8b", "llama3.1", "llama3"]:
            text = text.replace(old, "phi3:mini")
        lines = text.splitlines(True)
        insert_at = 0
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("import ") or s.startswith("from ") or not s or s.startswith("#"):
                insert_at = i + 1
                continue
            break
        lines.insert(insert_at, "\n" + REQUESTS_WRAPPER + "\n")
        write_text(path, "".join(lines))


def ensure_config():
    path = os.path.join(ROOT, CONFIG_FILE)
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        try:
            old = json.loads(read_text(path))
            if isinstance(old, dict):
                cfg.update(old)
        except Exception:
            pass
    # Forzar estado seguro por defecto
    cfg["backend"] = cfg.get("backend") or "ollama"
    cfg["model_name"] = cfg.get("model_name") or "phi3:mini"
    cfg["ollama_timeout"] = int(cfg.get("ollama_timeout") or 900)
    backup(path)
    write_text(path, json.dumps(cfg, indent=2, ensure_ascii=False))


def ensure_env():
    path = os.path.join(ROOT, ".env")
    current = read_text(path) if os.path.exists(path) else ""
    backup(path)
    items = {
        "LLM_BACKEND": "ollama",
        "OLLAMA_MODEL": "phi3:mini",
        "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "OLLAMA_TIMEOUT": "900",
    }
    for k, v in items.items():
        found = False
        lines = []
        for line in current.splitlines():
            if line.startswith(k + "="):
                lines.append(k + "=" + v)
                found = True
            else:
                lines.append(line)
        current = "\n".join(lines)
        if not found:
            current = (current + "\n" if current else "") + k + "=" + v
    write_text(path, current + "\n")


def main():
    if not os.path.exists(os.path.join(ROOT, "app.py")):
        print("ERROR: ejecuta este parche desde la carpeta raiz donde esta app.py")
        raise SystemExit(1)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    write_file("pages/settings_page.py", SETTINGS_PAGE)
    write_file("core/llm_runtime.py", LLM_RUNTIME)
    patch_python_files()
    ensure_config()
    ensure_env()
    print("\n=== PARCHE V6 ENTERPRISE LLM APLICADO ===")
    print("Raiz:", ROOT)
    print("Backup:", BACKUP_DIR)
    print("Archivos clave regenerados:")
    print(" - pages/settings_page.py")
    print(" - core/llm_runtime.py")
    print(" - .emcali_llm_config.json")
    print("\nSiguiente paso:")
    print("1) Cierra Streamlit con CTRL+C")
    print("2) Ejecuta: streamlit run app.py")
    print("3) En Configuracion, selecciona plataforma/backend/modelo y guarda.")

if __name__ == "__main__":
    main()
