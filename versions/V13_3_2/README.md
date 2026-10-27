# EMCALI Cyber 2.0 Híbrido

Aplicación modular en Streamlit para gestión defensiva de vulnerabilidades con:
- normalización Qualys / Tenable / CSV / JSON
- análisis LLM con RAG local
- backend híbrido: mock, Ollama, OpenAI, Anthropic y Gemini
- reportes, riesgo, remediación y métricas
- empaquetado Windows con PyInstaller y NSIS

## Ejecución rápida

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```

## Variables de entorno opcionales

Copie `.env.example` a `.env` y ajuste credenciales si va a usar backends cloud.


## Formatos de ingesta soportados (versión ampliada)

La aplicación ahora acepta y normaliza automáticamente:
- Exportaciones de Qualys y Tenable/Nessus
- JSON en esquema unificado de EMCALI Cyber 2.0
- CSV y Excel con datasets enriquecidos tipo NVD + CISA KEV + EPSS
- Archivos tipo `cve_cisa_epss_enriched_dataset.csv`
- Archivos tipo `cve_corpus.csv`

El normalizador:
- mapea nombres alternativos de columnas
- calcula `severity` a partir de CVSS cuando no existe
- deriva `exploitability` usando CVSS, EPSS y CISA KEV
- completa campos faltantes con valores por defecto para mantener el Unified Schema
