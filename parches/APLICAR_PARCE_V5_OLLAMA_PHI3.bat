@echo off
chcp 65001 >nul
title Parche V5 Ollama Phi3 - EMCALI Cyber 2.0
echo ==================================================
echo   PARCHE V5 OLLAMA PHI3 - EMCALI Cyber 2.0
echo ==================================================
echo.
echo IMPORTANTE: ejecute este BAT dentro de la carpeta raiz de la app.
echo Ejemplos:
echo   C:\EMCALI_Cyber20_Hibrido_App
echo   C:\emcali-cyber-app
echo.
if not exist app.py (
  echo ADVERTENCIA: no se encuentra app.py en esta carpeta.
  echo Si esta no es la raiz de la app, cierre esta ventana y mueva este parche a la carpeta correcta.
  echo.
)
python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python no esta disponible en PATH.
  echo Abra CMD en el entorno virtual de la app o instale Python.
  pause
  exit /b 1
)
python parche_v5_ollama_phi3.py
echo.
echo Si no hubo errores, reinicie la aplicacion con:
echo   streamlit run app.py
echo.
pause
