# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, time
from pathlib import Path
from typing import Dict, Any, Callable, List
import requests

APP_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = APP_ROOT / "models" / "cybersecurity"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

CYBER_MODELS = [
    {
        "id": "cybersec-assistant-3b-q5",
        "name": "CyberSec-Assistant-3B",
        "family": "Qwen2.5-3B-Instruct",
        "quantization": "Q5_K_M",
        "size_gb": 2.07,
        "filename": "cybersec-assistant-3b-Q5_K_M.gguf",
        "download_url": "https://huggingface.co/AYI-NEDJIMI/CyberSec-Assistant-3B-GGUF/resolve/main/cybersec-assistant-3b-Q5_K_M.gguf?download=true",
        "repo_url": "https://huggingface.co/AYI-NEDJIMI/CyberSec-Assistant-3B-GGUF",
        "ollama_name": "emcali-cybersec-assistant:3b-q5",
        "recommended_vram_gb": 3.0,
        "template": "qwen",
        "sha256": None,
        "purpose": "SLM especializado en ciberseguridad; candidato principal para pruebas con VRAM limitada.",
        "builtin": True,
    },
    {
        "id": "foundation-sec-8b-instruct-q4",
        "name": "Foundation-Sec-8B-Instruct",
        "family": "Llama 3.1 8B",
        "quantization": "Q4_K_M",
        "size_gb": 4.92,
        "filename": "Foundation-Sec-8B-Instruct-Q4_K_M.gguf",
        "download_url": "https://huggingface.co/dr-ry/Foundation-Sec-8B-Instruct-GGUF/resolve/main/Foundation-Sec-8B-Instruct-Q4_K_M.gguf?download=true",
        "repo_url": "https://huggingface.co/dr-ry/Foundation-Sec-8B-Instruct-GGUF",
        "ollama_name": "emcali-foundation-sec:8b-q4",
        "recommended_vram_gb": 6.0,
        "template": "llama3",
        "sha256": None,
        "purpose": "Modelo 8B especializado en ciberseguridad; prueba exigente de calidad/rendimiento.",
        "builtin": True,
    },
    {
        "id": "lily-cybersecurity-7b-q4km",
        "name": "Lily-Cybersecurity-7B-v0.2",
        "family": "Mistral 7B Instruct",
        "quantization": "Q4_K_M",
        "size_gb": 4.37,
        "filename": "Lily-7B-Instruct-v0.2.Q4_K_M.gguf",
        "download_url": "https://huggingface.co/segolilylabs/Lily-Cybersecurity-7B-v0.2-GGUF/resolve/main/Lily-7B-Instruct-v0.2.Q4_K_M.gguf?download=true",
        "repo_url": "https://huggingface.co/segolilylabs/Lily-Cybersecurity-7B-v0.2-GGUF",
        "ollama_name": "emcali-lily-cybersecurity:7b-q4",
        "recommended_vram_gb": 5.5,
        "template": "llama3",
        "sha256": "7a65855a499f4cb41ccfbca00df3022884beaa6be74c3067eb5e0ee9206ceb29",
        "purpose": "Modelo 7B especializado en ciberseguridad; candidato adicional para benchmark local.",
        "builtin": True,
    },
]

CUSTOM_CATALOG = APP_ROOT / "models" / "custom_cyber_models.json"

def _safe_id(value: str) -> str:
    import re
    v=re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip()).strip("-._").lower()
    return v[:80] or "custom-model"

def load_custom_models() -> List[Dict[str, Any]]:
    if not CUSTOM_CATALOG.exists(): return []
    try:
        data=json.loads(CUSTOM_CATALOG.read_text(encoding="utf-8"))
        return data if isinstance(data,list) else []
    except Exception: return []

def all_models() -> List[Dict[str, Any]]:
    return CYBER_MODELS + load_custom_models()

def add_custom_model(model: Dict[str, Any]) -> Dict[str, Any]:
    required=["name","filename","download_url","ollama_name"]
    missing=[x for x in required if not str(model.get(x,"")).strip()]
    if missing: raise ValueError("Faltan campos: "+", ".join(missing))
    if not str(model["filename"]).lower().endswith(".gguf"): raise ValueError("El archivo debe ser GGUF (.gguf).")
    if not str(model["download_url"]).lower().startswith(("https://","http://")): raise ValueError("La URL de descarga debe ser HTTP/HTTPS.")
    model=dict(model); model["id"]=_safe_id(model.get("id") or model["name"]+"-"+model.get("quantization","custom")); model["builtin"]=False
    items=load_custom_models()
    if any(x.get("id")==model["id"] for x in CYBER_MODELS+items): raise ValueError("Ya existe un modelo con ese ID.")
    items.append(model); CUSTOM_CATALOG.parent.mkdir(parents=True,exist_ok=True)
    CUSTOM_CATALOG.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
    return model

