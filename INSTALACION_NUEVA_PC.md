# 🖥️ Guía de Instalación en Nueva Computadora

Esta guía te ayudará a instalar y configurar SCCA en una nueva computadora desde cero.

## 📋 **Requisitos Mínimos**
- **RAM**: 6 GB mínimo (8 GB recomendado)
- **Espacio**: 10 GB libres
- **SO**: Windows 10/11, Linux, macOS
- **Internet**: Para descargar dependencias

## 🚀 **Instalación Paso a Paso**

### **1. Instalar Python 3.10+**
```bash
# Verificar si ya tienes Python
python --version

# Si no tienes Python, descargar desde:
# https://www.python.org/downloads/
```

### **2. Clonar el repositorio**
```bash
git clone <tu-repositorio-url>
cd scca_project
```

### **3. Crear entorno virtual**
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### **4. Instalar dependencias Python**
```bash
pip install -r requirements.txt
```

### **5. Instalar FFmpeg**

#### **Windows (Recomendado - WinGet):**
```bash
winget install Gyan.FFmpeg
```

#### **Windows (Manual):**
1. Ir a https://ffmpeg.org/download.html
2. Descargar versión para Windows
3. Extraer y agregar al PATH

#### **Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

#### **macOS:**
```bash
brew install ffmpeg
```

### **6. Instalar y configurar Ollama**

#### **Windows:**
1. Descargar desde: https://ollama.com/download/windows
2. Instalar `OllamaSetup.exe`
3. Reiniciar terminal

#### **Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### **macOS:**
```bash
brew install ollama
```

### **7. Configurar Ollama automáticamente**
```bash
# Ejecutar script de configuración
python setup_ollama.py
```

Este script automáticamente:
- ✅ Verifica instalación de Ollama
- ✅ Inicia el servidor Ollama
- ✅ Descarga modelo Mistral 7B (~4.4 GB)
- ✅ Prueba la conexión

### **8. Verificar instalación**
```bash
# Probar todo el sistema
python test_system.py
```

Deberías ver:
```
✅ Whisper: Modelo cargado correctamente
✅ LLM: Conexión exitosa
✅ FFmpeg: Disponible
✅ Servidor: Funcionando correctamente
```

### **9. Iniciar la aplicación**
```bash
# Iniciar servidor SCCA
uvicorn backend.main_app:app --host 127.0.0.1 --port 8000 --reload
```

### **10. Acceder a la aplicación**
Abrir navegador en: **http://127.0.0.1:8000**

## ⚡ **Instalación Rápida (Script Automático)**

Si quieres automatizar todo el proceso, puedes crear este script:

### **Windows (install.bat):**
```batch
@echo off
echo 🚀 Instalando SCCA...

echo 📦 Instalando FFmpeg...
winget install Gyan.FFmpeg

echo 🐋 Instalando Ollama...
winget install Ollama.Ollama

echo 🐍 Creando entorno virtual...
python -m venv venv
call venv\Scripts\activate

echo 📋 Instalando dependencias...
pip install -r requirements.txt

echo 🤖 Configurando Ollama...
python setup_ollama.py

echo 🧪 Verificando sistema...
python test_system.py

echo ✅ ¡Instalación completada!
echo 🌐 Inicia el servidor con: uvicorn backend.main_app:app --host 127.0.0.1 --port 8000 --reload
pause
```

### **Linux/Mac (install.sh):**
```bash
#!/bin/bash
echo "🚀 Instalando SCCA..."

# Instalar FFmpeg
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt update && sudo apt install -y ffmpeg
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install ffmpeg
fi

# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Python setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar Ollama
python setup_ollama.py

# Verificar
python test_system.py

echo "✅ ¡Instalación completada!"
echo "🌐 Inicia el servidor con: uvicorn backend.main_app:app --host 127.0.0.1 --port 8000 --reload"
```

## 🔧 **Configuración Opcional**

### **Variables de entorno (.env):**
El proyecto incluye un archivo `.env` preconfigurado, pero puedes personalizarlo:

```bash
# URL del servidor LLM (Ollama)
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL_NAME=mistral:7b-instruct

# Configuración de Whisper
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=cpu

# Directorios
OUTPUT_DIR=output
MODELS_DIR=models

# Servidor
HOST=127.0.0.1
PORT=8000
DEBUG=false
```

## 🐛 **Solución de Problemas Comunes**

### **Error: "ollama no se reconoce como comando"**
```bash
# Reiniciar terminal después de instalar Ollama
# O agregar manualmente al PATH:
# Windows: C:\Users\%USERNAME%\AppData\Local\Programs\Ollama
```

### **Error: "No se puede conectar al LLM"**
```bash
# Verificar que Ollama esté ejecutándose
ollama list

# Si no está ejecutándose, iniciarlo
ollama serve
```

### **Error: "FFmpeg not found"**
```bash
# Verificar instalación
ffmpeg -version

# Si no está instalado, usar WinGet (Windows)
winget install Gyan.FFmpeg
```

### **Error: "Insufficient memory"**
- Cerrar otras aplicaciones
- El modelo Mistral 7B necesita ~4-6 GB RAM
- Considerar usar un modelo más pequeño

## 📊 **Uso de Recursos**

| Componente | RAM | Disco | CPU |
|------------|-----|-------|-----|
| **Ollama + Mistral** | 4-6 GB | 4.4 GB | Medio |
| **Whisper** | 1-2 GB | 150 MB | Alto |
| **FFmpeg** | 200 MB | 150 MB | Alto |
| **Servidor Web** | 100 MB | 50 MB | Bajo |
| **Total** | **6-8 GB** | **5 GB** | **Variable** |

## 🎯 **Próximos Pasos**

1. **✅ Verificar** que todo funcione con `python test_system.py`
2. **🚀 Iniciar** servidor con `uvicorn backend.main_app:app --host 127.0.0.1 --port 8000 --reload`
3. **🌐 Abrir** http://127.0.0.1:8000 en el navegador
4. **📹 Subir** tu primer video y generar clips

## 📞 **Soporte**

Si tienes problemas:
1. Revisa los logs en la terminal
2. Ejecuta `python test_system.py` para diagnosticar
3. Verifica que todos los servicios estén ejecutándose
4. Consulta el README.md principal

**¡Disfruta creando clips automáticamente con SCCA!** 🎬✨