from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class OutputProfile(str, Enum):
    """Perfiles de salida para los clips"""
    SOCIAL_CLIPS = "Clips para Redes Sociales"  # Clips cortos para redes sociales
    EDUCATIONAL = "Cápsulas Educativas"  # Clips educativos medianos
    REFERENCE = "Archivo de Referencia"  # Clips largos de referencia

class JobStatus(str, Enum):
    """Estados posibles de un trabajo"""
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    CUTTING = "cutting"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessRequest(BaseModel):
    """Modelo para la solicitud de procesamiento"""
    context: str
    topics: str
    profile: OutputProfile
    video_filename: str
    
class ClipResult(BaseModel):
    """Resultado de un clip generado"""
    title: str
    start_time: float
    end_time: float
    duration: float
    filename: str
    description: Optional[str] = None

class JobResponse(BaseModel):
    """Respuesta del estado de un trabajo"""
    job_id: str
    status: JobStatus
    progress: float
    message: str
    results: Optional[List[ClipResult]] = None
    error: Optional[str] = None