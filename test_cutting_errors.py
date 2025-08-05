import asyncio
import logging
import ffmpeg
from pathlib import Path
from backend.core.cutter import VideoCutter

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_problematic_clips():
    """
    Prueba clips con datos problemáticos para identificar la causa de los errores
    """
    logger.info("=== PRUEBA DE CLIPS PROBLEMÁTICOS ===")
    
    # Buscar el video más reciente
    videos_dir = Path("output/videos")
    video_files = list(videos_dir.glob("*.mp4"))
    if not video_files:
        logger.error("No se encontraron videos")
        return
    
    video_path = str(video_files[0])
    logger.info(f"Usando video: {video_path}")
    
    # Obtener información del video
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        logger.info(f"Duración del video: {duration} segundos")
    except Exception as e:
        logger.error(f"Error obteniendo duración: {e}")
        return
    
    # Clips de prueba con diferentes problemas potenciales
    test_clips = [
        {
            "title": "Clip válido normal",
            "start_time": 10.0,
            "end_time": 20.0,
            "duration": 10.0,
            "description": "Clip normal que debería funcionar",
            "confidence": 0.8
        },
        {
            "title": "Clip con decimales",
            "start_time": 30.5,
            "end_time": 45.7,
            "duration": 15.2,
            "description": "Clip con tiempos decimales",
            "confidence": 0.7
        },
        {
            "title": "Clip cerca del final",
            "start_time": duration - 30,
            "end_time": duration - 10,
            "duration": 20.0,
            "description": "Clip cerca del final del video",
            "confidence": 0.6
        },
        {
            "title": "Clip que excede duración",
            "start_time": duration - 5,
            "end_time": duration + 10,  # Excede la duración del video
            "duration": 15.0,
            "description": "Clip que excede la duración del video",
            "confidence": 0.5
        },
        {
            "title": "Clip con tiempo negativo",
            "start_time": 100.0,
            "end_time": 95.0,  # Tiempo de fin menor que inicio
            "duration": -5.0,
            "description": "Clip con datos inconsistentes",
            "confidence": 0.4
        },
        {
            "title": "Clip muy largo",
            "start_time": 0.0,
            "end_time": min(600.0, duration),  # 10 minutos o duración total
            "duration": min(600.0, duration),
            "description": "Clip muy largo",
            "confidence": 0.3
        }
    ]
    
    logger.info(f"Probando {len(test_clips)} clips con diferentes problemas")
    
    # Crear instancia del cortador
    cutter = VideoCutter("output")
    
    # Función de callback para progreso
    async def progress_callback(status, progress, message):
        logger.info(f"Progreso: {status} - {progress:.2f} - {message}")
    
    # Probar cada clip individualmente
    for i, clip in enumerate(test_clips):
        logger.info(f"\n--- Probando clip {i+1}: {clip['title']} ---")
        logger.info(f"Start: {clip['start_time']}, End: {clip['end_time']}, Duration: {clip['duration']}")
        
        try:
            # Probar cortado individual
            result = await cutter._cut_single_clip(video_path, clip, i+1)
            logger.info(f"✅ Clip {i+1} cortado exitosamente: {result}")
            
            # Verificar que el archivo existe
            if result.exists():
                size = result.stat().st_size
                logger.info(f"   Archivo creado: {size} bytes")
            else:
                logger.error(f"   ❌ Archivo no existe después del cortado")
                
        except Exception as e:
            logger.error(f"❌ Error cortando clip {i+1}: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    # Ahora probar todos los clips válidos juntos
    logger.info("\n=== PROBANDO CLIPS VÁLIDOS EN LOTE ===")
    valid_clips = [clip for clip in test_clips if clip['start_time'] < clip['end_time'] and clip['end_time'] <= duration]
    logger.info(f"Clips válidos: {len(valid_clips)}")
    
    try:
        results = await cutter.cut_clips(video_path, valid_clips, progress_callback)
        logger.info(f"✅ Cortado en lote exitoso: {len(results)} clips generados")
        
        for result in results:
            logger.info(f"   - {result['title']}: {result['file_path']}")
            
    except Exception as e:
        logger.error(f"❌ Error en cortado en lote: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def main():
    logger.info("Iniciando prueba de clips problemáticos...")
    await test_problematic_clips()
    logger.info("Prueba completada.")

if __name__ == "__main__":
    asyncio.run(main())