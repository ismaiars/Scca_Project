@echo off
echo Agregando Ollama al PATH del sistema...

:: Obtener la ruta de Ollama
set OLLAMA_PATH=%LOCALAPPDATA%\Programs\Ollama

:: Verificar si Ollama existe
if not exist "%OLLAMA_PATH%\ollama.exe" (
    echo Error: Ollama no encontrado en %OLLAMA_PATH%
    echo Por favor, instala Ollama desde https://ollama.com/download/windows
    pause
    exit /b 1
)

:: Agregar al PATH del usuario actual
echo Agregando %OLLAMA_PATH% al PATH del usuario...
setx PATH "%PATH%;%OLLAMA_PATH%"

if %errorlevel% equ 0 (
    echo ✅ Ollama agregado al PATH exitosamente
    echo ⚠️  IMPORTANTE: Cierra y reabre todas las ventanas de terminal/PowerShell
    echo    para que los cambios surtan efecto.
    echo.
    echo 🔄 Después de reiniciar la terminal, ejecuta:
    echo    ollama list
    echo.
) else (
    echo ❌ Error al agregar Ollama al PATH
)

pause