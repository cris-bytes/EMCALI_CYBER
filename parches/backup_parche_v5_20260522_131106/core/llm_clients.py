from __future__ import annotations
import os
import requests
from openai import OpenAI
from anthropic import Anthropic
from google import genai
from google.genai import types


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
