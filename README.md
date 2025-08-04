# Sistema de Creación de Contenido Automatizado (SCCA)

Una aplicación web local que utiliza IA para extraer clips temáticos de videos largos de forma automatizada.

## 🎯 Características

- **Transcripción automática** con Whisper.cpp optimizado para CPU
- **Análisis inteligente** usando modelos LLM locales (Mistral-7B)
- **Corte automático** de clips con FFmpeg
- **Interfaz web moderna** con progreso en tiempo real
- **Perfiles personalizables** para diferentes tipos de contenido
- **Optimizado para CPU** sin necesidad de GPU dedicada

## 🏗️ Arquitectura

```
scca_project/
├── backend/                 # Servidor FastAPI
│   ├── main_app.py         # Punto de entrada
│   ├── api.py              # Endpoints HTTP/WebSocket
│   ├── core/               # Lógica principal
│   │   ├── transcriber.py  # Whisper.cpp
│   │   ├── analyzer.py     # LLM local
│   │   ├── cutter.py       # FFmpeg
│   │   └── job_manager.py  # Gestión de trabajos
│   └── models/             # Modelos Pydantic
├── frontend/               # Interfaz web
│   ├── templates/          # HTML
│   └── static/            # CSS/JS
└── requirements.txt        # Dependencias Python
```

## 📋 Requisitos del Sistema

### Software Requerido

1. **Python 3.10+**
2. **FFmpeg** - Para procesamiento de video
3. **whisper.cpp** - Para transcripción optimizada
4. **Servidor LLM local** (LM Studio, Ollama, etc.)

### Modelos de IA

1. **Whisper**: `ggml-medium.bin` (modelo por defecto)
2. **LLM**: `Mistral-7B-Instruct-v0.2` (cuantización Q4_K_M)

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd scca_project
```

### 2. Crear entorno virtual
```bash
python -m venv venv
# Windows
venv\\Scripts\\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias Python
```bash
pip install -r requirements.txt
```

### 4. Instalar FFmpeg

#### Windows:
1. Descargar desde https://ffmpeg.org/download.html
2. Extraer y agregar al PATH del sistema
3. Verificar: `ffmpeg -version`

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install ffmpeg
```

#### macOS:
```bash
brew install ffmpeg
```

### 5. Instalar whisper.cpp

#### Opción A: Compilar desde fuente
```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
```

#### Opción B: Usar binarios precompilados
Descargar desde las releases de GitHub y agregar al PATH.

### 6. Descargar modelos

#### Modelo Whisper:
```bash
# Crear directorio de modelos
mkdir models
cd models

# Descargar modelo medium (recomendado)
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
```

#### Modelo LLM:
1. Instalar LM Studio desde https://lmstudio.ai/
2. Descargar `Mistral-7B-Instruct-v0.2` (Q4_K_M)
3. Iniciar servidor local en puerto 1234

### 7. Configurar servidor LLM

#### LM Studio:
1. Abrir LM Studio
2. Cargar el modelo Mistral-7B-Instruct-v0.2
3. Ir a "Local Server" y iniciar en puerto 1234
4. Verificar que esté disponible en `http://localhost:1234`

#### Ollama (alternativa):
```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo
ollama pull mistral:7b-instruct

# Iniciar servidor
ollama serve
```

## 🎮 Uso

### 1. Iniciar el servidor
```bash
# Desde el directorio raíz del proyecto
python -m backend.main_app

# O usando uvicorn directamente
uvicorn backend.main_app:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Acceder a la aplicación
Abrir navegador en: http://localhost:8000

### 3. Usar la interfaz

1. **Subir video**: Seleccionar archivo de video (máx. 2GB)
2. **Configurar contexto**: Describir el contenido del video
3. **Definir temas**: Especificar temas de interés separados por comas
4. **Seleccionar perfil**:
   - **Clips para Redes Sociales**: 15-60 segundos, dinámico
   - **Cápsulas Educativas**: 2-5 minutos, educativo
   - **Archivo de Referencia**: 1-10 minutos, informativo
5. **Iniciar proceso**: El progreso se mostrará en tiempo real
6. **Descargar clips**: Una vez completado, descargar clips individuales o todos

## 🔧 Configuración Avanzada

### Variables de entorno (.env)
```bash
# URL del servidor LLM
LLM_API_URL=http://localhost:1234/v1/chat/completions

# Ruta del modelo Whisper
WHISPER_MODEL_PATH=models/ggml-medium.bin

# Directorio de salida
OUTPUT_DIR=output

# Configuración del servidor
HOST=127.0.0.1
PORT=8000
```

### Personalizar modelos
```python
# En backend/core/transcriber.py
transcriber = WhisperTranscriber(model_path="ruta/a/tu/modelo.bin")

# En backend/core/analyzer.py
analyzer = LLMAnalyzer(api_url="http://tu-servidor-llm:puerto/v1/chat/completions")
```

## 🐛 Solución de Problemas

### Error: "Whisper model not found"
- Verificar que el modelo esté en `models/ggml-medium.bin`
- Descargar el modelo desde HuggingFace

### Error: "LLM connection failed"
- Verificar que el servidor LLM esté ejecutándose
- Comprobar la URL en la configuración
- Probar conexión: `curl http://localhost:1234/v1/models`

### Error: "FFmpeg not found"
- Instalar FFmpeg y agregarlo al PATH
- Verificar instalación: `ffmpeg -version`

### Clips no se generan
- Verificar que la transcripción sea correcta
- Ajustar los temas de interés para ser más específicos
- Revisar logs del servidor para errores

## 📊 Rendimiento

### Tiempos estimados (CPU Intel i7):
- **Transcripción**: ~0.3x velocidad del video
- **Análisis**: ~30-60 segundos por hora de video
- **Corte**: ~0.1x velocidad del video

### Optimizaciones:
- Usar modelo Whisper `small` para mayor velocidad
- Cuantización Q4_K_M para el LLM (balance velocidad/calidad)
- Procesar videos en resolución 720p para mayor velocidad

## 🔄 Actualizaciones

### Actualizar dependencias:
```bash
pip install -r requirements.txt --upgrade
```

### Actualizar modelos:
```bash
# Whisper
cd models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large.bin

# LLM - actualizar desde LM Studio o Ollama
```

## 🤝 Contribuir

1. Fork del repositorio
2. Crear rama para feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

Para reportar bugs o solicitar funcionalidades:
1. Crear issue en GitHub
2. Incluir logs del servidor
3. Especificar configuración del sistema
4. Proporcionar pasos para reproducir el problema

## 🔮 Roadmap

### Versión 1.1
- [ ] Validación automática de clips
- [ ] Perfiles personalizados guardados
- [ ] Titulación automática con IA
- [ ] Branding personalizable

### Versión 1.2
- [ ] Soporte para múltiples idiomas
- [ ] Integración con APIs de redes sociales
- [ ] Análisis de sentimientos
- [ ] Métricas de engagement predichas

---

**SCCA v1.0** - Sistema de Creación de Contenido Automatizado