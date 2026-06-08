# -*- coding: utf-8 -*-
from __future__ import annotations
import subprocess
import streamlit as st

from core.hardware_accel import (
    LIGHTWEIGHT_MODELS,
    benchmark_prompt,
    hardware_recommendation,
    is_ollama_using_gpu,
    ollama_list_models,
    ollama_ps,
    parse_nvidia_smi_csv,
)
from core.llm_runtime import load_config, save_config


def _install_model(model_name: str) -> None:
    try:
        with st.spinner(f"Instalando {model_name} con Ollama..."):
            proc = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True, timeout=1800)
        if proc.returncode == 0:
            st.success(f"Modelo instalado correctamente: {model_name}")
            st.code(proc.stdout[-2000:] if proc.stdout else "Instalación finalizada.")
        else:
            st.error(f"No fue posible instalar {model_name}.")
            st.code((proc.stdout or "") + "\n" + (proc.stderr or ""))
    except Exception as exc:
        st.error(f"Error instalando modelo: {exc}")


def render(*args, **kwargs):
    st.title("Aceleración IA / GPU")
    st.caption("Diagnóstico de hardware, GPU NVIDIA, Ollama, modelos livianos y recomendaciones para equipos EMCALI.")

    cfg = load_config()
    gpu = parse_nvidia_smi_csv()
    rec = hardware_recommendation(gpu)

    st.subheader("1. Estado de hardware")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("GPU detectada", "Sí" if gpu.get("detected") else "No")
    with c2:
        st.metric("GPU", gpu.get("name", "No detectada"))
    with c3:
        st.metric("VRAM", f"{gpu.get('memory_used_mb',0)} / {gpu.get('memory_total_mb',0)} MB")
    with c4:
        st.metric("GPU Util", f"{gpu.get('gpu_util_percent',0)}%")

    if gpu.get("detected"):
        st.info(f"Driver: {gpu.get('driver')} · Temperatura: {gpu.get('temperature_c')} °C")
    else:
        st.warning(gpu.get("message", "No se detectó GPU NVIDIA."))

    st.subheader("2. Estado real de Ollama en CPU/GPU")
    using_gpu, detail = is_ollama_using_gpu()
    if using_gpu:
        st.success("Ollama parece estar usando GPU o aparece como proceso asociado en nvidia-smi.")
    else:
        st.warning("Ollama no aparece usando GPU. Modo probable: CPU.")
    with st.expander("Ver salida técnica de ollama ps / nvidia-smi"):
        st.code(detail)
        ps = ollama_ps()
        st.code(ps.get("raw", "Sin salida de ollama ps"))

    st.subheader("3. Recomendación automática")
    if rec["severity"] == "success":
        st.success(f"{rec['status']}: {rec['message']}")
    elif rec["severity"] == "warning":
        st.warning(f"{rec['status']}: {rec['message']}")
    else:
        st.info(f"{rec['status']}: {rec['message']}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Modelos recomendados para este equipo**")
        st.write(", ".join(rec.get("recommended", [])))
    with col_b:
        st.markdown("**Modelos no recomendados / pesados**")
        st.write(", ".join(rec.get("avoid", [])) or "Sin restricciones relevantes detectadas.")

    st.subheader("4. Modelos livianos para instalar/probar")
    installed = set(ollama_list_models())
    for m in LIGHTWEIGHT_MODELS:
        cols = st.columns([2, 1, 4, 2])
        with cols[0]:
            st.write(f"**{m['name']}**")
        with cols[1]:
            st.write(m["size"])
        with cols[2]:
            st.caption(m["use"])
        with cols[3]:
            if m["name"] in installed:
                st.success("Instalado")
            else:
                if st.button(f"Instalar", key=f"install_{m['name']}"):
                    _install_model(m["name"])

    st.subheader("5. Configuración de aceleración para Ollama")
    st.caption("La aplicación EMCALI no calcula directamente en GPU; envía peticiones a Ollama. Ollama decide CPU/GPU según driver, CUDA, VRAM y modelo. Estos parámetros ayudan a controlar el comportamiento.")
    current = int(cfg.get("ollama_num_gpu", -1))
    options = [-1, 0, 1, 10, 99]
    labels = {
        -1: "Automático / Ollama decide",
        0: "Forzar CPU",
        1: "Intentar 1 capa en GPU",
        10: "Intentar 10 capas en GPU",
        99: "Intentar máximo en GPU"
    }
    selected = st.selectbox("Modo num_gpu para Ollama", options, index=options.index(current) if current in options else 0, format_func=lambda x: labels[x])
    cfg["ollama_num_gpu"] = int(selected)
    cfg["gpu_monitoring_enabled"] = st.checkbox("Activar monitoreo GPU en métricas", value=bool(cfg.get("gpu_monitoring_enabled", True)))
    if st.button("Guardar configuración de aceleración", type="primary"):
        save_config(cfg)
        st.success("Configuración guardada. Reinicia la aplicación para aplicar completamente los cambios.")

    st.subheader("6. Benchmark rápido")
    available = ollama_list_models() or [cfg.get("model_name", "phi3:mini")]
    model = st.selectbox("Modelo a probar", available, index=available.index(cfg.get("model_name")) if cfg.get("model_name") in available else 0)
    if st.button("Ejecutar benchmark local"):
        result = benchmark_prompt(model, cfg.get("ollama_base_url", "http://127.0.0.1:11434"), int(cfg.get("ollama_timeout", 120)))
        if result.get("ok"):
            b1, b2, b3 = st.columns(3)
            b1.metric("Latencia", f"{result['elapsed_sec']:.2f} s")
            b2.metric("Tokens", int(result.get("tokens", 0) or 0))
            b3.metric("Tokens/s", f"{result.get('tokens_sec', 0):.2f}")
            st.code(result.get("response", ""))
        else:
            st.error(result.get("error"))

    st.subheader("7. Interpretación para Dell T1650 + Quadro K2000")
    st.markdown("""
- Si `nvidia-smi` muestra Quadro K2000 pero `ollama ps` no muestra GPU, el modo efectivo es CPU.
- Con 2 GB de VRAM se recomiendan modelos pequeños: `qwen2.5:1.5b`, `gemma2:2b`, `tinyllama`, `smollm2`.
- Para modelos de ciberseguridad grandes como Foundation-Sec-8B se recomienda una GPU con más VRAM o usar CPU con paciencia.
- La aplicación ahora valida hardware, recomienda modelos y permite monitorear si Ollama realmente usa GPU.
""")
