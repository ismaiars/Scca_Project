import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from .models import ProcessRequest, JobStatus, OutputProfile
from .core.job_manager import JobManager

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
        
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await video_file.read()
            temp_file.write(content)
            temp_video_path = temp_file.name
        
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
    Lista los archivos en el directorio de salida
    """
    try:
        files = job_manager.cutter.get_output_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listando archivos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))