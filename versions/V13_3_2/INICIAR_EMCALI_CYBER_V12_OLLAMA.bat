@echo off
setlocal
TITLE EMCALI Cyber 2.0 Hibrido V12 + Ollama - APROBADA ESTABLE
cd /d "%~dp0"
where ollama >nul 2>nul
if errorlevel 1 (
  echo ADVERTENCIA: Ollama no esta disponible en PATH.
) else (
  start "Ollama" /min ollama serve
  timeout /t 3 /nobreak >nul
)
call "%~dp0INICIAR_EMCALI_CYBER_V12.bat"
