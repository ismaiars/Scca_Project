import os
import asyncio
import subprocess
import tempfile
from typing import Callable, Optional
import logging
import whisper
import ffmpeg

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """Transcriptor de video usando OpenAI Whisper"""
    
    def __init__(self, model_name: str = "medium"):
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
            if progress_callback:
                await progress_callback("Extrayendo audio del video...")
            
            # Extraer audio
            audio_path = await self._extract_audio(video_path)
            
            if progress_callback:
                await progress_callback("Iniciando transcripción con Whisper...")
            
            # Transcribir con OpenAI Whisper
            result = self.model.transcribe(audio_path)
            transcription = result["text"]
            
            # Limpiar archivo temporal
            os.unlink(audio_path)
            
            if progress_callback:
                await progress_callback("Transcripción completada")
            
            return transcription
            
        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            raise
    
    async def _extract_audio(self, video_path: str) -> str:
        """Extrae audio del video usando FFmpeg"""
        try:
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
        """Obtiene información del modelo Whisper"""
        return {
            "model_name": self.model_name,
            "model_loaded": self.model is not None
        }