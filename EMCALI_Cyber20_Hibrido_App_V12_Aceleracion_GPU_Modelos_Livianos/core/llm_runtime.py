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
    "ollama_num_gpu": -1,
    "gpu_monitoring_enabled": True,
    "temperature": 0.1,
    "top_k_rag": 3,
    "enable_cache": True,
    "enable_async_queue": True,
    "enable_streaming": False,
    "fallback_local": True,
    "fallback_gemini": False,
    "fallback_openai": False,
    "fallback_anthropic": False,
    "gemini_model": "gemini-1.5-flash",
    "openai_model": "gpt-4o-mini",
    "anthropic_model": "claude-sonnet-4-6",
    "gemini_api_key": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
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
    cfg["anthropic_model"] = os.getenv("ANTHROPIC_MODEL", cfg.get("anthropic_model", "claude-sonnet-4-6"))
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
    options = {
        "num_predict": int(cfg.get("ollama_num_predict", 256)),
        "num_ctx": int(cfg.get("ollama_num_ctx", 2048)),
        "temperature": float(cfg.get("temperature", 0.1)),
    }
    # num_gpu: -1 = automático/Ollama decide; 0 = CPU; >0 intenta offload a GPU.
    try:
        num_gpu_cfg = int(cfg.get("ollama_num_gpu", -1))
        if num_gpu_cfg >= 0:
            options["num_gpu"] = num_gpu_cfg
    except Exception:
        pass
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": bool(cfg.get("enable_streaming", False)),
        "options": options,
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


def call_anthropic(prompt: str, **kwargs) -> str:
    cfg = load_config()
    api_key = kwargs.get("api_key") or cfg.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("Anthropic API Key no configurada")
    model = kwargs.get("model") or cfg.get("anthropic_model", "claude-sonnet-4-6")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": int(kwargs.get("max_tokens") or cfg.get("anthropic_max_tokens", 1200)),
        "messages": [{"role": "user", "content": str(prompt or "")}],
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=int(cfg.get("ollama_timeout", 900)))
    r.raise_for_status()
    data = r.json()
    parts = []
    for block in data.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts).strip()


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
    elif backend == "anthropic":
        order.append("anthropic")
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
    if cfg.get("fallback_anthropic", False) and "anthropic" not in order:
        order.append("anthropic")
    if cfg.get("fallback_local", True) and "offline" not in order:
        order.append("offline")

    for item in order:
        try:
            if item == "ollama":
                text = call_ollama(prompt, **kwargs)
            elif item == "anthropic":
                text = call_anthropic(prompt, **kwargs)
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
