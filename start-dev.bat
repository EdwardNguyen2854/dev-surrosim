@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=python"
set "PYTHONPATH=%ROOT%src;%PYTHONPATH%"
if exist "%ROOT%.venv\Scripts\python.exe" set "PYTHON=%ROOT%.venv\Scripts\python.exe"

start "SurroSim API" /D "%ROOT%" cmd /k ""%PYTHON%" -m surrosim serve --port 8003"
start "SurroSim Web" /D "%ROOT%apps\web" cmd /k "npm run dev"

echo API: http://localhost:8003
echo Web: http://localhost:5173
