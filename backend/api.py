import os
import tempfile
import logging
import json
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from models import ProcessRequest, JobStatus, OutputProfile
from core.job_manager import JobManager
from core.cutter import VideoCutter

logger = logging.getLogger(__name__)

# Crear router para la API
router = APIRouter()

# Instancia global del job manager
job_manager = JobManager()

@router.post("/api/start_process")
async def start_process(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    context: str = Form(...),
    topics: str = Form(...),
    profile: str = Form(...)
):
    """
    Inicia el proceso de creación de clips
    """
    try:
        # Validar archivo de video
        if not video_file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="El archivo debe ser un video")
        
        # Validar perfil
        try:
            profile_enum = OutputProfile(profile)
        except ValueError:
            raise HTTPException(status_code=400, detail="Perfil de salida no válido")
        
        # Crear directorio de videos si no existe
        videos_dir = Path("output") / "videos"
        videos_dir.mkdir(exist_ok=True)
        
        # Generar nombre único para el video
        video_filename = f"{uuid.uuid4()}.mp4"
        video_path = videos_dir / video_filename
        
        # Guardar archivo de video permanentemente
        content = await video_file.read()
        with open(video_path, "wb") as f:
            f.write(content)
        
        temp_video_path = str(video_path)
        
        # Crear trabajo
        job_id = job_manager.create_job(context, topics, profile, temp_video_path)
        
        # Iniciar procesamiento en segundo plano
        background_tasks.add_task(job_manager.process_job, job_id)
        
        logger.info(f"Proceso iniciado: {job_id}")
        
        return {
            "job_id": job_id,
            "message": "Proceso iniciado exitosamente",
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Error iniciando proceso: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    Endpoint WebSocket para actualizaciones en tiempo real
    """
    await websocket.accept()
    
    try:
        # Registrar conexión WebSocket
        await job_manager.register_websocket(job_id, websocket)
        
        # Enviar estado inicial si el trabajo existe
        job_status = job_manager.get_job_status(job_id)
        if job_status:
            initial_update = {
                "status": job_status["status"],
                "progress": job_status["progress"],
                "message": job_status["message"],
                "results": job_status.get("results", [])
            }
            await websocket.send_text(str(initial_update).replace("'", '"'))
        
        # Mantener conexión activa
        while True:
            try:
                # Esperar mensajes del cliente (ping/pong)
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado para trabajo: {job_id}")
    except Exception as e:
        logger.error(f"Error en WebSocket para {job_id}: {str(e)}")
    finally:
        job_manager.unregister_websocket(job_id)

@router.get("/api/job/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Obtiene el estado de un trabajo específico
    """
    job_status = job_manager.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    return {
        "job_id": job_id,
        "status": job_status["status"],
        "progress": job_status["progress"],
        "message": job_status["message"],
        "results": job_status.get("results", []),
        "created_at": job_status["created_at"].isoformat(),
        "updated_at": job_status.get("updated_at", job_status["created_at"]).isoformat()
    }

@router.get("/api/jobs")
async def get_all_jobs():
    """
    Obtiene todos los trabajos activos
    """
    jobs = job_manager.get_all_jobs()
    
    return {
        "jobs": [
            {
                "job_id": job["id"],
                "status": job["status"],
                "progress": job["progress"],
                "message": job["message"],
                "created_at": job["created_at"].isoformat()
            }
            for job in jobs
        ]
    }

@router.delete("/api/job/{job_id}")
async def cleanup_job(job_id: str):
    """
    Limpia un trabajo completado
    """
    job_status = job_manager.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    job_manager.cleanup_job(job_id)
    
    return {"message": f"Trabajo {job_id} limpiado exitosamente"}

@router.get("/api/download/{filename}")
async def download_clip(filename: str):
    """
    Descarga un clip generado
    """
    file_path = job_manager.cutter.output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='video/mp4'
    )

@router.get("/api/system/status")
async def get_system_status():
    """
    Obtiene el estado del sistema
    """
    system_status = job_manager.get_system_status()
    dependencies = await job_manager.validate_dependencies()
    
    return {
        "system": system_status,
        "dependencies": dependencies,
        "health": all(dependencies.values())
    }

@router.get("/api/system/validate")
async def validate_system():
    """
    Valida que todas las dependencias estén disponibles
    """
    dependencies = await job_manager.validate_dependencies()
    
    missing_deps = [dep for dep, available in dependencies.items() if not available]
    
    if missing_deps:
        return {
            "valid": False,
            "missing_dependencies": missing_deps,
            "dependencies": dependencies
        }
    
    return {
        "valid": True,
        "message": "Todas las dependencias están disponibles",
        "dependencies": dependencies
    }

@router.post("/api/system/cleanup")
async def cleanup_output_directory():
    """
    Limpia el directorio de salida
    """
    try:
        job_manager.cutter.cleanup_output_dir()
        return {"message": "Directorio de salida limpiado exitosamente"}
    except Exception as e:
        logger.error(f"Error limpiando directorio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/output/files")
async def list_output_files():
    """
    Lista todos los archivos de salida disponibles
    """
    try:
        files = job_manager.cutter.get_output_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listando archivos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/transcriptions")
