@echo off
rem Collecte quotidienne Ligue 1 CI, lancée par la tâche planifiée Windows
rem « Ligue1CI - collecte quotidienne ». Journal détaillé : logs\pipeline.log
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs
echo ===== %date% %time% ===== >> logs\collecte_quotidienne.log
"C:\Python314\python.exe" -m src.collecte.run >> logs\collecte_quotidienne.log 2>&1
echo code de sortie : %errorlevel% >> logs\collecte_quotidienne.log
