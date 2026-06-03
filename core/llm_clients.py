from __future__ import annotations
import os
import requests
from openai import OpenAI
from anthropic import Anthropic
from google import genai
from google.genai import types




# === EMCALI_PATCH_V5_OLLAMA_LITE ===
# Parche defensivo: si este modulo llama Ollama, reduce prompt, tokens y sube timeout.


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

try:
    import requests as _emcali_requests
    if not hasattr(_emcali_requests, "_emcali_original_post_v5"):
        _emcali_requests._emcali_original_post_v5 = _emcali_requests.post
        def _emcali_post_v5(url, *args, **kwargs):
            try:
                url_s = str(url)
                if ("11434" in url_s) or ("/api/generate" in url_s) or ("/api/chat" in url_s):
                    current_timeout = kwargs.get("timeout", 0)
                    try:
                        current_timeout = int(current_timeout or 0)
                    except Exception:
                        current_timeout = 0
                    if current_timeout < 900:
                        kwargs["timeout"] = 900
                    payload = kwargs.get("json")
                    if isinstance(payload, dict):
                        payload["stream"] = False
                        if not payload.get("model") or str(payload.get("model", "")).lower().startswith("llama"):
                            payload["model"] = "phi3:mini"
                        if "prompt" in payload and isinstance(payload["prompt"], str) and len(payload["prompt"]) > 3500:
                            payload["prompt"] = payload["prompt"][:3500] + "\n\n[Contexto recortado automaticamente para modelo local liviano.]"
                        opts = payload.get("options")
                        if not isinstance(opts, dict):
                            opts = {}
                        opts.setdefault("num_predict", 128)
                        opts.setdefault("num_ctx", 2048)
                        opts.setdefault("temperature", 0.1)
                        payload["options"] = opts
                        kwargs["json"] = payload
            except Exception:
                pass
            return _emcali_requests._emcali_original_post_v5(url, *args, **kwargs)
        _emcali_requests.post = _emcali_post_v5
except Exception:
    pass
# === FIN EMCALI_PATCH_V5_OLLAMA_LITE ===

def call_ollama(prompt: str, model: str, base_url: str, timeout_sec: int = 600) -> dict:
    response = requests.post(f"{base_url.rstrip('/')}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=timeout_sec)
    response.raise_for_status()
    payload = response.json()
    return {'text': payload.get('response', '').strip(), 'raw': payload, 'usage': {'total_duration': payload.get('total_duration'), 'eval_count': payload.get('eval_count'), 'eval_duration': payload.get('eval_duration')}}


def call_openai(prompt: str, model: str) -> dict:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    resp = client.responses.create(model=model, input=prompt)
    text = getattr(resp, 'output_text', '') or ''
    return {'text': text.strip(), 'raw': resp.model_dump() if hasattr(resp, 'model_dump') else str(resp), 'usage': getattr(resp, 'usage', None)}


def call_anthropic(prompt: str, model: str) -> dict:
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    msg = client.messages.create(model=model, max_tokens=1200, messages=[{'role': 'user', 'content': prompt}])
    parts = []
    for block in msg.content:
        if getattr(block, 'type', None) == 'text':
            parts.append(block.text)
    raw = msg.model_dump() if hasattr(msg, 'model_dump') else str(msg)
    return {'text': '\n'.join(parts).strip(), 'raw': raw, 'usage': getattr(msg, 'usage', None)}


def call_gemini(prompt: str, model: str) -> dict:
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    resp = client.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0)))
    text = getattr(resp, 'text', '') or ''
    raw = resp.model_dump() if hasattr(resp, 'model_dump') else str(resp)
    return {'text': text.strip(), 'raw': raw, 'usage': None}
