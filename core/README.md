# Directorio Core

Este directorio contiene el motor central de **EMCALI Cyber 2.0 Híbrido**. Aquí reside toda la lógica de negocio, manejo de estado y comunicación con los modelos de lenguaje.

## Archivos Principales

- **`analysis.py`**: Lógica central para analizar vulnerabilidades, calcular métricas compuestas y generar recomendaciones base.
- **`enrichment.py`**: Funciones para enriquecer datos de vulnerabilidades cruzando información con CISA KEV y EPSS.
- **`llm_clients.py`**: Conectores e integraciones con diferentes proveedores de IA (Ollama de forma local, OpenAI, Anthropic, Gemini). Maneja los *prompts* y la estructura de respuestas.
- **`llm_runtime.py`**: Motor de ejecución del RAG (Retrieval-Augmented Generation). Coordina la búsqueda en la base de conocimiento local y el envío de contexto al LLM seleccionado.
- **`normalizer.py`**: Lógica de estandarización. Convierte reportes disparatados (Qualys, Nessus, CSV personalizados) al esquema unificado (`Unified Schema`) de la aplicación.
- **`state.py`**: Manejador del estado global de Streamlit. Almacena las variables de sesión de forma segura a través de las distintas vistas (páginas).
- **`ui.py`**: Utilidades y componentes reusables de interfaz de usuario para inyectar consistencia visual a lo largo de la app.

## Notas para Desarrolladores
Si deseas agregar soporte para una nueva fuente de datos (ej. un nuevo escáner), debes añadir las reglas de mapeo en `normalizer.py`. Si deseas integrar un nuevo LLM, añade la clase conector en `llm_clients.py`.
