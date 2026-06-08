@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo Aplicando Parche V6 Enterprise LLM para EMCALI Cyber 2.0...
python parche_v6_enterprise_llm.py
if errorlevel 1 (
  echo.
  echo ERROR aplicando el parche. Verifique que esta carpeta contiene app.py y que Python esta instalado.
  pause
  exit /b 1
)
echo.
echo Parche aplicado. Cierre y reinicie Streamlit: streamlit run app.py
pause