async def list_transcriptions():
    """
    Lista todas las transcripciones guardadas
    """
    try:
        from pathlib import Path
        transcriptions_dir = Path("output") / "transcriptions"
        
        if not transcriptions_dir.exists():
            return {"transcriptions": []}
        
        transcriptions = []
        for json_file in transcriptions_dir.glob("*_transcription.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    transcriptions.append({
                        "job_id": data.get("job_id"),
                        "timestamp": data.get("timestamp"),
                        "filename": data.get("video_info", {}).get("filename", "unknown"),
                        "duration": data.get("video_info", {}).get("duration", 0),
                        "file_path": str(json_file)
                    })
            except Exception as e:
                logger.error(f"Error leyendo transcripción {json_file}: {e}")
                continue
        
        # Ordenar por timestamp descendente
        transcriptions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {"transcriptions": transcriptions}
    except Exception as e:
        logger.error(f"Error listando transcripciones: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/transcriptions/{job_id}")
async def get_transcription(job_id: str):
    """
    Obtiene una transcripción específica por job_id
    """
    try:
        from pathlib import Path
        transcriptions_dir = Path("output") / "transcriptions"
        json_file = transcriptions_dir / f"{job_id}_transcription.json"
        
        if not json_file.exists():
            raise HTTPException(status_code=404, detail="Transcripción no encontrada")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo transcripción {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/whisper/models")
async def get_whisper_models():
    """
    Obtiene información de modelos Whisper disponibles
    """
    try:
        models_info = job_manager.transcriber.get_available_models()
        current_model = job_manager.transcriber.get_model_info()
        
        return {
            "current_model": current_model,
            "available_models": models_info
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo modelos Whisper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/whisper/change_model")
async def change_whisper_model(request: dict):
    """
    Cambia el modelo de Whisper
    """
    try:
        model_name = request.get("model_name")
        
        if not model_name:
            raise HTTPException(status_code=400, detail="model_name es requerido")
        
        available_models = job_manager.transcriber.get_available_models()
        if model_name not in available_models:
            raise HTTPException(status_code=400, detail=f"Modelo {model_name} no disponible")
        
        success = job_manager.transcriber.change_model(model_name)
        
        if success:
            return {
                "success": True,
                "message": f"Modelo cambiado a {model_name}",
                "current_model": job_manager.transcriber.get_model_info()
            }
        else:
            raise HTTPException(status_code=500, detail="Error cambiando modelo")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando modelo Whisper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/ollama/models")
async def get_ollama_models():
    """
    Obtiene información sobre los modelos LLM disponibles
    """
    try:
        available_models = await job_manager.analyzer.get_available_models()
        current_model = job_manager.analyzer.model_name
        
        return {
            "available_models": available_models,
            "current_model": current_model,
            "ollama_status": len(available_models) > 0
        }
    except Exception as e:
        logger.error(f"Error obteniendo modelos Ollama: {str(e)}")
        return {
            "available_models": [],
            "current_model": job_manager.analyzer.model_name,
            "ollama_status": False,
            "error": str(e)
        }

@router.post("/api/ollama/change_model")
async def change_ollama_model(request: dict):
    """
    Cambia el modelo LLM de Ollama
    """
    try:
        model_name = request.get("model")
        if not model_name:
            raise HTTPException(status_code=400, detail="Nombre del modelo requerido")
        
        success = job_manager.analyzer.change_model(model_name)
        if success:
            return {
                "success": True,
                "message": f"Modelo LLM cambiado a {model_name}",
                "current_model": model_name
            }
        else:
            raise HTTPException(status_code=400, detail="Error cambiando modelo")
    except Exception as e:
        logger.error(f"Error cambiando modelo Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/start_process_with_transcription")
async def start_process_with_transcription(
    background_tasks: BackgroundTasks,
    transcription_job_id: str = Form(...),
    context: str = Form(...),
    topics: str = Form(...),
    profile: str = Form(...)
):
    """
    Inicia el proceso de creación de clips usando una transcripción existente
    """
    try:
        # Validar perfil
        try:
            profile_enum = OutputProfile(profile)
        except ValueError:
            raise HTTPException(status_code=400, detail="Perfil de salida no válido")
        
        # Verificar que existe la transcripción
        transcription_path = f"output/transcriptions/{transcription_job_id}_transcription.json"
        if not os.path.exists(transcription_path):
            raise HTTPException(status_code=404, detail="Transcripción no encontrada")
        
        # Crear trabajo usando transcripción existente
        job_id = job_manager.create_job_with_transcription(
            context, topics, profile, transcription_job_id
        )
        
        # Iniciar procesamiento en segundo plano
        background_tasks.add_task(job_manager.process_job, job_id)
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Proceso iniciado con transcripción existente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error iniciando proceso con transcripción: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/video/info")
async def get_video_info(
    video_file: UploadFile = File(...)
):
    """
    Obtiene información detallada del video incluyendo tamaño real
    """
    try:
        # Validar archivo de video
        if not video_file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="El archivo debe ser un video")
        
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await video_file.read()
            temp_file.write(content)
            temp_video_path = temp_file.name
        
        try:
            # Obtener información del video
            cutter = VideoCutter()
            video_info = await cutter.get_video_info(temp_video_path)
            
            # Agregar información del archivo
            video_info.update({
                "filename": video_file.filename,
                "content_type": video_file.content_type,
                "file_size": len(content)  # Tamaño real en bytes
            })
            
            return video_info
            
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(temp_video_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error obteniendo información del video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))