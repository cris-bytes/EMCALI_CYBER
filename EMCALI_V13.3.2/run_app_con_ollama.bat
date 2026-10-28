@echo off
TITLE EMCALI Cyber 2.0 Híbrido + Ollama
cd /d "%~dp0"
start "" ollama serve
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
start http://127.0.0.1:8501
python -m streamlit run app.py
pause
