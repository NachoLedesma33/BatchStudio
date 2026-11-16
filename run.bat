@echo off
title PDF Batch Studio - Desarrollo
echo Levantando backend en http://127.0.0.1:8765 ...
start "PDFBS Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload"
timeout /t 3 /nobreak >nul
echo Levantando frontend en http://localhost:5173 ...
start "PDFBS Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo.
echo Backend:  http://127.0.0.1:8765
echo Frontend: http://localhost:5173
echo API docs: http://127.0.0.1:8765/docs
