import asyncio
import uuid
import json
import logging
import os
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import WebSocket
from transcriber import WhisperTranscriber
from analyzer import LLMAnalyzer
from cutter import VideoCutter
import ffmpeg

logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self):
        self.active_jobs: Dict[str, Dict] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.transcriber = WhisperTranscriber()
        self.analyzer = LLMAnalyzer()
        self.cutter = VideoCutter()
    
    def create_job(self, context: str, topics: str, profile: str, video_path: str) -> str:
        """
        Crea un nuevo trabajo y devuelve el job_id
        """
        job_id = str(uuid.uuid4())
        
        # Calcular estimaciones de tiempo basadas en duración del video
        time_estimates = self._calculate_time_estimates(video_path)
        
        self.active_jobs[job_id] = {
            "id": job_id,
            "status": "created",
            "progress": 0.0,
            "message": "Trabajo creado",
            "context": context,
            "topics": topics,
            "profile": profile,
            "video_path": video_path,
            "created_at": datetime.now(),
            "results": [],
            "time_estimates": time_estimates,
            "stage_start_times": {}
        }
        
        logger.info(f"Trabajo creado: {job_id}")
        return job_id
    
    def create_job_with_transcription(self, context: str, topics: str, profile: str, transcription_job_id: str) -> str:
        """
        Crea un nuevo trabajo usando una transcripción existente
        """
        job_id = str(uuid.uuid4())
        
        # Cargar transcripción existente
        transcription_path = Path("output") / "transcriptions" / f"{transcription_job_id}_transcription.json"
        
        with open(transcription_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        transcription = transcript_data["transcription"]
        original_video_path = transcript_data.get("video_path", "")
        
        # Calcular estimaciones de tiempo usando el video original si existe
        time_estimates = self._calculate_time_estimates(original_video_path, skip_transcription=True)
        
        self.active_jobs[job_id] = {
            "id": job_id,
            "status": "created",
            "progress": 0.0,
            "message": "Trabajo creado con transcripción existente",
            "context": context,
            "topics": topics,
            "profile": profile,
            "video_path": original_video_path,
            "created_at": datetime.now(),
            "results": [],
            "use_existing_transcription": True,
            "transcription": transcription,
            "source_transcription_job_id": transcription_job_id,
            "time_estimates": time_estimates,
            "stage_start_times": {}
        }
        
        logger.info(f"Trabajo creado con transcripción existente: {job_id} (fuente: {transcription_job_id})")
        return job_id
    
    async def register_websocket(self, job_id: str, websocket: WebSocket):
        """
        Registra una conexión WebSocket para un trabajo
        """
        self.websocket_connections[job_id] = websocket
        logger.info(f"WebSocket registrado para trabajo: {job_id}")
    
    def unregister_websocket(self, job_id: str):
        """
        Desregistra una conexión WebSocket
        """
        if job_id in self.websocket_connections:
            del self.websocket_connections[job_id]
            logger.info(f"WebSocket desregistrado para trabajo: {job_id}")
    
    async def send_progress_update(self, job_id: str, status: str, progress: float, message: str, results: Optional[List] = None):
        """
        Envía una actualización de progreso a través de WebSocket
        """
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.update({
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.now()
            })
            
            if results is not None:
                job["results"] = results
        
        if job_id in self.websocket_connections:
            try:
                # Calcular información de tiempo
                elapsed_time = (datetime.now() - self.active_jobs[job_id]["created_at"]).total_seconds()
                time_info = self._calculate_remaining_time(self.active_jobs[job_id], progress, elapsed_time)
                
                update = {
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "results": results,
                    "time_info": time_info
                }
                
                await self.websocket_connections[job_id].send_text(json.dumps(update))
                # Mostrar progreso en terminal con barra visual
                progress_bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
                logger.info(f"📈 [{progress_bar}] {progress*100:.1f}% - {message}")
                
            except Exception as e:
                logger.error(f"Error enviando progreso para {job_id}: {str(e)}")
                self.unregister_websocket(job_id)
    
    async def process_job(self, job_id: str):
        """
        Procesa un trabajo completo de forma asíncrona
        """
        if job_id not in self.active_jobs:
            logger.error(f"Trabajo no encontrado: {job_id}")
            return
        
        job = self.active_jobs[job_id]
        
        try:
            await self.send_progress_update(job_id, "starting", 0.0, "Iniciando procesamiento...")
            logger.info(f"🎬 INICIANDO PROCESAMIENTO - Job ID: {job_id}")
            
            # Verificar si usar transcripción existente
            if job.get("use_existing_transcription", False):
                # Usar transcripción existente
                transcription = job["transcription"]
                await self.send_progress_update(job_id, "transcribing", 0.33, "Usando transcripción existente...")
                logger.info(f"📄 USANDO TRANSCRIPCIÓN EXISTENTE - Job ID: {job_id} (fuente: {job.get('source_transcription_job_id')})")
            else:
                # Fase 1: Transcripción
                await self.send_progress_update(job_id, "transcribing", 0.0, "Iniciando transcripción...")
                logger.info(f"🎤 FASE 1/3: TRANSCRIPCIÓN - Job ID: {job_id}")
                
                progress_callback = lambda status, progress, message: self.send_progress_update(
                    job_id, status, progress * 0.33, message
                )
                
                transcription = await self.transcriber.transcribe_video(
                    job["video_path"], 
                    progress_callback
                )
                
                if not transcription:
                    raise Exception("No se pudo obtener transcripción del video")
                
                # Guardar transcripción
                await self._save_transcription(job_id, transcription, job["video_path"])
            
            # Fase 2: Análisis
            await self.send_progress_update(job_id, "analyzing", 0.33, "Iniciando análisis con IA...")
            logger.info(f"🧠 FASE 2/3: ANÁLISIS CON IA - Job ID: {job_id}")
            
            progress_callback = lambda status, progress, message: self.send_progress_update(
                job_id, status, 0.33 + (progress * 0.33), message
            )
            
            clips = await self.analyzer.analyze_transcription(
                job["context"],
                job["topics"],
                job["profile"],
                transcription,
                progress_callback
            )
            
            if not clips:
                raise Exception("No se identificaron clips relevantes en el video")
            
            # Fase 3: Corte de clips
            await self.send_progress_update(job_id, "cutting", 0.66, "Iniciando corte de clips...")
            logger.info(f"✂️ FASE 3/3: CORTE DE CLIPS - Job ID: {job_id}")
            
            progress_callback = lambda status, progress, message: self.send_progress_update(
                job_id, status, 0.66 + (progress * 0.34), message
            )
            
            results = await self.cutter.cut_clips(
                job["video_path"],
                clips,
                progress_callback
            )
            
            # Finalización
            await self.send_progress_update(
                job_id, 
                "complete", 
                1.0, 
                f"Procesamiento completado. {len(results)} clips generados.",
                results
            )
            
            # Calcular tiempo total
            total_time = (datetime.now() - job["created_at"]).total_seconds()
            logger.info(f"✅ PROCESAMIENTO COMPLETADO - Job ID: {job_id}")
            logger.info(f"📊 ESTADÍSTICAS: {len(results)} clips generados en {total_time:.1f} segundos")
            
        except Exception as e:
            error_message = f"Error en procesamiento: {str(e)}"
            logger.error(f"Error en trabajo {job_id}: {error_message}")
            
            await self.send_progress_update(
                job_id,
                "error",
                0.0,
                error_message
            )
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Obtiene el estado actual de un trabajo
        """
        return self.active_jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Dict]:
        """
        Obtiene todos los trabajos activos
        """
        return list(self.active_jobs.values())
    
    def cleanup_job(self, job_id: str):
        """
        Limpia un trabajo y sus recursos asociados
        """
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            
            # Solo eliminar video si no es reutilizado por otros trabajos
            if "video_path" in job and job["video_path"] and os.path.exists(job["video_path"]):
                # Verificar si otros trabajos usan el mismo video
                video_in_use = any(
                    other_job.get("video_path") == job["video_path"] 
                    for other_job_id, other_job in self.active_jobs.items() 
                    if other_job_id != job_id
                )
                
                if not video_in_use:
                    try:
                        os.unlink(job["video_path"])
                        logger.info(f"Archivo de video eliminado: {job['video_path']}")
                    except Exception as e:
                        logger.error(f"Error eliminando archivo de video: {e}")
                else:
                    logger.info(f"Video mantenido (en uso por otros trabajos): {job['video_path']}")
            
            del self.active_jobs[job_id]
        
        if job_id in self.websocket_connections:
            self.unregister_websocket(job_id)
        
        logger.info(f"Trabajo limpiado: {job_id}")
    
    async def validate_dependencies(self) -> Dict[str, bool]:
        """
        Valida que todas las dependencias estén disponibles
        """
        validation = {
            "whisper_model": self.transcriber.validate_model(),
            "llm_connection": await self.analyzer.test_connection(),
            "ffmpeg": True  # Se asume que FFmpeg está disponible
        }
        
        return validation
    
    def get_system_status(self) -> Dict:
        """
        Obtiene el estado del sistema
        """
        return {
            "active_jobs": len(self.active_jobs),
            "websocket_connections": len(self.websocket_connections),
            "transcriber_model": self.transcriber.get_model_info(),
            "analyzer_url": self.analyzer.api_url,
            "output_directory": str(self.cutter.output_dir)
        }
    
    async def _save_transcription(self, job_id: str, transcription: str, video_path: str):
        """
        Guarda la transcripción y metadatos del video
        """
        try:
            # Crear directorio de transcripciones
            transcriptions_dir = Path("output") / "transcriptions"
            transcriptions_dir.mkdir(exist_ok=True)
            
            # Obtener información del video
            video_info = await self._get_video_info(video_path)
            
            # Crear archivo de transcripción con metadatos
            transcript_data = {
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
                "video_info": video_info,
                "video_path": video_path,  # Guardar ruta del video
                "transcription": transcription
            }
            
            # Guardar como JSON
            json_path = transcriptions_dir / f"{job_id}_transcription.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            
            # Guardar solo el texto de transcripción
            txt_path = transcriptions_dir / f"{job_id}_transcription.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(transcription)
            
            logger.info(f"Transcripción guardada: {json_path}")
            
        except Exception as e:
            logger.error(f"Error guardando transcripción: {e}")
    
    async def _get_video_info(self, video_path: str) -> Dict:
        """
        Obtiene información detallada del video
        """
        try:
            probe = ffmpeg.probe(video_path)
            
            # Información del archivo
            format_info = probe.get('format', {})
            
            # Información del stream de video
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            
            video_info = {
                "filename": os.path.basename(video_path),
                "file_size": int(format_info.get('size', 0)),
                "duration": float(format_info.get('duration', 0)),
                "format_name": format_info.get('format_name', 'unknown'),
                "bit_rate": int(format_info.get('bit_rate', 0))
            }
            
            if video_stream:
                video_info.update({
                    "video_codec": video_stream.get('codec_name', 'unknown'),
                    "width": int(video_stream.get('width', 0)),
                    "height": int(video_stream.get('height', 0)),
                    "fps": eval(video_stream.get('r_frame_rate', '0/1')),
                    "video_bitrate": int(video_stream.get('bit_rate', 0))
                })
            
            if audio_stream:
                video_info.update({
                    "audio_codec": audio_stream.get('codec_name', 'unknown'),
                    "sample_rate": int(audio_stream.get('sample_rate', 0)),
                    "channels": int(audio_stream.get('channels', 0)),
                    "audio_bitrate": int(audio_stream.get('bit_rate', 0))
                })
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error obteniendo información del video: {e}")
            return {
                "filename": os.path.basename(video_path),
                "error": str(e)
            }
    
    def _calculate_time_estimates(self, video_path: str, skip_transcription: bool = False) -> Dict:
        """
        Calcula estimaciones de tiempo para cada etapa basándose en la duración del video
        """
        try:
            # Obtener duración del video
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
            
            # Estimaciones basadas en experiencia empírica
            # Transcripción: ~0.3x duración del video (Whisper es rápido)
            # Análisis: ~0.1x duración del video (depende del LLM)
            # Corte: ~0.05x duración del video (FFmpeg es muy rápido)
            
            transcription_time = 0 if skip_transcription else max(30, duration * 0.3)
            analysis_time = max(20, duration * 0.1)
            cutting_time = max(10, duration * 0.05)
            
            total_time = transcription_time + analysis_time + cutting_time
            
            return {
                "transcription": int(transcription_time),
                "analysis": int(analysis_time),
                "cutting": int(cutting_time),
                "total": int(total_time),
                "video_duration": int(duration)
            }
            
        except Exception as e:
            logger.error(f"Error calculando estimaciones de tiempo: {str(e)}")
            # Valores por defecto si no se puede obtener la duración
            transcription_time = 0 if skip_transcription else 60
            return {
                "transcription": transcription_time,
                "analysis": 30,
                "cutting": 15,
                "total": transcription_time + 45,
                "video_duration": 0
            }
    
    def _calculate_remaining_time(self, job: Dict, progress: float, elapsed_time: float) -> Dict:
        """
        Calcula el tiempo restante basándose en el progreso actual con estimaciones mejoradas
        """
        estimates = job.get("time_estimates", {})
        stage_start_times = job.get("stage_start_times", {})
        
        if progress <= 0:
            return {
                "elapsed": int(elapsed_time),
                "remaining": estimates.get("total", 0),
                "estimated_total": estimates.get("total", 0),
                "current_stage": "Iniciando",
                "stage_progress": 0.0,
                "stage_estimates": estimates
            }
        
        # Determinar etapa actual y progreso de etapa
        if progress < 0.33:
            current_stage = "Transcripción" if not job.get("use_existing_transcription") else "Preparando"
            stage_progress = progress / 0.33
            stage_key = "transcription"
        elif progress < 0.66:
            current_stage = "Análisis con IA"
            stage_progress = (progress - 0.33) / 0.33
            stage_key = "analysis"
        else:
            current_stage = "Cortando clips"
            stage_progress = (progress - 0.66) / 0.34
            stage_key = "cutting"
        
        # Calcular tiempo restante con estimaciones adaptativas
        if progress > 0.1:  # Usar velocidad real después del 10%
            # Calcular velocidad promedio
            avg_speed = progress / elapsed_time
            remaining_progress = 1.0 - progress
            remaining = remaining_progress / avg_speed if avg_speed > 0 else estimates.get("total", 0)
            
            # Ajustar por etapa actual (análisis suele ser más lento)
            if 0.33 <= progress < 0.66:  # En análisis
                remaining *= 1.5  # Factor de corrección para análisis con IA
            
            estimated_total = elapsed_time + remaining
        else:
            # Usar estimaciones iniciales
            estimated_total = estimates.get("total", 0)
            remaining = max(0, estimated_total - elapsed_time)
        
        # Guardar tiempo de inicio de etapa
        if stage_key not in stage_start_times:
            stage_start_times[stage_key] = elapsed_time
            job["stage_start_times"] = stage_start_times
        
        return {
                "elapsed": int(elapsed_time),
                "remaining": int(max(0, remaining)),
                "estimated_total": int(estimated_total),
                "current_stage": current_stage,
                "stage_progress": min(1.0, max(0.0, stage_progress)),
                "stage_estimates": estimates,
                "avg_speed": round(progress / elapsed_time * 100, 2) if elapsed_time > 0 else 0
            }