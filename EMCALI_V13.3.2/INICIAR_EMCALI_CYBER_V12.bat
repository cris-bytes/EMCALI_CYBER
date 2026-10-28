@echo off
setlocal
TITLE EMCALI Cyber 2.0 Hibrido V12 - APROBADA ESTABLE
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [V12] Creando entorno Python...
  py -3.12 -m venv .venv 2>nul || py -3.11 -m venv .venv
  if errorlevel 1 (
    echo ERROR: Instale Python 3.12 o 3.11 y vuelva a ejecutar.
    pause
    exit /b 1
  )
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
start "" http://127.0.0.1:8501
python -m streamlit run app.py
pause
