@echo off
setlocal

rem SurroSim desktop launcher (Windows).
rem One click: builds the frontend and desktop dependencies on first run,
rem then opens the native window. Close the window to stop the app.

set "ROOT=%~dp0"
set "WEB=%ROOT%apps\web"
set "DESKTOP=%ROOT%apps\desktop"
set "ELECTRON=%DESKTOP%\node_modules\electron\dist\electron.exe"

if not exist "%WEB%\node_modules" (
  echo [SurroSim] Installing web dependencies ^(first run only^)...
  pushd "%WEB%"
  call npm install
  if errorlevel 1 (
    popd
    echo [SurroSim] npm install failed.
    pause
    exit /b 1
  )
  popd
)

if not exist "%WEB%\dist\index.html" (
  echo [SurroSim] Building the web app...
  pushd "%WEB%"
  call npm run build
  if errorlevel 1 (
    popd
    echo [SurroSim] Frontend build failed.
    pause
    exit /b 1
  )
  popd
)

if not exist "%ELECTRON%" (
  echo [SurroSim] Installing desktop dependencies ^(first run only^)...
  pushd "%DESKTOP%"
  call npm install
  if errorlevel 1 (
    popd
    echo [SurroSim] npm install failed.
    pause
    exit /b 1
  )
  rem npm script guards can skip Electron's binary download; force it if needed.
  if not exist "%ELECTRON%" call node node_modules\electron\install.js
  popd
)

echo [SurroSim] Starting desktop app...
start "" "%ELECTRON%" "%DESKTOP%"
exit /b 0
