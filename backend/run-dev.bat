@echo off
cd /d %~dp0
set PDFBS_DEV_NO_TOKEN=1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
