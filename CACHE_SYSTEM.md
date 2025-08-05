# Sistema de Caché de Análisis - SCCA

## Descripción

El sistema de caché de análisis permite almacenar los resultados del análisis de clips con IA para evitar repetir el proceso más lento del pipeline. Esto mejora significativamente la eficiencia cuando se procesan videos con los mismos parámetros.

## Características

### ✅ Funcionalidades Implementadas

- **Caché Automático**: Los resultados del análisis se guardan automáticamente después de cada procesamiento exitoso
- **Detección Inteligente**: El sistema genera claves únicas basadas en:
  - Hash del archivo de video
  - Contenido de la transcripción
  - Parámetros de análisis (contexto, temas, perfil)
- **Carga Rápida**: Si existe un caché válido, se carga instantáneamente sin ejecutar el LLM
- **Gestión de Archivos**: Los archivos de caché se almacenan en formato JSON legible
- **Limpieza Automática**: Eliminación automática de archivos de caché antiguos (30 días por defecto)

### 🔧 API Endpoints

#### Obtener información del caché
```http
GET /api/cache/analysis
```

Respuesta:
```json
{
  "cache_enabled": true,
  "cache_directory": "output/analysis_cache",
  "total_files": 5,
  "total_size_mb": 2.45,
  "cache_files": [
    {
      "cache_key": "f8f41776b2303787488d89166856df05",
      "timestamp": "2025-08-05T09:40:04.882058",
      "video_path": "output/videos/video.mp4",
      "clips_count": 3,
      "analysis_params": {
        "context": "Video de prueba",
        "topics": "tecnología, programación",
        "profile": "Clips para Redes Sociales"
      },
      "file_size_kb": 1.37,
      "filename": "f8f41776b2303787488d89166856df05_analysis.json"
    }
  ]
}
```

#### Limpiar todo el caché
```http
DELETE /api/cache/analysis
```

#### Eliminar caché específico
```http
DELETE /api/cache/analysis/{cache_key}
```

## Estructura de Archivos

### Directorio de Caché
```
output/
└── analysis_cache/
    ├── f8f41776b2303787488d89166856df05_analysis.json
    ├── a1b2c3d4e5f6789012345678901234567_analysis.json
    └── ...
```

### Formato del Archivo de Caché
```json
{
  "cache_key": "f8f41776b2303787488d89166856df05",
  "job_id": "test_job_123",
  "timestamp": "2025-08-05T09:40:04.882058",
  "video_path": "output/videos/video.mp4",
  "analysis_params": {
    "context": "Descripción del video",
    "topics": "tema1, tema2, tema3",
    "profile": "Clips para Redes Sociales"
  },
  "clips_count": 3,
  "clips": [
    {
      "title": "Título del Clip",
      "description": "Descripción del clip",
      "start_time": 0.0,
      "end_time": 30.0,
      "duration": 30.0,
      "relevance_score": 0.9,
      "topics": ["tema1"],
      "segment_id": 1
    }
  ]
}
```

## Algoritmo de Generación de Claves

1. **Hash del Video**: Se calcula el MD5 del archivo de video
2. **Parámetros de Análisis**: Se concatenan contexto, temas, perfil y longitud de transcripción
3. **Clave Final**: MD5 de la concatenación: `{video_hash}|{context}|{topics}|{profile}|{transcription_length}`

## Beneficios de Rendimiento

### Antes del Caché
- **Transcripción**: ~30-60 segundos
- **Análisis con IA**: ~60-120 segundos (parte más lenta)
- **Corte de Clips**: ~10-30 segundos
- **Total**: ~100-210 segundos

### Con Caché (hit)
- **Transcripción**: ~30-60 segundos
- **Análisis con IA**: ~0.1 segundos (carga desde caché)
- **Corte de Clips**: ~10-30 segundos
- **Total**: ~40-90 segundos

**Mejora**: Reducción del 50-60% en tiempo de procesamiento

## Casos de Uso

### ✅ Cuándo se Utiliza el Caché
- Mismo video con mismos parámetros de análisis
- Re-procesamiento después de errores en el corte
- Ajustes en la configuración de corte (sin cambiar análisis)
- Pruebas y desarrollo

### ❌ Cuándo NO se Utiliza el Caché
- Video diferente
- Cambios en contexto, temas o perfil
- Transcripción modificada
- Archivo de video modificado

## Configuración

### Parámetros Configurables
- **Edad máxima del caché**: 30 días (configurable en `_cleanup_old_cache`)
- **Directorio de caché**: `output/analysis_cache`
- **Formato de archivos**: JSON con codificación UTF-8

### Mantenimiento
- **Limpieza automática**: Se ejecuta después de cada guardado de caché
- **Limpieza manual**: Disponible via API endpoints
- **Monitoreo**: Información detallada via endpoint GET

## Pruebas

Para probar el sistema de caché:

```bash
python test_analysis_cache.py
```

Este script:
1. Genera una clave de caché
2. Verifica si existe caché previo
3. Crea caché de prueba si no existe
4. Verifica la carga desde caché
5. Muestra información del directorio de caché

## Logs

El sistema registra eventos importantes:

```
📋 CACHÉ UTILIZADO - 3 clips cargados desde caché
Análisis guardado en caché: output/analysis_cache/f8f41776b2303787488d89166856df05_analysis.json (3 clips)
Análisis cargado desde caché: 3 clips (creado: 2025-08-05T09:40:04.882058)
```

## Seguridad

- Los archivos de caché no contienen información sensible
- Las claves de caché son hashes no reversibles
- Los archivos se almacenan localmente en el servidor
- Limpieza automática previene acumulación excesiva