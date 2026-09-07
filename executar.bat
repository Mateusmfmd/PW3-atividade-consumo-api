@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Instalando/verificando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Erro ao instalar as dependencias.
    pause
    exit /b 1
)
echo.
echo Iniciando o Catalogo de Gatos...
python app.py
pause
