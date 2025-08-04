@echo off
echo.
echo ========================================
echo 🚀 INSTALADOR AUTOMATICO DE SCCA
echo ========================================
echo.

echo 📦 Instalando FFmpeg...
winget install Gyan.FFmpeg
if %errorlevel% neq 0 (
    echo ❌ Error instalando FFmpeg
    pause
    exit /b 1
)

echo.
echo 🐋 Instalando Ollama...
winget install Ollama.Ollama
if %errorlevel% neq 0 (
    echo ❌ Error instalando Ollama
    pause
    exit /b 1
)

echo.
echo 🐍 Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Error creando entorno virtual
    pause
    exit /b 1
)

echo.
echo 📋 Activando entorno virtual...
call venv\Scripts\activate

echo.
echo 📦 Instalando dependencias Python...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)

echo.
echo ⏳ Esperando a que Ollama esté disponible...
timeout /t 5 /nobreak > nul

echo.
echo 🤖 Configurando Ollama...
python setup_ollama.py
if %errorlevel% neq 0 (
    echo ❌ Error configurando Ollama
    pause
    exit /b 1
)

echo.
echo 🧪 Verificando sistema...
python test_system.py

echo.
echo ========================================
echo ✅ ¡INSTALACION COMPLETADA!
echo ========================================
echo.
echo 🌐 Para iniciar SCCA, ejecuta:
echo    uvicorn backend.main_app:app --host 127.0.0.1 --port 8000 --reload
echo.
echo 📖 Luego abre: http://127.0.0.1:8000
echo.
pause