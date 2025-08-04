#!/bin/bash

echo ""
echo "========================================"
echo "🚀 INSTALADOR AUTOMATICO DE SCCA"
echo "========================================"
echo ""

# Detectar sistema operativo
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
else
    echo "❌ Sistema operativo no soportado"
    exit 1
fi

echo "📦 Instalando FFmpeg..."
if [[ "$OS" == "linux" ]]; then
    sudo apt update && sudo apt install -y ffmpeg
elif [[ "$OS" == "mac" ]]; then
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew no está instalado. Instálalo desde https://brew.sh/"
        exit 1
    fi
    brew install ffmpeg
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "❌ Error instalando FFmpeg"
    exit 1
fi

echo ""
echo "🐋 Instalando Ollama..."
curl -fsSL https://ollama.ai/install.sh | sh

if ! command -v ollama &> /dev/null; then
    echo "❌ Error instalando Ollama"
    exit 1
fi

echo ""
echo "🐍 Creando entorno virtual..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "❌ Error creando entorno virtual"
    exit 1
fi

echo ""
echo "📋 Activando entorno virtual..."
source venv/bin/activate

echo ""
echo "📦 Instalando dependencias Python..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias"
    exit 1
fi

echo ""
echo "⏳ Esperando a que Ollama esté disponible..."
sleep 5

echo ""
echo "🤖 Configurando Ollama..."
python setup_ollama.py

if [ $? -ne 0 ]; then
    echo "❌ Error configurando Ollama"
    exit 1
fi

echo ""
echo "🧪 Verificando sistema..."
python test_system.py

echo ""
echo "========================================"
echo "✅ ¡INSTALACION COMPLETADA!"
echo "========================================"
echo ""
echo "🌐 Para iniciar SCCA, ejecuta:"
echo "   source venv/bin/activate"
echo "   uvicorn backend.main_app:app --host 127.0.0.1 --port 8000 --reload"
echo ""
echo "📖 Luego abre: http://127.0.0.1:8000"
echo ""