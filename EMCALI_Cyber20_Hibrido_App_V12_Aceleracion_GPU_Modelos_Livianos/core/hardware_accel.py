# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

LIGHTWEIGHT_MODELS = [
    {"name": "smollm2:135m", "size": "~135M", "use": "prueba ultra liviana / validación rápida", "cmd": "ollama pull smollm2:135m"},
    {"name": "smollm2:360m", "size": "~360M", "use": "prueba liviana con mejor coherencia", "cmd": "ollama pull smollm2:360m"},
    {"name": "qwen2.5:0.5b", "size": "~0.5B", "use": "prueba rápida para clasificación básica", "cmd": "ollama pull qwen2.5:0.5b"},
    {"name": "qwen2.5:1.5b", "size": "~1.5B", "use": "recomendado para Dell T1650 / análisis corto", "cmd": "ollama pull qwen2.5:1.5b"},
    {"name": "tinyllama", "size": "~1.1B", "use": "prueba general de baja carga", "cmd": "ollama pull tinyllama"},
    {"name": "gemma2:2b", "size": "~2B", "use": "balance calidad/velocidad en CPU", "cmd": "ollama pull gemma2:2b"},
    {"name": "phi3:mini", "size": "~3.8B", "use": "calidad superior, puede ser lento en CPU", "cmd": "ollama pull phi3:mini"},
]

NOT_RECOMMENDED_2GB = ["llama3.1:8b", "qwen3:8b", "mistral:7b", "Foundation-Sec-8B"]


def run_cmd(args: List[str], timeout: int = 8) -> Tuple[bool, str]:
    try:
        out = subprocess.check_output(args, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return True, out.strip()
    except subprocess.CalledProcessError as exc:
        return False, (exc.output or str(exc)).strip()
    except Exception as exc:
        return False, str(exc)


def parse_nvidia_smi_csv() -> Dict[str, Any]:
    ok, out = run_cmd([
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    ], timeout=5)
    if not ok:
        return {"detected": False, "message": out}
    line = out.splitlines()[0] if out.splitlines() else ""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 6:
        return {"detected": False, "message": out}
    def to_int(x, default=0):
        try: return int(float(str(x).strip()))
        except Exception: return default
    return {
        "detected": True,
        "name": parts[0],
        "driver": parts[1],
        "memory_used_mb": to_int(parts[2]),
        "memory_total_mb": to_int(parts[3]),
        "gpu_util_percent": to_int(parts[4]),
        "temperature_c": to_int(parts[5]),
        "raw": out,
    }


def nvidia_processes() -> List[Dict[str, str]]:
    ok, out = run_cmd(["nvidia-smi"], timeout=5)
    if not ok:
        return []
    rows = []
    for line in out.splitlines():
        low = line.lower()
        if ".exe" in low or "python" in low or "ollama" in low:
            rows.append({"line": line.strip()})
    return rows


def ollama_ps() -> Dict[str, Any]:
    ok, out = run_cmd(["ollama", "ps"], timeout=6)
    if not ok:
        return {"ok": False, "raw": out, "models": []}
    models = []
    lines = [x for x in out.splitlines() if x.strip()]
    for line in lines[1:]:
        models.append({"line": line})
    return {"ok": True, "raw": out, "models": models}


def ollama_list_models() -> List[str]:
    ok, out = run_cmd(["ollama", "list"], timeout=8)
    if not ok:
        return []
    models = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def is_ollama_using_gpu() -> Tuple[bool, str]:
    ps = ollama_ps()
    raw = ps.get("raw", "")
    low = raw.lower()
    if "gpu" in low and "100% cpu" not in low:
        return True, raw
    for row in nvidia_processes():
        if "ollama" in row.get("line", "").lower():
            return True, row["line"]
    return False, raw or "ollama.exe no aparece en nvidia-smi. Probable modo CPU."


def hardware_recommendation(gpu: Dict[str, Any]) -> Dict[str, Any]:
    if not gpu.get("detected"):
        return {
            "status": "CPU Mode",
            "severity": "warning",
            "message": "No se detecta GPU NVIDIA. Usar modelos livianos por CPU.",
            "recommended": [m["name"] for m in LIGHTWEIGHT_MODELS[:5]],
            "avoid": NOT_RECOMMENDED_2GB,
        }
    name = str(gpu.get("name", "")).lower()
    vram = int(gpu.get("memory_total_mb", 0) or 0)
    if "k2000" in name or vram <= 2500:
        return {
            "status": "CPU Mode recomendado",
            "severity": "info",
            "message": "GPU detectada, pero con VRAM baja/arquitectura antigua. Ollama puede decidir ejecutar en CPU.",
            "recommended": ["smollm2:360m", "qwen2.5:0.5b", "qwen2.5:1.5b", "tinyllama", "gemma2:2b", "phi3:mini"],
            "avoid": NOT_RECOMMENDED_2GB,
        }
    if vram < 6000:
        return {
            "status": "GPU parcial posible",
            "severity": "success",
            "message": "GPU usable para modelos pequeños/medianos. Validar con ollama ps y nvidia-smi.",
            "recommended": ["qwen2.5:1.5b", "gemma2:2b", "phi3:mini"],
            "avoid": ["Foundation-Sec-8B", "modelos > 7B"],
        }
    return {
        "status": "GPU recomendada",
        "severity": "success",
        "message": "GPU con VRAM suficiente para acelerar modelos medianos. Validar consumo antes de producción.",
        "recommended": ["phi3:mini", "gemma2:2b", "llama3.1:8b", "Foundation-Sec-8B"],
        "avoid": [],
    }


def benchmark_prompt(model: str, base_url: str = "http://127.0.0.1:11434", timeout: int = 120) -> Dict[str, Any]:
    import requests
    prompt = "Responde en una frase: prueba de rendimiento EMCALI Cyber 2.0."
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": 64, "temperature": 0.1}}
    start = time.time()
    try:
        r = requests.post(base_url.rstrip("/") + "/api/generate", json=payload, timeout=timeout)
        elapsed = time.time() - start
        r.raise_for_status()
        data = r.json()
        eval_count = data.get("eval_count") or 0
        eval_duration_ns = data.get("eval_duration") or 0
        tps = 0.0
        try:
            tps = float(eval_count) / (float(eval_duration_ns) / 1_000_000_000) if eval_duration_ns else 0.0
        except Exception:
            tps = 0.0
        return {"ok": True, "elapsed_sec": elapsed, "tokens": eval_count, "tokens_sec": tps, "response": data.get("response", ""), "raw": data}
    except Exception as exc:
        return {"ok": False, "elapsed_sec": time.time() - start, "error": str(exc)}
