# -*- coding: utf-8 -*-
"""
Parche V5 para EMCALI Cyber 2.0 Hibrido
- Fuerza modelo liviano phi3:mini por defecto.
- Evita timeouts largos/colgados ajustando payload de Ollama.
- Crea backup automatico de archivos .py modificados.
Ejecutar desde la raiz de la aplicacion: C:\\EMCALI_Cyber20_Hibrido_App o C:\\emcali-cyber-app
"""
from __future__ import print_function
import os
import re
import shutil
import datetime

ROOT = os.getcwd()
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = os.path.join(ROOT, "backup_parche_v5_" + STAMP)
MODEL = "phi3:mini"
TIMEOUT = "900"
MAX_PROMPT = "3500"
NUM_PREDICT = "128"
NUM_CTX = "2048"

MARKER = "# === EMCALI_PATCH_V5_OLLAMA_LITE ==="

PATCH_CODE = r'''
# === EMCALI_PATCH_V5_OLLAMA_LITE ===
# Parche defensivo: si este modulo llama Ollama, reduce prompt, tokens y sube timeout.
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
'''

def should_skip(path):
    lower = path.lower()
    return (".venv" + os.sep in lower or "__pycache__" in lower or "backup_parche" in lower)

def read_text(path):
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read(), enc
        except Exception:
            continue
    return None, None

def write_text(path, text, enc):
    with open(path, "w", encoding=enc or "utf-8", newline="") as f:
        f.write(text)

def backup(path):
    rel = os.path.relpath(path, ROOT)
    dst = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(path, dst)

py_files = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in (".venv", "__pycache__") and not d.startswith("backup_parche")]
    for fn in files:
        if fn.endswith(".py"):
            p = os.path.join(base, fn)
            if not should_skip(p):
                py_files.append(p)

if not py_files:
    print("ERROR: no se encontraron archivos .py. Ejecuta este parche desde la carpeta raiz de la app.")
    raise SystemExit(1)

os.makedirs(BACKUP_DIR, exist_ok=True)
modified = []

for path in py_files:
    text, enc = read_text(path)
    if text is None:
        continue
    original = text

    # 1) Reemplazos directos de modelos pesados por defecto.
    replacements = [
        ("llama3.1:8b", MODEL),
        ("llama3:8b", MODEL),
        ("llama3.1", MODEL),
        ("llama3", MODEL),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    # 2) Defaults comunes de configuracion.
    text = re.sub(r"('model_name'\s*:\s*)'[^']+'", r"\1'" + MODEL + r"'", text)
    text = re.sub(r'("model_name"\s*:\s*)"[^"]+"', r'\1"' + MODEL + r'"', text)
    text = re.sub(r"settings\.get\(\s*['\"]model_name['\"]\s*,\s*['\"][^'\"]+['\"]\s*\)", "settings.get('model_name', '" + MODEL + "')", text)
    text = re.sub(r"settings\.get\(\s*['\"]ollama_timeout['\"]\s*,\s*\d+\s*\)", "settings.get('ollama_timeout', " + TIMEOUT + ")", text)
    text = re.sub(r"settings\.get\(\s*['\"]timeout['\"]\s*,\s*\d+\s*\)", "settings.get('timeout', " + TIMEOUT + ")", text)
    text = re.sub(r"timeout\s*=\s*300\b", "timeout=" + TIMEOUT, text)
    text = re.sub(r"timeout\s*=\s*600\b", "timeout=" + TIMEOUT, text)

    # 3) Insertar wrapper defensivo en modulos que usan requests/Ollama.
    lower = text.lower()
    if ("ollama" in lower or "11434" in lower or "/api/generate" in lower) and ("requests" in lower):
        if MARKER not in text:
            # Insertar despues de imports iniciales; si falla, al inicio.
            lines = text.splitlines(True)
            insert_at = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from ") or stripped == "" or stripped.startswith("#"):
                    insert_at = i + 1
                    continue
                break
            lines.insert(insert_at, "\n" + PATCH_CODE + "\n")
            text = "".join(lines)

    if text != original:
        backup(path)
        write_text(path, text, enc)
        modified.append(os.path.relpath(path, ROOT))

# 4) Crear/actualizar .env recomendado.
env_path = os.path.join(ROOT, ".env")
if os.path.exists(env_path):
    env_text, env_enc = read_text(env_path)
    if env_text is None:
        env_text, env_enc = "", "utf-8"
else:
    env_text, env_enc = "", "utf-8"
orig_env = env_text

def upsert_env(txt, key, value):
    pattern = re.compile(r"^" + re.escape(key) + r"=.*$", re.MULTILINE)
    line = key + "=" + value
    if pattern.search(txt):
        return pattern.sub(line, txt)
    if txt and not txt.endswith("\n"):
        txt += "\n"
    return txt + line + "\n"

for k, v in [
    ("OLLAMA_MODEL", MODEL),
    ("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    ("OLLAMA_TIMEOUT", TIMEOUT),
    ("OLLAMA_NUM_PREDICT", NUM_PREDICT),
    ("OLLAMA_NUM_CTX", NUM_CTX),
    ("LLM_BACKEND", "ollama"),
    ("GEMINI_ENABLED", "false"),
]:
    env_text = upsert_env(env_text, k, v)
if env_text != orig_env:
    if os.path.exists(env_path):
        backup(env_path)
    write_text(env_path, env_text, env_enc)
    modified.append(".env")

print("\n=== PARCHE V5 APLICADO ===")
print("Carpeta raiz:", ROOT)
print("Backup:", BACKUP_DIR)
if modified:
    print("Archivos modificados:")
    for m in modified:
        print(" -", m)
else:
    print("No hubo cambios nuevos; probablemente el parche ya estaba aplicado.")
print("\nSiguiente paso:")
print("1) Cierra Streamlit con CTRL+C")
print("2) Verifica Ollama: curl http://127.0.0.1:11434/api/generate -d \"{\\\"model\\\":\\\"phi3:mini\\\",\\\"prompt\\\":\\\"OK\\\",\\\"stream\\\":false}\"")
print("3) Ejecuta: streamlit run app.py")
