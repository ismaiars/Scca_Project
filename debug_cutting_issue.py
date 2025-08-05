import asyncio
import logging
import json
from pathlib import Path
from backend.core.cutter import VideoCutter
from backend.core.analyzer import LLMAnalyzer
from backend.core.transcriber import WhisperTranscriber

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_cutting_process():
    """
    Reproduce el proceso completo para identificar el problema de cortado
    """
    logger.info("=== DEPURACIÓN DEL PROCESO DE CORTADO ===")
    
    # Buscar el video más reciente
    videos_dir = Path("output/videos")
    if not videos_dir.exists():
        logger.error("No existe el directorio output/videos")
        return
    
    video_files = list(videos_dir.glob("*.mp4"))
    if not video_files:
        logger.error("No se encontraron videos en output/videos")
        return
    
    video_path = str(video_files[0])
    logger.info(f"Usando video: {video_path}")
    
    # Crear clips de prueba con datos problemáticos típicos
    test_clips = [
        {
            "title": "Clip de prueba 1",
            "start_time": 0.0,
            "end_time": 10.0,
            "duration": 10.0,
            "description": "Primer clip de prueba",
            "confidence": 0.8
        },
        {
            "title": "Clip de prueba 2",
            "start_time": 30.5,
            "end_time": 45.2,
            "duration": 14.7,
            "description": "Segundo clip de prueba",
            "confidence": 0.7
        },
        {
            "title": "Clip con tiempo inválido",
            "start_time": 2100.0,  # Tiempo mayor que la duración del video
            "end_time": 2110.0,
            "duration": 10.0,
            "description": "Clip que debería fallar",
            "confidence": 0.6
        },
        {
            "title": "Clip con duración negativa",
            "start_time": 100.0,
            "end_time": 95.0,  # Tiempo de fin menor que inicio
            "duration": -5.0,
            "description": "Clip con datos inconsistentes",
            "confidence": 0.5
        }
    ]
    
    logger.info(f"Probando cortado con {len(test_clips)} clips de prueba")
    
    # Crear instancia del cortador
    cutter = VideoCutter("output")
    
    # Función de callback para progreso
    async def progress_callback(status, progress, message):
        logger.info(f"Progreso: {status} - {progress:.2f} - {message}")
    
    try:
        # Intentar cortar los clips
        results = await cutter.cut_clips(video_path, test_clips, progress_callback)
        
        logger.info(f"Resultado: {len(results)} clips cortados exitosamente")
        
        for i, result in enumerate(results):
            logger.info(f"Clip {i+1}: {result['title']} - {result['file_path']}")
            
    except Exception as e:
        logger.error(f"Error durante el cortado: {str(e)}")
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")

async def analyze_video_and_cut():
    """
    Reproduce el proceso completo de análisis y cortado
    """
    logger.info("=== PROCESO COMPLETO: ANÁLISIS + CORTADO ===")
    
    # Buscar el video más reciente
    videos_dir = Path("output/videos")
    video_files = list(videos_dir.glob("*.mp4"))
    video_path = str(video_files[0])
    
    # Buscar transcripción existente
    transcriptions_dir = Path("output/transcriptions")
    txt_files = list(transcriptions_dir.glob("*.txt"))
    
    if not txt_files:
        logger.error("No se encontró transcripción existente")
        return
    
    # Leer la transcripción más reciente
    latest_txt = max(txt_files, key=lambda x: x.stat().st_mtime)
    with open(latest_txt, 'r', encoding='utf-8') as f:
        transcription = f.read()
    
    logger.info(f"Usando transcripción: {latest_txt}")
    logger.info(f"Longitud de transcripción: {len(transcription)} caracteres")
    
    # Crear analizador
    analyzer = LLMAnalyzer()
    
    # Función de callback para progreso
    async def progress_callback(status, progress, message):
        logger.info(f"Análisis: {status} - {progress:.2f} - {message}")
    
    try:
        # Analizar transcripción para encontrar clips
        clips = await analyzer.analyze_transcription(
            context="Contenido educativo",
            topics="Tecnología, programación",
            profile="Desarrolladores",
            transcription=transcription,
            progress_callback=progress_callback
        )
        
        logger.info(f"Análisis completado: {len(clips)} clips encontrados")
        
        # Mostrar información de los clips encontrados
        for i, clip in enumerate(clips):
            logger.info(f"Clip {i+1}: {clip['title']}")
            logger.info(f"  Tiempo: {clip['start_time']:.2f}s - {clip['end_time']:.2f}s")
            logger.info(f"  Duración: {clip['duration']:.2f}s")
            logger.info(f"  Confianza: {clip.get('confidence', 0):.2f}")
        
        # Ahora intentar cortar los clips reales
        if clips:
            logger.info("Iniciando cortado de clips reales...")
            cutter = VideoCutter("output")
            
            async def cutting_callback(status, progress, message):
                logger.info(f"Cortado: {status} - {progress:.2f} - {message}")
            
            results = await cutter.cut_clips(video_path, clips, cutting_callback)
            logger.info(f"Cortado completado: {len(results)} clips generados")
        
    except Exception as e:
        logger.error(f"Error en proceso completo: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def main():
    logger.info("Iniciando depuración del problema de cortado...")
    
    # Primero probar con clips de prueba
    await debug_cutting_process()
    
    print("\n" + "="*50 + "\n")
    
    # Luego probar el proceso completo
    await analyze_video_and_cut()

if __name__ == "__main__":
    asyncio.run(main())