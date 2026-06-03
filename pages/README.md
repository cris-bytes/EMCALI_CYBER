# Directorio Pages

Este directorio contiene las vistas (páginas) de la aplicación Streamlit. La interfaz de usuario es modular; cada archivo aquí representa una pestaña o página accesible desde la barra lateral izquierda.

## Páginas Disponibles

- **`analyze.py`**: Vista donde el usuario puede solicitar al LLM un análisis profundo de una vulnerabilidad específica, viendo el cruce de datos con CISA KEV y EPSS.
- **`dashboard.py`**: El panel de control principal. Muestra métricas clave, KPIs de ciberseguridad, y gráficos generales del estado actual de las vulnerabilidades cargadas.
- **`ingest.py`**: Interfaz para cargar archivos de escáneres (Qualys, Nessus) o CSVs. Aquí se dispara internamente el `normalizer.py` del módulo core.
- **`metrics_eval.py`**: Página dedicada a evaluar el rendimiento de los análisis del LLM y las métricas de completitud de datos (Data Quality).
- **`rag.py`**: Interfaz tipo "Chat" para interactuar con el motor RAG. Permite al usuario hacer preguntas en lenguaje natural sobre las vulnerabilidades y políticas internas cargadas en la base de datos.
- **`remediate.py`**: Vista orientada a los equipos de operaciones de TI (IT Ops). Muestra planes de parcheo, tickets sugeridos y tareas de mitigación paso a paso generadas por la IA.
- **`reports.py`**: Generador de informes. Permite exportar los resultados consolidados a formatos ejecutivos (PDF/CSV) para gerencia.
- **`risk.py`**: Mapa de calor (Heatmap) y matriz de riesgo. Cruza impacto vs probabilidad para destacar los CVEs que requieren atención inmediata.
- **`settings_page.py`**: Configuración de la aplicación. Aquí el usuario puede elegir qué LLM usar (Ollama, OpenAI, etc.), definir temperaturas del modelo y ajustar *prompts* del sistema.
