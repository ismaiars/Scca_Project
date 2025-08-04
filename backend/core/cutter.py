import os
import asyncio
import ffmpeg
from typing import List, Dict, Callable, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class VideoCutter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    async def cut_clips(self, video_path: str, clips: List[Dict], 
                       progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Corta los clips del video original usando FFmpeg
        """
        try:
            if progress_callback:
                await progress_callback("cutting", 0.1, "Preparando corte de clips...")
            
            results = []
            total_clips = len(clips)
            
            for i, clip in enumerate(clips):
                if progress_callback:
                    progress = 0.1 + (0.8 * (i + 1) / total_clips)
                    await progress_callback("cutting", progress, f"Cortando clip {i+1}/{total_clips}: {clip['title']}")
                
                try:
                    output_path = await self._cut_single_clip(video_path, clip, i+1)
                    
                    clip_result = {
                        "title": clip["title"],
                        "start_time": clip["start_time"],
                        "end_time": clip["end_time"],
                        "duration": clip["duration"],
                        "description": clip["description"],
                        "file_path": str(output_path),
                        "file_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0
                    }
                    
                    results.append(clip_result)
                    
                except Exception as e:
                    logger.error(f"Error cortando clip {i+1}: {str(e)}")
                    continue
            
            if progress_callback:
                await progress_callback("cutting", 1.0, f"Corte completado. {len(results)} clips generados")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en corte de clips: {str(e)}")
            if progress_callback:
                await progress_callback("cutting", 0.0, f"Error: {str(e)}")
            raise e
    
    async def _cut_single_clip(self, video_path: str, clip: Dict, clip_number: int) -> Path:
        """
        Corta un clip individual del video
        """
        # Generar nombre de archivo seguro
        safe_title = self._sanitize_filename(clip["title"])
        output_filename = f"clip_{clip_number:03d}_{safe_title}.mp4"
        output_path = self.output_dir / output_filename
        
        start_time = clip["start_time"]
        duration = clip["duration"]
        
        try:
            # Usar ffmpeg-python para cortar el clip
            stream = ffmpeg.input(video_path, ss=start_time, t=duration)
            stream = ffmpeg.output(
                stream, 
                str(output_path),
                vcodec='libx264',
                acodec='aac',
                preset='medium',
                crf=23
            )
            
            # Ejecutar el comando de forma asíncrona
            process = await asyncio.create_subprocess_exec(
                *ffmpeg.compile(stream, overwrite_output=True),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Error desconocido en FFmpeg"
                logger.error(f"Error en FFmpeg: {error_msg}")
                raise Exception(f"Error cortando clip: {error_msg}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error cortando clip individual: {str(e)}")
            raise e
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza el nombre del archivo para que sea válido en el sistema de archivos
        """
        # Caracteres no permitidos en nombres de archivo
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limitar longitud
        filename = filename[:50]
        
        # Eliminar espacios al inicio y final
        filename = filename.strip()
        
        # Si queda vacío, usar nombre por defecto
        if not filename:
            filename = "clip"
        
        return filename
    
    async def get_video_info(self, video_path: str) -> Dict:
        """
        Obtiene información del video usando FFprobe
        """
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            
            duration = float(probe['format']['duration'])
            
            info = {
                "duration": duration,
                "format": probe['format']['format_name'],
                "size": int(probe['format']['size']),
                "bitrate": int(probe['format']['bit_rate']) if 'bit_rate' in probe['format'] else 0
            }
            
            if video_stream:
                info.update({
                    "width": int(video_stream['width']),
                    "height": int(video_stream['height']),
                    "fps": eval(video_stream['r_frame_rate']),
                    "video_codec": video_stream['codec_name']
                })
            
            if audio_stream:
                info.update({
                    "audio_codec": audio_stream['codec_name'],
                    "sample_rate": int(audio_stream['sample_rate']),
                    "channels": int(audio_stream['channels'])
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Error obteniendo información del video: {str(e)}")
            return {}
    
    def cleanup_output_dir(self):
        """
        Limpia el directorio de salida
        """
        try:
            for file_path in self.output_dir.glob("*.mp4"):
                file_path.unlink()
            logger.info("Directorio de salida limpiado")
        except Exception as e:
            logger.error(f"Error limpiando directorio: {str(e)}")
    
    def get_output_files(self) -> List[Dict]:
        """
        Obtiene lista de archivos en el directorio de salida
        """
        files = []
        try:
            for file_path in self.output_dir.glob("*.mp4"):
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                })
        except Exception as e:
            logger.error(f"Error listando archivos: {str(e)}")
        
        return files