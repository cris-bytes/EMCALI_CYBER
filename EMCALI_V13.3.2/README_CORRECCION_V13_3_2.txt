EMCALI Cyber V13.3.2 - PARCHE EXPERIMENTAL de normalizador, motor y ejecutor

CAMBIOS:
- core/normalizer.py: mapea cvss_official->cvss, epss_official->epss, sin inventar valores.
- Preserva cisa_kev desconocido (None), distingue YES/NO, y conserva metadatos de procedencia del benchmark.
- En Unified JSON no inventa CVSS=5, EPSS=0 ni CISA KEV=False cuando faltan.
- core/risk_engine_v1332.py: acepta KEV explícito, mantiene desconocido != cero.
- core/enrichment_bridge.py: interpreta 'si' además de 'sí'.
- ejecutar_bateria2_corregida_v13.py: compara casos de referencia con el motor REAL, casos faltantes, inválidos y sensibilidad; recorre los 10 datasets, guarda hashes, cobertura y CSV por hallazgo.

IMPORTANTE: La ejecución de validación local (Linux Python 3, sin Streamlit/OpenAI instalados) dio 34 PASS, 0 FAIL, 5 PENDING. 3.000 filas evaluadas, 0 scores completos porque CVSS/EPSS oficiales no estaban disponibles en esos archivos. No es prueba de GPU/Windows/Streamlit. No modificar V12 ni sustituir V13.3.2 aprobada en HP Victus antes de validar.

INSTALACION EN WINDOWS:
1. Respaldar C:\EMCALI_Cyber_V13_3_2_EXP; trabajar en copia C:\EMCALI_Cyber_V13_3_2_PATCH_EXP.
2. Extraer este ZIP dentro de la copia, conservando las carpetas core y el ejecutor en la raiz.
3. cd C:\EMCALI_Cyber_V13_3_2_PATCH_EXP
4. python -m py_compile .\core\normalizer.py .\core\risk_engine_v1332.py .\core\enrichment_bridge.py .\ejecutar_bateria2_corregida_v13.py
5. python .\ejecutar_bateria2_corregida_v13.py --app-dir "C:\EMCALI_Cyber_V13_3_2_PATCH_EXP" --datasets-dir "C:\EMCALI_Cyber_V12_Benchmark_V2_Completo\EMCALI_Cyber_V12_Benchmark_V2\datasets" --out "C:\EMCALI_Cyber_V13_3_2_PATCH_EXP\bateria2_corregida"
6. Revisar bateria2_corregida_manifest.json, bateria2_corregida_resultados.csv, cobertura_datasets.csv y evidencia_riesgo_por_hallazgo.csv.

No se requiere --online en este ejecutor; el flag está reservado. La verificación oficial independiente, la persistencia de Streamlit y la inferencia GPU siguen PENDING. Para obtener scores completos, enriquecer CVSS/EPSS con NVD/FIRST, con procedencia verificable, sin imputar ceros.
