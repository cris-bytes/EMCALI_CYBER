# -*- coding: utf-8 -*-
from __future__ import annotations
import streamlit as st
import requests
from core.model_manager import all_models, add_custom_model, remove_custom_model, download_model, install_ollama, status, healthcheck
from core.llm_runtime import load_config, save_config
from core.hardware_accel import parse_nvidia_smi_csv, benchmark_prompt

def render(*args, **kwargs):
    st.title("Gestor de Modelos de Ciberseguridad")
    st.caption("V13.1 experimental · Descarga, instalación, healthcheck, selección y benchmark. La V12 aprobada permanece como baseline.")
    cfg=load_config(); gpu=parse_nvidia_smi_csv(); vram=(gpu.get("memory_total_mb",0) or 0)/1024
    st.info(f"GPU: {gpu.get('name','No detectada')} · VRAM detectada: {vram:.2f} GB" if gpu.get("detected") else "GPU NVIDIA no detectada; Ollama puede usar CPU.")
    st.warning("El tamaño GGUF en disco no equivale al consumo total de VRAM. Contexto, KV cache y runtime añaden memoria.")
    st.subheader("Modelos ya instalados en Ollama")
    st.caption("Inventario dinámico de /api/tags. Estos modelos no requieren descarga GGUF ni registro manual.")
    base_url = str(cfg.get('ollama_base_url', 'http://127.0.0.1:11434')).rstrip('/')
    try:
        response = requests.get(base_url + '/api/tags', timeout=6)
        response.raise_for_status()
        installed = response.json().get('models', [])
        names = sorted({m.get('name', '') for m in installed if m.get('name')})
        if names:
            selected = st.selectbox('Modelo Ollama instalado', names, index=names.index(cfg.get('model_name')) if cfg.get('model_name') in names else 0, key='installed_ollama_model_v133')
            matching = next((m for m in installed if m.get('name') == selected), {})
            st.caption(f"Tamaño en disco: {matching.get('size', 0) / 1e9:.2f} GB · Modelo registrado localmente")
            if st.button('Activar modelo instalado', key='activate_installed_ollama_v133', type='primary'):
                cfg['backend'] = 'ollama'
                cfg['model_name'] = selected
                save_config(cfg)
                st.session_state.setdefault('settings', {})['backend'] = 'ollama'
                st.session_state['settings']['model_name'] = selected
                st.success(f'Modelo activo: {selected}. Selección persistida en configuración.')
            if st.button('Probar inferencia del modelo seleccionado', key='test_installed_ollama_v133'):
                with st.spinner('Ejecutando prueba controlada...'):
                    result = benchmark_prompt(selected, base_url, int(cfg.get('ollama_timeout', 900)))
                if result.get('ok'):
                    st.success('Inferencia completada')
                    st.metric('Latencia', f"{result.get('elapsed_sec', 0):.2f} s")
                    st.code(result.get('response', ''))
                else:
                    st.error(result.get('error', 'Falló la inferencia'))
        else:
            st.warning('Ollama no devolvió modelos instalados.')
    except (requests.RequestException, ValueError) as exc:
        st.warning(f'No se pudo consultar el inventario de Ollama: {exc}')
    st.divider()
    st.subheader('Catálogo de modelos GGUF descargables')
    for m in all_models():
        st.markdown("---"); st.subheader(f"{m['name']} · {m['quantization']}")
        st.caption(f"{m['family']} · GGUF {m['size_gb']:.2f} GB · {m['purpose']}")
        s=status(m)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("GGUF", "Descargado" if s['downloaded'] else "Pendiente")
        c2.metric("Ollama", "Instalado" if s['installed'] else "Pendiente")
        c3.metric("Tamaño",f"{m['size_gb']:.2f} GB")
        c4.metric("VRAM orientativa",f"~{m['recommended_vram_gb']:.1f} GB+")
        if gpu.get('detected') and vram and vram < m['recommended_vram_gb']:
            st.warning("VRAM por debajo de la referencia del catálogo: puede requerir offload parcial CPU/GPU o menor contexto.")
        b1,b2,b3,b4=st.columns(4)
        with b1:
            if st.button("Descargar GGUF",key="dl_"+m['id'],disabled=s['downloaded']):
                bar=st.progress(0,text="Preparando descarga...")
                def cb(done,total):
                    pct=int(done*100/total) if total else 0
                    bar.progress(min(100,pct),text=f"{done/1024**3:.2f} / {(total/1024**3 if total else 0):.2f} GB")
                try:
                    p=download_model(m,cb); bar.progress(100,text="Descarga completa"); st.success(f"Guardado: {p}")
                except Exception as e: st.error(f"Descarga fallida: {e}")
        with b2:
            if st.button("Instalar en Ollama",key="in_"+m['id'],disabled=not s['downloaded'] or s['installed']):
                with st.spinner("Creando modelo en Ollama..."):
                    ok,msg=install_ollama(m)
                (st.success if ok else st.error)("Instalación completada." if ok else "No fue posible instalar.")
                with st.expander("Salida técnica"): st.code(msg[-5000:])
        with b3:
            if st.button("Healthcheck",key="hc_"+m['id'],disabled=not s['installed']):
                ok,msg,sec=healthcheck(m,cfg.get('ollama_base_url','http://127.0.0.1:11434'))
                (st.success if ok else st.error)(f"Healthcheck {'OK' if ok else 'falló'} · {sec:.2f} s")
                st.code(msg)
        with b4:
            if st.button("Usar modelo",key="use_"+m['id'],disabled=not s['installed']):
                cfg['backend']='ollama'; cfg['model_name']=m['ollama_name']; save_config(cfg)
                st.session_state.setdefault('settings',{})['backend']='ollama'; st.session_state['settings']['model_name']=m['ollama_name']
                st.success(f"Modelo activo: {m['ollama_name']}")
        if s['installed'] and st.button("Ejecutar benchmark rápido",key="bench_"+m['id']):
            with st.spinner("Ejecutando inferencia controlada..."):
                r=benchmark_prompt(m['ollama_name'],cfg.get('ollama_base_url','http://127.0.0.1:11434'),int(cfg.get('ollama_timeout',900)))
            if r.get('ok'):
                x,y,z=st.columns(3); x.metric('Latencia',f"{r['elapsed_sec']:.2f} s"); y.metric('Tokens',int(r.get('tokens',0) or 0)); z.metric('Tokens/s',f"{r.get('tokens_sec',0):.2f}")
                st.code(r.get('response',''))
            else: st.error(r.get('error','Error desconocido'))
    st.markdown('---')
    st.subheader("➕ Añadir otro modelo GGUF")
    st.caption("Permite ampliar el catálogo sin modificar el código. Registre únicamente modelos GGUF cuya licencia y procedencia hayan sido verificadas.")
    with st.expander("Registrar modelo personalizado", expanded=False):
        with st.form("custom_cyber_model_form", clear_on_submit=True):
            a,b=st.columns(2)
            name=a.text_input("Nombre del modelo *", placeholder="Ej. CyberSecQwen-4B")
            family=b.text_input("Familia", placeholder="Ej. Qwen / Llama / Mistral")
            c,d,e=st.columns(3)
            quant=c.text_input("Cuantización", value="Q4_K_M")
            size=d.number_input("Tamaño GGUF (GB)", min_value=0.0, value=0.0, step=0.01)
            vram=e.number_input("VRAM orientativa (GB)", min_value=0.0, value=0.0, step=0.5)
            filename=st.text_input("Nombre exacto del archivo GGUF *", placeholder="modelo.Q4_K_M.gguf")
            download_url=st.text_input("URL directa de descarga GGUF *", placeholder="https://huggingface.co/.../resolve/main/modelo.gguf")
            repo_url=st.text_input("Repositorio / ficha del modelo", placeholder="https://huggingface.co/...")
            ollama_name=st.text_input("Nombre local Ollama *", placeholder="emcali-modelo:4b-q4")
            sha=st.text_input("SHA-256 (opcional, recomendado)", placeholder="64 caracteres hexadecimales")
            template=st.selectbox("Plantilla", ["llama3","qwen","generic"], index=2)
            purpose=st.text_area("Uso / observaciones", placeholder="Candidato para benchmark de vulnerabilidades...")
            submitted=st.form_submit_button("Agregar al catálogo")
            if submitted:
                try:
                    m=add_custom_model({"name":name,"family":family or "Custom","quantization":quant or "Custom","size_gb":float(size),"filename":filename,"download_url":download_url,"repo_url":repo_url,"ollama_name":ollama_name,"recommended_vram_gb":float(vram),"template":template,"sha256":sha.strip() or None,"purpose":purpose or "Modelo personalizado para evaluación."})
                    st.success(f"Modelo agregado: {m['name']}. Recargue la página para verlo en el catálogo.")
                except Exception as ex: st.error(str(ex))
    custom=[m for m in all_models() if not m.get("builtin",False)]
    if custom:
        with st.expander("Administrar modelos personalizados"):
            for m in custom:
                x,y=st.columns([5,1]); x.write(f"**{m['name']}** · {m.get('quantization','')} · `{m['ollama_name']}`")
                if y.button("Quitar", key="rm_"+m['id']):
                    if remove_custom_model(m['id']): st.success("Entrada retirada del catálogo. El GGUF/Ollama no se elimina automáticamente por seguridad.")
    st.markdown('---')
    st.caption('Los modelos se descargan desde los repositorios configurados. La aplicación no incluye los pesos dentro del ZIP.')
