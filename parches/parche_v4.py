from pathlib import Path
import re



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

ROOT = Path.cwd()
print(f"Aplicando parche V4 Ollama Lite en: {ROOT}")

# Backup helper
def write_if_changed(path: Path, text: str):
    old = path.read_text(encoding='utf-8', errors='ignore') if path.exists() else ''
    if old != text:
        bak = path.with_suffix(path.suffix + '.bak_v4')
        if path.exists() and not bak.exists():
            bak.write_text(old, encoding='utf-8')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        print(f"Actualizado: {path.relative_to(ROOT)}")

# 1. Reemplazo global conservador de modelo pesado
for p in ROOT.rglob('*.py'):
    if '.venv' in p.parts or '__pycache__' in p.parts:
        continue
    txt = p.read_text(encoding='utf-8', errors='ignore')
    old = txt
    txt = txt.replace('phi3:mini', 'phi3:mini')
    txt = txt.replace('phi3:mini', 'phi3:mini')
    if txt != old:
        if not p.with_suffix(p.suffix + '.bak_v4_model').exists():
            p.with_suffix(p.suffix + '.bak_v4_model').write_text(old, encoding='utf-8')
        p.write_text(txt, encoding='utf-8')
        print(f"Modelo liviano aplicado en: {p.relative_to(ROOT)}")

# 2. Crear cliente Ollama robusto y rápido, sin Gemini si no hay key
llm_clients = ROOT / 'core' / 'llm_clients.py'
write_if_changed(llm_clients, r'''import requests


def build_ollama_prompt(query, context=None, finding=None):
    """Construye un prompt corto para evitar timeouts en equipos CPU/Xeon."""
    context = context or ""
    finding = finding or {}
    base = f"""
Eres un analista senior de ciberseguridad IT/OT para EMCALI.
Responde en español, de forma breve, técnica y accionable.

Hallazgo:
{finding}

Contexto RAG:
{context[:2500]}

Consulta:
{query}

Entrega exactamente:
1. Priorización del riesgo.
2. Impacto de negocio.
3. Remediación defensiva en pasos.
4. Evidencia o validación posterior.
""".strip()
    return base


def query_ollama(prompt, settings=None):
    """Consulta Ollama con opciones livianas para máquinas sin GPU potente."""
    settings = settings or {}
    base_url = settings.get('ollama_base_url') or settings.get('base_url') or 'http://127.0.0.1:11434'
    model = settings.get('model_name') or settings.get('ollama_model') or 'phi3:mini'
    timeout = int(settings.get('ollama_timeout') or settings.get('timeout_ollama') or 900)
    url = base_url.rstrip('/') + '/api/generate'
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {
            'temperature': 0.2,
            'num_predict': int(settings.get('ollama_num_predict', 256)),
            'num_ctx': int(settings.get('ollama_num_ctx', 2048)),
            'top_p': 0.9,
        },
    }
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data.get('response', '').strip()


def query_gemini(prompt, settings=None):
    settings = settings or {}
    api_key = settings.get('gemini_api_key') or settings.get('GOOGLE_API_KEY') or settings.get('GEMINI_API_KEY')
    if not api_key:
        return ''
    # Gemini opcional no implementado aquí para evitar fallo por API key ausente.
    return ''


def call_llm(query=None, context=None, finding=None, settings=None, prompt=None):
    settings = settings or {}
    prompt = prompt or build_ollama_prompt(query or '', context=context, finding=finding)
    backend = (settings.get('backend') or settings.get('BackendLLM') or 'ollama').lower()
    if backend == 'offline':
        return ''
    if backend == 'gemini':
        return query_gemini(prompt, settings)
    return query_ollama(prompt, settings)


def ollama_healthcheck(settings=None):
    settings = settings or {}
    base_url = settings.get('ollama_base_url') or 'http://127.0.0.1:11434'
    try:
        r = requests.get(base_url.rstrip('/') + '/api/tags', timeout=10)
        r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, str(e)
''')

