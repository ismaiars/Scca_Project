import os
import asyncio
import subprocess
import tempfile
from typing import Callable, Optional
import logging
import whisper
import ffmpeg
import time
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """Transcriptor de video usando OpenAI Whisper"""
    
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self.load_model()
    
    def load_model(self) -> bool:
        """Carga el modelo Whisper"""
        try:
            logger.info(f"Cargando modelo Whisper: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            logger.info(f"Modelo Whisper cargado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando modelo Whisper: {e}")
            raise
    
    def validate_model(self) -> bool:
        """Valida que el modelo esté cargado"""
        return self.model is not None
        
    async def transcribe_video(self, video_path: str, progress_callback: Optional[Callable] = None) -> str:
        """Transcribe un video usando OpenAI Whisper"""
        try:
            start_time = time.time()
            
            if progress_callback:
                await progress_callback("transcribing", 0.05, "🎬 Analizando video...")
            
            # Obtener duración del video
            video_duration = await self._get_video_duration(video_path)
            estimated_seconds, estimated_time_formatted = self._estimate_transcription_time(video_duration)
            
            if progress_callback:
                await progress_callback("transcribing", 0.1, f"📹 Video: {video_duration:.1f}s | ⏱️ Tiempo estimado: {estimated_time_formatted}")
            
            # Extraer audio
            audio_path = await self._extract_audio(video_path, progress_callback)
            
            if progress_callback:
                await progress_callback("transcribing", 0.2, "🎤 Iniciando transcripción con Whisper...")
            
            # Transcribir con progreso en tiempo real
            result = await self._transcribe_with_progress(audio_path, progress_callback, start_time, estimated_seconds)
            transcription = result["text"]
            
            # Limpiar archivo temporal
            os.unlink(audio_path)
            
            actual_time = time.time() - start_time
            actual_time_formatted = self._format_time(actual_time)
            if progress_callback:
                await progress_callback("transcribing", 1.0, f"✅ Transcripción completada en {actual_time_formatted}")
            
            return transcription
            
        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            raise
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Obtiene la duración del video en segundos"""
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            logger.warning(f"No se pudo obtener duración del video: {e}")
            return 0.0
    
    def _format_time(self, seconds: float) -> str:
        """Convierte segundos a formato horas:minutos:segundos"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def _estimate_transcription_time(self, video_duration: float) -> tuple[float, str]:
        """Estima el tiempo de transcripción basado en la duración del video"""
        # Whisper optimizado con configuraciones de velocidad
        # Tiempos reducidos con las optimizaciones aplicadas
        model_multipliers = {
            "tiny": 1.5,
            "base": 2.0,  # Optimizado con beam_size=1 y otras configuraciones
            "small": 3.0,
            "medium": 4.0,
            "large": 6.0
        }
        multiplier = model_multipliers.get(self.model_name, 2.0)
        estimated_seconds = video_duration * multiplier
        formatted_time = self._format_time(estimated_seconds)
        return estimated_seconds, formatted_time
    
    async def _transcribe_with_progress(self, audio_path: str, progress_callback: Optional[Callable], start_time: float, estimated_time: float):
        """Transcribe con progreso simulado en tiempo real"""
        # Crear un hilo para la transcripción
        result_container = {"result": None, "error": None, "completed": False}
        
        def transcribe_thread():
            try:
                # Configuraciones optimizadas para velocidad
                result_container["result"] = self.model.transcribe(
                    audio_path,
                    fp16=False,  # Usar FP32 para mejor compatibilidad
                    language="es",  # Especificar idioma español
                    task="transcribe",  # Solo transcribir, no traducir
                    beam_size=1,  # Reducir beam size para velocidad
                    best_of=1,  # Usar solo 1 candidato
                    temperature=0.0,  # Determinístico
                    compression_ratio_threshold=2.4,
                    logprob_threshold=-1.0,
                    no_speech_threshold=0.6
                )
                result_container["completed"] = True
            except Exception as e:
                result_container["error"] = e
                result_container["completed"] = True
        
        # Iniciar transcripción en hilo separado
        thread = threading.Thread(target=transcribe_thread)
        thread.start()
        
        # Simular progreso mientras transcribe
        progress = 0.2  # Ya estamos en 20%
        while not result_container["completed"]:
            elapsed_time = time.time() - start_time
            
            # Calcular progreso estimado
            if estimated_time > 0:
                estimated_progress = min(0.95, 0.2 + (elapsed_time / estimated_time) * 0.75)
                progress = max(progress, estimated_progress)
            else:
                # Progreso lineal si no tenemos estimación
                progress = min(0.95, progress + 0.05)
            
            if progress_callback:
                remaining_time = max(0, estimated_time - elapsed_time)
                remaining_time_formatted = self._format_time(remaining_time)
                await progress_callback(
                    "transcribing", 
                    progress, 
                    f"🎤 Transcribiendo... {progress*100:.1f}% | ⏱️ Restante: ~{remaining_time_formatted}"
                )
            
            await asyncio.sleep(2)  # Actualizar cada 2 segundos
        
        # Esperar a que termine el hilo
        thread.join()
        
        if result_container["error"]:
            raise result_container["error"]
        
        return result_container["result"]
    
    async def _extract_audio(self, video_path: str, progress_callback: Optional[Callable] = None) -> str:
        """Extrae audio del video usando FFmpeg"""
        try:
            if progress_callback:
                await progress_callback("transcribing", 0.15, "🎵 Extrayendo audio del video...")
            
            # Crear archivo temporal para el audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                audio_path = temp_audio.name
            
            # Extraer audio usando ffmpeg-python
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, ar=16000, ac=1, format='wav')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return audio_path
            
        except Exception as e:
            logger.error(f"Error extrayendo audio: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """Obtiene información del modelo actual"""
        return {
            "model_name": self.model_name,
            "model_loaded": self.model is not None
        }
    
    def change_model(self, model_name: str) -> bool:
        """Cambia el modelo de Whisper dinámicamente"""
        try:
            logger.info(f"Cambiando modelo de {self.model_name} a {model_name}")
            self.model_name = model_name
            self.model = whisper.load_model(model_name)
            logger.info(f"Modelo {model_name} cargado exitosamente")
            return True
        except Exception as e:
            logger.error(f"Error cambiando modelo: {e}")
            return False
    
    def get_available_models(self) -> dict:
        """Obtiene información de modelos disponibles con sus características"""
        return {
            "tiny": {
                "size": "39 MB",
                "speed": "Muy rápido (~1.5x tiempo real)",
                "accuracy": "Básica",
                "recommended_for": "Pruebas rápidas, contenido simple"
            },
            "base": {
                "size": "74 MB",
                "speed": "Rápido (~2x tiempo real)",
                "accuracy": "Buena",
                "recommended_for": "Uso general, balance velocidad/calidad"
            },
            "small": {
                "size": "244 MB",
                "speed": "Moderado (~3x tiempo real)",
                "accuracy": "Muy buena",
                "recommended_for": "Contenido técnico, mejor calidad"
            },
            "medium": {
                "size": "769 MB",
                "speed": "Lento (~4x tiempo real)",
                "accuracy": "Excelente",
                "recommended_for": "Contenido complejo, máxima calidad"
            },
            "large": {
                "size": "1550 MB",
                "speed": "Muy lento (~6x tiempo real)",
                "accuracy": "Máxima",
                "recommended_for": "Transcripciones profesionales"
            }
        }