def remove_custom_model(model_id: str) -> bool:
    items=load_custom_models(); new=[x for x in items if x.get("id")!=model_id]
    if len(new)==len(items): return False
    CUSTOM_CATALOG.write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding="utf-8"); return True

def model_path(model: Dict[str, Any]) -> Path:
    return MODEL_DIR / model["filename"]

def installed_ollama_models() -> list[str]:
    try:
        p=subprocess.run(["ollama","list"],capture_output=True,text=True,timeout=10)
        if p.returncode != 0: return []
        return [x.split()[0] for x in p.stdout.splitlines()[1:] if x.strip()]
    except Exception: return []

def status(model: Dict[str, Any]) -> Dict[str, Any]:
    p=model_path(model)
    installed=model["ollama_name"] in installed_ollama_models()
    return {"downloaded": p.exists(), "bytes": p.stat().st_size if p.exists() else 0, "installed": installed, "path": str(p)}

def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""): h.update(block)
    return h.hexdigest()

def download_model(model: Dict[str, Any], progress_cb: Callable[[int,int],None]|None=None) -> Path:
    """Download GGUF with HTTP Range resume. Leaves .part until complete."""
    dest=model_path(model); part=dest.with_suffix(dest.suffix+".part")
    existing=part.stat().st_size if part.exists() else 0
    headers={"Range":f"bytes={existing}-"} if existing else {}
    with requests.get(model["download_url"],headers=headers,stream=True,timeout=(20,120),allow_redirects=True) as r:
        if existing and r.status_code == 200: # server ignored Range
            existing=0; part.unlink(missing_ok=True)
        r.raise_for_status()
        total=existing+int(r.headers.get("content-length",0) or 0)
        mode="ab" if existing else "wb"
        done=existing
        with part.open(mode) as f:
            for chunk in r.iter_content(chunk_size=4*1024*1024):
                if not chunk: continue
                f.write(chunk); done += len(chunk)
                if progress_cb: progress_cb(done,total)
    part.replace(dest)
    expected=model.get("sha256")
    if expected and _sha256(dest).lower()!=expected.lower():
        dest.unlink(missing_ok=True); raise RuntimeError("SHA-256 no coincide; archivo eliminado.")
    return dest

def create_modelfile(model: Dict[str, Any]) -> Path:
    gguf=model_path(model)
    mf=MODEL_DIR / (model["id"]+".Modelfile")
    common='''\nSYSTEM """Eres el motor local de análisis defensivo de EMCALI Cyber 2.0 Híbrido. Analiza vulnerabilidades y remediaciones usando la evidencia suministrada y el contexto RAG. No inventes CVE, CVSS, EPSS ni CISA KEV. Distingue evidencia recuperada de inferencias del modelo."""\nPARAMETER temperature 0.2\nPARAMETER top_p 0.9\nPARAMETER num_ctx 4096\n'''
    if model.get("template")=="qwen":
        tmpl='''TEMPLATE """<|im_start|>system\n{{ .System }}<|im_end|>\n<|im_start|>user\n{{ .Prompt }}<|im_end|>\n<|im_start|>assistant\n"""\nPARAMETER stop "<|im_end|>"\n'''
    else: tmpl=""
    mf.write_text(f'FROM "{gguf.as_posix()}"\n'+tmpl+common,encoding="utf-8")
    return mf

def install_ollama(model: Dict[str, Any], timeout:int=1800) -> tuple[bool,str]:
    if not model_path(model).exists(): return False,"Primero descargue el GGUF."
    mf=create_modelfile(model)
    try:
        p=subprocess.run(["ollama","create",model["ollama_name"],"-f",str(mf)],capture_output=True,text=True,timeout=timeout)
        return p.returncode==0,(p.stdout+"\n"+p.stderr).strip()
    except Exception as e: return False,str(e)

def healthcheck(model: Dict[str, Any], base_url="http://127.0.0.1:11434", timeout=180) -> tuple[bool,str,float]:
    t=time.time()
    try:
        payload={"model":model["ollama_name"],"prompt":"Responde solo: EMCALI CYBER MODEL OK","stream":False,"options":{"num_predict":16,"temperature":0.0}}
        r=requests.post(base_url.rstrip("/")+"/api/generate",json=payload,timeout=timeout)
        r.raise_for_status(); txt=r.json().get("response","").strip()
        return bool(txt),txt,time.time()-t
    except Exception as e: return False,str(e),time.time()-t