# 3. Settings page mejorada con prueba de conexión
settings_page = ROOT / 'pages' / 'settings_page.py'
write_if_changed(settings_page, r'''import streamlit as st
import requests


def _ensure_settings(settings=None):
    if settings is None:
        settings = st.session_state.get('settings', {})
    settings.setdefault('backend', 'ollama')
    settings.setdefault('model_name', 'phi3:mini')
    settings.setdefault('ollama_model', settings.get('model_name', 'phi3:mini'))
    settings.setdefault('ollama_base_url', 'http://127.0.0.1:11434')
    settings.setdefault('ollama_timeout', 900)
    settings.setdefault('ollama_num_predict', 256)
    settings.setdefault('ollama_num_ctx', 2048)
    settings.setdefault('fallback_enabled', False)
    return settings


def render_settings_page(settings=None):
    settings = _ensure_settings(settings)
    st.title('⚙️ Configuración')
    st.subheader('Motor LLM híbrido')

    backend_options = ['ollama', 'offline', 'gemini']
    current_backend = settings.get('backend', 'ollama')
    if current_backend not in backend_options:
        current_backend = 'ollama'
    settings['backend'] = st.selectbox('Backend LLM', backend_options, index=backend_options.index(current_backend))

    model_options = ['phi3:mini', 'tinyllama', 'gemma:2b', 'qwen2.5:3b', 'phi3:mini.2:3b', 'mistral:7b', 'phi3:mini']
    current_model = settings.get('model_name') or settings.get('ollama_model') or 'phi3:mini'
    if current_model not in model_options:
        model_options.insert(0, current_model)
    selected_model = st.selectbox('Modelo Ollama activo', model_options, index=model_options.index(current_model))
    custom_model = st.text_input('Modelo personalizado Ollama opcional', value='', placeholder='Ejemplo: tinyllama')
    settings['model_name'] = custom_model.strip() or selected_model
    settings['ollama_model'] = settings['model_name']

    settings['ollama_base_url'] = st.text_input('URL Ollama', value=settings.get('ollama_base_url', 'http://127.0.0.1:11434'))
    settings['ollama_timeout'] = st.number_input('Timeout Ollama (segundos)', 60, 1800, int(settings.get('ollama_timeout', 900)), 30)
    settings['timeout_ollama'] = settings['ollama_timeout']
    settings['ollama_num_predict'] = st.number_input('Máximo tokens de respuesta Ollama', 64, 1024, int(settings.get('ollama_num_predict', 256)), 64)
    settings['ollama_num_ctx'] = st.number_input('Contexto Ollama', 1024, 8192, int(settings.get('ollama_num_ctx', 2048)), 512)

    settings['fallback_enabled'] = st.toggle('Activar fallback Gemini', value=bool(settings.get('fallback_enabled', False)))
    settings['gemini_api_key'] = st.text_input('Gemini API Key', value=settings.get('gemini_api_key', ''), type='password')

    st.session_state['settings'] = settings
    st.success(f"Modelo activo: {settings['model_name']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button('Probar conexión Ollama'):
            try:
                r = requests.get(settings['ollama_base_url'].rstrip('/') + '/api/tags', timeout=10)
                r.raise_for_status()
                names = [m.get('name') for m in r.json().get('models', [])]
                st.success('Ollama responde correctamente.')
                st.write(names)
            except Exception as e:
                st.error(f'Ollama no responde: {e}')
    with col2:
        if st.button('Probar generación corta'):
            try:
                payload = {
                    'model': settings['model_name'],
                    'prompt': 'Responde únicamente: OK',
                    'stream': False,
                    'options': {'num_predict': 16, 'num_ctx': 1024}
                }
                r = requests.post(settings['ollama_base_url'].rstrip() + '/api/generate', json=payload, timeout=120)
                r.raise_for_status()
                st.success(r.json().get('response', 'Sin respuesta'))
            except Exception as e:
                st.error(f'Generación falló: {e}')

    with st.expander('Comandos recomendados'):
        st.code(f'''ollama list
ollama pull {settings['model_name']}
ollama run {settings['model_name']}
# prueba API:
curl http://127.0.0.1:11434/api/generate -d "{{\"model\":\"{settings['model_name']}\",\"prompt\":\"Responde OK\",\"stream\":false,\"options\":{{\"num_predict\":16}}}}"''', language='bash')
    return settings


def main(settings=None):
    return render_settings_page(settings)

def render(settings=None):
    return render_settings_page(settings)

def page(settings=None):
    return render_settings_page(settings)
''')

# 4. Intentar parchear analysis.py para usar timeout y modelo de settings si hay llamadas directas a requests/Ollama.
analysis = ROOT / 'core' / 'analysis.py'
if analysis.exists():
    txt = analysis.read_text(encoding='utf-8', errors='ignore')
    old = txt
    # Agregar defaults en cualquier settings.get antiguo
    txt = txt.replace("settings.get('model_name', 'phi3:mini')", "settings.get('model_name', 'phi3:mini')")
    txt = txt.replace('settings.get('model_name', 'phi3:mini')', 'settings.get('model_name', 'phi3:mini')')
    txt = re.sub(r'read timeout=900|timeout=900', 'timeout=900', txt)
    # Si hay strings directos de api/generate con stream implícito, este parche se queda en llm_clients.
    if txt != old:
        if not analysis.with_suffix(analysis.suffix + '.bak_v4_analysis').exists():
            analysis.with_suffix(analysis.suffix + '.bak_v4_analysis').write_text(old, encoding='utf-8')
        analysis.write_text(txt, encoding='utf-8')
        print('Timeout reforzado en core/analysis.py')

print('\nParche V4 finalizado.')
print('Reinicie Streamlit: CTRL+C y luego streamlit run app.py')
