import asyncio
import uuid
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from fastapi import WebSocket
from .transcriber import WhisperTranscriber
from .analyzer import LLMAnalyzer
from .cutter import VideoCutter

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
            "results": []
        }
        
        logger.info(f"Trabajo creado: {job_id}")
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
            self.active_jobs[job_id].update({
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.now()
            })
            
            if results is not None:
                self.active_jobs[job_id]["results"] = results
        
        if job_id in self.websocket_connections:
            try:
                update = {
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "results": results
                }
                
                await self.websocket_connections[job_id].send_text(json.dumps(update))
                logger.debug(f"Progreso enviado para {job_id}: {status} - {progress:.2f}")
                
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
            
            # Fase 1: Transcripción
            await self.send_progress_update(job_id, "transcribing", 0.0, "Iniciando transcripción...")
            
            progress_callback = lambda status, progress, message: self.send_progress_update(
                job_id, status, progress * 0.33, message
            )
            
            transcription = await self.transcriber.transcribe_video(
                job["video_path"], 
                progress_callback
            )
            
            if not transcription:
                raise Exception("No se pudo obtener transcripción del video")
            
            # Fase 2: Análisis
            await self.send_progress_update(job_id, "analyzing", 0.33, "Iniciando análisis con IA...")
            
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
            
            logger.info(f"Trabajo completado exitosamente: {job_id}")
            
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
        Limpia un trabajo completado
        """
        if job_id in self.active_jobs:
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