import asyncio
import logging
import time
from pathlib import Path
from backend.core.cutter import VideoCutter

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_clip_creation():
    """
    Verifica si los clips se están creando y persistiendo correctamente
    """
    logger.info("=== VERIFICACIÓN DE CREACIÓN DE CLIPS ===")
    
    # Buscar el video
    videos_dir = Path("output/videos")
    video_files = list(videos_dir.glob("*.mp4"))
    if not video_files:
        logger.error("No se encontraron videos")
        return
    
    video_path = str(video_files[0])
    logger.info(f"Usando video: {video_path}")
    
    # Crear directorio de salida específico para esta prueba
    output_dir = Path("test_clips")
    output_dir.mkdir(exist_ok=True)
    logger.info(f"Directorio de salida: {output_dir.absolute()}")
    
    # Crear instancia del cortador con directorio específico
    cutter = VideoCutter(str(output_dir))
    
    # Clip de prueba simple
    test_clip = {
        "title": "Clip de verificación",
        "start_time": 10.0,
        "end_time": 20.0,
        "duration": 10.0,
        "description": "Clip para verificar creación",
        "confidence": 0.8
    }
    
    logger.info("Cortando clip de prueba...")
    
    try:
        # Cortar clip individual
        result_path = await cutter._cut_single_clip(video_path, test_clip, 1)
        logger.info(f"Clip cortado, ruta devuelta: {result_path}")
        
        # Verificar inmediatamente después del cortado
        if result_path.exists():
            size = result_path.stat().st_size
            logger.info(f"✅ Archivo existe inmediatamente: {size} bytes")
        else:
            logger.error(f"❌ Archivo NO existe inmediatamente después del cortado")
            return
        
        # Esperar un poco y verificar de nuevo
        logger.info("Esperando 2 segundos...")
        await asyncio.sleep(2)
        
        if result_path.exists():
            size = result_path.stat().st_size
            logger.info(f"✅ Archivo sigue existiendo después de 2s: {size} bytes")
        else:
            logger.error(f"❌ Archivo DESAPARECIÓ después de 2 segundos")
        
        # Listar todos los archivos en el directorio
        logger.info("Archivos en el directorio de salida:")
        for file in output_dir.iterdir():
            if file.is_file():
                logger.info(f"  - {file.name} ({file.stat().st_size} bytes)")
        
        # Verificar permisos del directorio
        logger.info(f"Permisos del directorio: {oct(output_dir.stat().st_mode)}")
        
    except Exception as e:
        logger.error(f"Error durante la verificación: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def test_direct_ffmpeg():
    """
    Prueba FFmpeg directamente sin usar la clase VideoCutter
    """
    logger.info("\n=== PRUEBA DIRECTA DE FFMPEG ===")
    
    videos_dir = Path("output/videos")
    video_files = list(videos_dir.glob("*.mp4"))
    video_path = str(video_files[0])
    
    output_dir = Path("test_clips")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "direct_ffmpeg_test.mp4"
    
    # Comando FFmpeg directo
    cmd = [
        "ffmpeg",
        "-ss", "30",
        "-t", "10",
        "-i", video_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "medium",
        "-crf", "23",
        str(output_file),
        "-y"
    ]
    
    logger.info(f"Ejecutando comando: {' '.join(cmd)}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("✅ FFmpeg directo exitoso")
            
            if output_file.exists():
                size = output_file.stat().st_size
                logger.info(f"✅ Archivo creado: {size} bytes")
            else:
                logger.error("❌ Archivo no se creó")
        else:
            logger.error(f"❌ FFmpeg falló con código {process.returncode}")
            if stderr:
                logger.error(f"Error: {stderr.decode()}")
                
    except Exception as e:
        logger.error(f"Error ejecutando FFmpeg directo: {str(e)}")

async def main():
    await verify_clip_creation()
    await test_direct_ffmpeg()
    
    # Listar archivos finales
    test_dir = Path("test_clips")
    if test_dir.exists():
        logger.info("\nArchivos finales en test_clips:")
        for file in test_dir.iterdir():
            if file.is_file():
                logger.info(f"  - {file.name} ({file.stat().st_size} bytes)")

if __name__ == "__main__":
    asyncio.run(main())