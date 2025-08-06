import os
import asyncio
import subprocess
import ffmpeg
from typing import List, Dict, Callable, Optional
import logging
from pathlib import Path
import whisper
import tempfile
import json
import re

logger = logging.getLogger(__name__)

class VideoCutter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    async def cut_clip(self, video_path: str, start_time: float, end_time: float, 
                      output_path: str, title: str = "Clip") -> bool:
        """
        Corta un solo clip del video original
        """
        try:
            clip_data = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "description": f"Clip: {title}"
            }
            
            # Usar el número 1 como clip_number para un solo clip
            result_path = await self._cut_single_clip(video_path, clip_data, 1)
            
            # Mover el archivo al path deseado si es diferente
            if str(result_path) != output_path:
                import shutil
                shutil.move(str(result_path), output_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error cortando clip individual: {str(e)}")
            return False
    
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
                    
                    # Guardar metadatos del clip
                    await self._save_clip_metadata(output_path, clip_result, video_path)
                    
                    results.append(clip_result)
                    
                except Exception as e:
                    logger.error(f"Error cortando clip {i+1}: {str(e)}")
                    logger.error(f"Clip que falló: {clip}")
                    logger.error(f"Tipo de error: {type(e).__name__}")
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
        
        logger.info(f"Cortando clip {clip_number}: {clip['title']}")
        logger.info(f"Video origen: {video_path}")
        logger.info(f"Archivo destino: {output_path}")
        logger.info(f"Tiempo inicio: {start_time}, Duración: {duration}")
        
        # Verificar que el archivo de video existe
        if not os.path.exists(video_path):
            error_msg = f"El archivo de video no existe: {video_path}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
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
            
            # Compilar el comando FFmpeg
            cmd = ffmpeg.compile(stream, overwrite_output=True)
            logger.info(f"Comando FFmpeg: {' '.join(cmd)}")
            
            # Ejecutar el comando usando subprocess.run (compatible con Python 3.13)
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr if result.stderr else "Error desconocido en FFmpeg"
                    logger.error(f"Error en FFmpeg (código {result.returncode}): {error_msg}")
                    if result.stdout:
                        logger.error(f"FFmpeg stdout: {result.stdout}")
                    raise Exception(f"Error cortando clip: {error_msg}")
                    
            except Exception as e:
                logger.error(f"Error ejecutando FFmpeg: {str(e)}")
                raise Exception(f"Error cortando clip: {str(e)}")
            
            # Verificar que el archivo se creó correctamente
            if not output_path.exists():
                error_msg = f"El archivo de salida no se creó: {output_path}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Clip cortado exitosamente: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error cortando clip individual: {str(e)}")
            logger.error(f"Detalles del error: {type(e).__name__}: {e}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
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
                # Calcular FPS de forma segura
                fps_str = video_stream['r_frame_rate']
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    fps = float(num) / float(den) if float(den) != 0 else 0
                else:
                    fps = float(fps_str)
                
                info.update({
                    "width": int(video_stream['width']),
                    "height": int(video_stream['height']),
                    "fps": round(fps, 2),
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
        Obtiene lista de archivos en el directorio de salida con información completa
        """
        files = []
        try:
            # Buscar archivos .mp4 recursivamente en el directorio de salida
            for file_path in self.output_dir.rglob("*.mp4"):
                if file_path.is_file():
                    # Cargar metadatos si existen
                    metadata = self._load_clip_metadata(str(file_path))
                    
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "modified": file_path.stat().st_mtime
                    }
                    
                    # Agregar información de metadatos si está disponible
                    if metadata and "clip_info" in metadata:
                        clip_info = metadata["clip_info"]
                        file_info.update({
                            "title": clip_info.get("title", file_path.stem),
                            "start_time": clip_info.get("start_time", 0),
                            "end_time": clip_info.get("end_time", 0),
                            "duration": clip_info.get("duration", 0),
                            "description": clip_info.get("description", "Clip existente")
                        })
                    else:
                        # Información por defecto si no hay metadatos
                        clean_title = file_path.stem.replace('clip_', '')
                        clean_title = re.sub(r'^\d+_', '', clean_title)  # Remover números iniciales
                        file_info.update({
                            "title": clean_title,
                            "start_time": 0,
                            "end_time": 0,
                            "duration": 0,
                            "description": "Clip existente"
                        })
                    
                    files.append(file_info)
                    
        except Exception as e:
            logger.error(f"Error listando archivos: {str(e)}")
        
        # Ordenar por fecha de modificación (más recientes primero)
        files.sort(key=lambda x: x.get("modified", 0), reverse=True)
        
        return files
    
    async def add_subtitles_to_clip(self, clip_path: str, video_path: str, 
                                   start_time: float, end_time: float,
                                   whisper_model=None) -> str:
        """
        Añade subtítulos a un clip específico usando Whisper
        """
        try:
            # Si no se proporciona modelo, cargar uno por defecto
            if whisper_model is None:
                whisper_model = whisper.load_model("base")
            
            # Extraer audio del clip directamente (no del video original)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            # Extraer audio del clip completo
            stream = ffmpeg.input(clip_path)
            stream = ffmpeg.output(stream, temp_audio_path, acodec='pcm_s16le', ac=1, ar=16000)
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            # Transcribir con configuración mejorada
            result = whisper_model.transcribe(
                temp_audio_path,
                language="es",
                word_timestamps=True,
                verbose=False,
                temperature=0.0,
                no_speech_threshold=0.6,
                logprob_threshold=-1.0
            )
            
            # Generar archivo SRT (sin offset ya que usamos el clip completo)
            srt_content = self._generate_srt_from_whisper(result, 0)
            
            # Crear archivo SRT temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix=".srt", delete=False, encoding='utf-8') as srt_file:
                srt_file.write(srt_content)
                srt_path = srt_file.name
            
            # Crear carpeta para clips con subtítulos
            clip_path_obj = Path(clip_path)
            subtitled_dir = self.output_dir / "subtitled_clips"
            subtitled_dir.mkdir(exist_ok=True)
            
            # Generar nombre para el clip con subtítulos en la carpeta separada
            subtitled_clip_path = subtitled_dir / f"{clip_path_obj.stem}_subtitled{clip_path_obj.suffix}"
            
            # Añadir subtítulos al video usando FFmpeg
            # Escapar la ruta del archivo SRT para Windows
            escaped_srt_path = srt_path.replace('\\', '/').replace(':', '\\:')
            
            input_video = ffmpeg.input(clip_path)
            output = ffmpeg.output(
                input_video,
                str(subtitled_clip_path),
                vf=f"subtitles='{escaped_srt_path}':force_style='FontSize=16,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
                vcodec='libx264',
                acodec='copy'
            )
            
            # Ejecutar FFmpeg con captura de errores
            try:
                ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            except ffmpeg.Error as e:
                stderr_output = e.stderr.decode('utf-8') if e.stderr else 'No stderr available'
                stdout_output = e.stdout.decode('utf-8') if e.stdout else 'No stdout available'
                logger.error(f"FFmpeg stderr: {stderr_output}")
                logger.error(f"FFmpeg stdout: {stdout_output}")
                raise Exception(f"Error en FFmpeg al añadir subtítulos: {stderr_output}")
            
            # Limpiar archivos temporales
            os.unlink(temp_audio_path)
            os.unlink(srt_path)
            
            logger.info(f"Subtítulos añadidos exitosamente: {subtitled_clip_path}")
            return str(subtitled_clip_path)
            
        except Exception as e:
            logger.error(f"Error añadiendo subtítulos: {str(e)}")
            raise e
    
    def _generate_srt_from_whisper(self, whisper_result: Dict, start_offset: float = 0) -> str:
        """
        Genera contenido SRT a partir del resultado de Whisper
        """
        srt_content = ""
        subtitle_index = 1
        
        logger.info(f"Generando SRT con {len(whisper_result.get('segments', []))} segmentos")
        
        for segment in whisper_result.get('segments', []):
            start_time = segment['start'] + start_offset
            end_time = segment['end'] + start_offset
            text = segment['text'].strip()
            
            # Incluir texto incluso si es muy corto, pero filtrar solo espacios
            if text and len(text) > 0:  
                srt_content += f"{subtitle_index}\n"
                srt_content += f"{self._format_srt_time(start_time)} --> {self._format_srt_time(end_time)}\n"
                srt_content += f"{text}\n\n"
                subtitle_index += 1
                logger.debug(f"Segmento {subtitle_index-1}: {start_time:.2f}-{end_time:.2f}s: '{text}'")
        
        logger.info(f"SRT generado con {subtitle_index-1} subtítulos")
        return srt_content
    
    def _format_srt_time(self, seconds: float) -> str:
        """
        Formatea tiempo en formato SRT (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    async def _save_clip_metadata(self, clip_path: Path, clip_data: Dict, original_video_path: str):
        """
        Guarda metadatos del clip en un archivo JSON
        """
        try:
            metadata = {
                "clip_info": clip_data,
                "original_video_path": original_video_path,
                "created_at": str(Path(clip_path).stat().st_mtime)
            }
            
            metadata_path = clip_path.with_suffix('.json')
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Metadatos guardados: {metadata_path}")
            
        except Exception as e:
            logger.error(f"Error guardando metadatos: {str(e)}")
    
    def _load_clip_metadata(self, clip_path: str) -> Optional[Dict]:
        """
        Carga metadatos de un clip desde su archivo JSON
        """
        try:
            clip_path_obj = Path(clip_path)
            metadata_path = clip_path_obj.with_suffix('.json')
            
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Error cargando metadatos: {str(e)}")
            return None