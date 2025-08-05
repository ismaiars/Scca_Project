#!/usr/bin/env python3
"""
Script de diagnóstico para probar el cortado de clips con FFmpeg
"""

import asyncio
import os
import ffmpeg
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_ffmpeg_cutting():
    """
    Prueba el cortado de un clip simple con FFmpeg
    """
    # Buscar el video más reciente
    videos_dir = Path("output/videos")
    if not videos_dir.exists():
        logger.error("No existe el directorio output/videos")
        return
    
    video_files = list(videos_dir.glob("*.mp4"))
    if not video_files:
        logger.error("No se encontraron videos en output/videos")
        return
    
    video_path = video_files[0]
    logger.info(f"Usando video: {video_path}")
    
    # Verificar que el archivo existe
    if not video_path.exists():
        logger.error(f"El archivo de video no existe: {video_path}")
        return
    
    # Obtener información del video
    try:
        probe = ffmpeg.probe(str(video_path))
        duration = float(probe['streams'][0]['duration'])
        logger.info(f"Duración del video: {duration} segundos")
    except Exception as e:
        logger.error(f"Error obteniendo información del video: {e}")
        return
    
    # Crear un clip de prueba (primeros 10 segundos)
    output_path = Path("test_clip.mp4")
    start_time = 0
    clip_duration = min(10, duration)
    
    logger.info(f"Cortando clip de prueba: {start_time}s a {start_time + clip_duration}s")
    
    try:
        # Usar ffmpeg-python para cortar el clip
        stream = ffmpeg.input(str(video_path), ss=start_time, t=clip_duration)
        stream = ffmpeg.output(
            stream, 
            str(output_path),
            vcodec='libx264',
            acodec='aac',
            preset='medium',
            crf=23
        )
        
        # Compilar el comando FFmpeg
        cmd = ffmpeg.compile(stream, overwrite_output=True)
        logger.info(f"Comando FFmpeg: {' '.join(cmd)}")
        
        # Ejecutar el comando de forma asíncrona
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Error desconocido en FFmpeg"
            logger.error(f"Error en FFmpeg (código {process.returncode}): {error_msg}")
            if stdout:
                logger.info(f"FFmpeg stdout: {stdout.decode()}")
            return False
        
        # Verificar que el archivo se creó correctamente
        if not output_path.exists():
            logger.error(f"El archivo de salida no se creó: {output_path}")
            return False
        
        file_size = output_path.stat().st_size
        logger.info(f"Clip creado exitosamente: {output_path} ({file_size} bytes)")
        
        # Limpiar archivo de prueba
        output_path.unlink()
        logger.info("Archivo de prueba eliminado")
        
        return True
        
    except Exception as e:
        logger.error(f"Error durante el cortado: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    logger.info("=== DIAGNÓSTICO DE CORTADO DE CLIPS ===")
    
    # Verificar FFmpeg
    try:
        result = await asyncio.create_subprocess_exec(
            'ffmpeg', '-version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0:
            logger.info("✅ FFmpeg está disponible")
        else:
            logger.error("❌ FFmpeg no está disponible")
            return
    except Exception as e:
        logger.error(f"❌ Error verificando FFmpeg: {e}")
        return
    
    # Probar cortado
    success = await test_ffmpeg_cutting()
    if success:
        logger.info("✅ Prueba de cortado exitosa")
    else:
        logger.error("❌ Prueba de cortado falló")

if __name__ == "__main__":
    asyncio.run(main())