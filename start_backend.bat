@echo off
title Çocuk Çizimi Analiz Backend Sunucusu
echo Çocuk Çizimi Analiz API sunucusu başlatılıyor...
cd /d "%~dp0backend"
uvicorn api:app --host 0.0.0.0 --port 5000 --reload
pause
