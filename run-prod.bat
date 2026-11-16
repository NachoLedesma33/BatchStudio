@echo off
title PDF Batch Studio - Produccion
cd /d %~dp0frontend
if not exist dist\index.html (
  echo Compilando frontend...
  call npm run build
  if errorlevel 1 exit /b 1
)
cd /d %~dp0backend
python -m app.desktop
