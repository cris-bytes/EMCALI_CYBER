@echo off
setlocal
TITLE EMCALI Cyber 2.0 Hibrido V12 Portable - HP Victus RTX 4050
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Runtime portable .venv no encontrado.
  pause
  exit /b 1
)
start "Ollama" /min ollama serve
start "" http://127.0.0.1:8501
".venv\Scripts\python.exe" -m streamlit run app.py
pause
