import logging
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from api import router

# Configurar logging con mejor formato para seguimiento de progreso
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Para mostrar en consola
    ]
)

# Configurar nivel de logging específico para componentes del sistema
logging.getLogger('core.job_manager').setLevel(logging.INFO)
logging.getLogger('core.transcriber').setLevel(logging.INFO)
logging.getLogger('core.analyzer').setLevel(logging.INFO)
logging.getLogger('core.cutter').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Crear aplicación FastAPI con límite de tamaño aumentado
app = FastAPI(
    title="Sistema de Creación de Contenido Automatizado (SCCA)",
    description="Aplicación web para extraer clips temáticos de videos usando IA",
    version="1.0.0"
)

# Nota: FastAPI no tiene límite de tamaño por defecto, pero uvicorn sí
# El límite se configura al iniciar el servidor

# Configurar rutas de archivos estáticos y templates
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Configurar templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Incluir router de la API
app.include_router(router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Página principal de la aplicación
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud
    """
    return {
        "status": "healthy",
        "service": "SCCA Backend",
        "version": "1.0.0"
    }

@app.on_event("startup")
async def startup_event():
    """
    Eventos de inicio de la aplicación
    """
    logger.info("Iniciando Sistema de Creación de Contenido Automatizado (SCCA)")
    
    # Crear directorios necesarios
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    logger.info("Directorios creados exitosamente")
    logger.info("SCCA Backend iniciado correctamente")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Eventos de cierre de la aplicación
    """
    logger.info("Cerrando SCCA Backend")

def main():
    """
    Función principal para iniciar el servidor
    """
    logger.info("Iniciando servidor SCCA...")
    
    uvicorn.run(
        "backend.main_app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        limit_max_requests=None,  # Sin límite de requests
        timeout_keep_alive=300   # Timeout extendido para archivos grandes
    )

if __name__ == "__main__":
    main()