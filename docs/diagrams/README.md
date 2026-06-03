# Diagramas de Arquitectura y Topología

Esta carpeta almacena todos los diagramas técnicos que ilustran el funcionamiento de la plataforma **EMCALI Cyber 2.0 Híbrido**. 

Puedes usarlos como referencia rápida para entender las capas tecnológicas.

## Índice de Diagramas

- **`0) Modelo único de arquitectura.png`**: Visión global de todos los componentes interactuando en el entorno corporativo.
- **`1. Diagrama de Arquitectura de Datos - Flujo de Datos.png`**: Muestra cómo fluyen los reportes de escáneres (ej. Qualys) desde la ingesta, pasando por la normalización, hasta el enriquecimiento y consumo del LLM.
- **`2. Diagrama de Componentes — Arquitectura RAG.png`**: Explica el proceso de Retrieval-Augmented Generation local, detallando la base de datos vectorial y cómo se inyecta contexto en el prompt.
- **`3. Diagrama de Secuencia — Análisis de Vulnerabilidades.png`**: Representación paso a paso de lo que ocurre cuando un usuario solicita un plan de remediación en la interfaz web.
- **`4. Diagrama de Despliegue — Arquitectura Híbrida.png`**: Detalla los servidores físicos/virtuales involucrados, mostrando la red local donde corre Ollama y las salidas controladas a APIs de terceros.
- **`5. Diagrama de Arquitectura — Componente RAG Local.png`**: Zoom al motor RAG para entender el procesamiento de documentos (chunking y embeddings).
- **`6) Topología funcional y módulos internos con ingesta de datos.png`**: Mapa de los módulos en Python (`core`, `pages`) y su relación con el usuario final.
- **`EMCALI Cyber 2.0 Híbrido v3. IMG*.png`**: Capturas y renders adicionales de la evolución de la arquitectura.
- **`POSTER.png`**: Póster ejecutivo resumiendo los beneficios y la estructura tecnológica del Agente EMCALI.
