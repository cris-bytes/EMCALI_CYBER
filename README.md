# EMCALI Cyber 2.0 Híbrido

Aplicación modular en Streamlit para la gestión defensiva de vulnerabilidades con capacidades avanzadas de análisis e integración de múltiples fuentes y modelos de lenguaje (LLMs).

## Características Principales
- Normalización automática de exportaciones (Qualys, Tenable, CSV, JSON).
- Análisis asistido por LLM con RAG (Retrieval-Augmented Generation) local.
- Soporte para múltiples backends de IA: mock, Ollama (Local), OpenAI, Anthropic y Gemini (Cloud).
- Reportes detallados sobre riesgo, remediación y métricas de ciberseguridad.
- Empaquetado optimizado para Windows mediante PyInstaller y NSIS.

## 🚀 Guía de Ejecución y Despliegue

La aplicación se puede ejecutar de varias formas dependiendo de tu entorno (Desarrollo, Producción local con `.bat`, o usando diferentes modelos de Inteligencia Artificial).

### Opción 1: Ejecución Rápida en Windows (Scripts .bat)

Si estás en Windows y prefieres no lidiar con comandos, puedes usar los scripts preconfigurados:
1. Asegúrate de tener Python 3.9 o superior instalado.
2. Da doble clic en **`run_app.bat`**: Este script creará automáticamente el entorno virtual, instalará las dependencias de `requirements.txt` y abrirá la aplicación en tu navegador.
3. Si tienes [Ollama](https://ollama.com/) instalado localmente, puedes hacer doble clic en **`run_app_con_ollama.bat`**. Este script verificará que el servicio de Ollama esté corriendo antes de iniciar la app.

### Opción 2: Ejecución Manual (Terminal / Desarrollo)

Si deseas levantar el entorno manualmente (ideal para desarrolladores y Linux/macOS):

```bash
# 1. Crear Entorno Virtual
python -m venv .venv

# 2. Activar Entorno
# En Windows (Powershell/CMD):
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

# 3. Instalar Dependencias
pip install -r requirements.txt

# 4. Iniciar la Aplicación
python -m streamlit run app.py
```

### ⚙️ Configuración de Variables (Backends IA)

Para usar servicios en la nube (OpenAI, Gemini, Anthropic), debes configurar tus API Keys:
1. Copia el archivo `.env.example` y renómbralo a `.env`.
2. Edita `.env` agregando tus claves reales:
```env
OPENAI_API_KEY=tu_clave_aqui
ANTHROPIC_API_KEY=tu_clave_aqui
GEMINI_API_KEY=tu_clave_aqui
```
*Si usas Ollama (local), no necesitas editar este archivo.*

---

## 📂 Estructura del Proyecto y Documentación

Para entender cómo funciona internamente, visita los manuales específicos de cada carpeta:

- **[core/](core/)**: Contiene la lógica del negocio (conexión a LLMs, normalización, estado de la app).
- **[pages/](pages/)**: Contiene cada una de las vistas de la interfaz en Streamlit (Dashboard, RAG, Análisis).
- **[docs/diagrams/](docs/diagrams/)**: Diagramas de arquitectura, componentes y secuencia.
- **[docs/reports/](docs/reports/)**: Informes técnicos detallados y manuales de arquitectura en PDF/DOCX.

## Formatos de Ingesta Soportados

La aplicación acepta y normaliza automáticamente:
- Exportaciones directas de **Qualys** y **Tenable/Nessus**.
- JSON bajo el esquema unificado de EMCALI Cyber 2.0.
- CSV y Excel con datasets enriquecidos (NVD + CISA KEV + EPSS).
- Archivos estándar como `cve_corpus.csv` o `cve_cisa_epss_enriched_dataset.csv`.

---

## 👥 Equipo y Autores

Este proyecto fue desarrollado y estructurado por el siguiente equipo:
- **Rubén Darío Sabogal**
- **Edwin Pérez Lozano**
- **Cristian Camilo Quebrada Bautista**
