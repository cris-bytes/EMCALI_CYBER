# Integración NVD + FIRST EPSS — V13.3.1 experimental

1. Haga respaldo de su instalación y de los datos. Extraiga el paquete en una carpeta NUEVA. No sobrescriba la V12.
2. Use Ingesta para cargar el archivo original `01_Smoke_KEV_50.xlsx`.
3. En la misma pantalla, en **NVD + FIRST EPSS**, cargue `hallazgos_50_enriquecidos.xlsx` generado previamente en PowerShell y pulse **Aplicar enriquecimiento a los hallazgos**.
4. Revise el resumen: coincidencias, CVSS y EPSS con metadatos de procedencia. Luego visite Riesgo.
5. No se consulta Internet al importar; se conservan los metadatos originales. No hay verificación independiente de los 50 CVE sin el archivo de respuestas de las API.
6. Los CVE sin coincidencia o con metadatos insuficientes no se sustituyen con ceros.
7. La interfaz usa datos en memoria de sesión; al reiniciar la sesión deberá volver a cargar ambos archivos.
8. Las puntuaciones y versiones CVSS de distintas generaciones no son directamente equivalentes para comparaciones estadísticas.

**Advertencia:** el archivo Excel generado contiene resultados de consultas, pero no incluye necesariamente las respuestas JSON originales firmadas ni una prueba independiente de su procedencia. Para auditoría formal conserve respuestas JSON, fecha/hora, URL y hash SHA-256.
