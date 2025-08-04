// Sistema de Creación de Contenido Automatizado (SCCA)
// Frontend JavaScript

class SCCAApp {
    constructor() {
        this.currentJobId = null;
        this.websocket = null;
        this.isProcessing = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateFileInputDisplay();
        this.validateSystem();
    }
    
    bindEvents() {
        // Formulario principal
        const form = document.getElementById('process-form');
        form.addEventListener('submit', this.handleFormSubmit.bind(this));
        
        // Input de archivo
        const fileInput = document.getElementById('video-file');
        fileInput.addEventListener('change', this.handleFileChange.bind(this));
        
        // Botón de nuevo proceso
        const newProcessBtn = document.getElementById('new-process-btn');
        newProcessBtn.addEventListener('click', this.resetApplication.bind(this));
        
        // Botón de descargar todos
        const downloadAllBtn = document.getElementById('download-all-btn');
        downloadAllBtn.addEventListener('click', this.downloadAllClips.bind(this));
    }
    
    async handleFormSubmit(event) {
        event.preventDefault();
        
        if (this.isProcessing) {
            this.showNotification('Ya hay un proceso en ejecución', 'warning');
            return;
        }
        
        const formData = new FormData(event.target);
        const videoFile = formData.get('video_file');
        
        // Validaciones
        if (!videoFile || videoFile.size === 0) {
            this.showNotification('Por favor selecciona un archivo de video', 'error');
            return;
        }
        
        if (videoFile.size > 500 * 1024 * 1024) { // 500MB
            this.showNotification('El archivo es demasiado grande (máximo 500MB)', 'error');
            return;
        }
        
        const context = formData.get('context').trim();
        const topics = formData.get('topics').trim();
        const profile = formData.get('profile');
        
        if (!context || !topics || !profile) {
            this.showNotification('Por favor completa todos los campos', 'error');
            return;
        }
        
        try {
            this.isProcessing = true;
            this.showProgressArea();
            this.resetProgress();
            
            // Enviar solicitud al backend
            const response = await fetch('/api/start_process', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error iniciando el proceso');
            }
            
            const result = await response.json();
            this.currentJobId = result.job_id;
            
            this.showNotification('Proceso iniciado exitosamente', 'success');
            this.connectWebSocket();
            
        } catch (error) {
            console.error('Error:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
            this.isProcessing = false;
            this.hideProgressArea();
        }
    }
    
    connectWebSocket() {
        if (!this.currentJobId) return;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.currentJobId}`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket conectado');
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleProgressUpdate(data);
            } catch (error) {
                console.error('Error parseando mensaje WebSocket:', error);
            }
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket desconectado');
        };
        
        this.websocket.onerror = (error) => {
            console.error('Error en WebSocket:', error);
            this.showNotification('Error en la conexión en tiempo real', 'error');
        };
    }
    
    handleProgressUpdate(data) {
        const { status, progress, message, results } = data;
        
        // Actualizar progreso general
        this.updateOverallProgress(progress, message);
        
        // Actualizar progreso específico por fase
        switch (status) {
            case 'transcribing':
                this.updateStepProgress('transcription', progress, message, 'active');
                break;
                
            case 'analyzing':
                this.updateStepProgress('transcription', 1.0, 'Completado', 'completed');
                this.updateStepProgress('analysis', progress - 0.33, message, 'active');
                break;
                
            case 'cutting':
                this.updateStepProgress('transcription', 1.0, 'Completado', 'completed');
                this.updateStepProgress('analysis', 1.0, 'Completado', 'completed');
                this.updateStepProgress('cutting', progress - 0.66, message, 'active');
                break;
                
            case 'complete':
                this.updateStepProgress('transcription', 1.0, 'Completado', 'completed');
                this.updateStepProgress('analysis', 1.0, 'Completado', 'completed');
                this.updateStepProgress('cutting', 1.0, 'Completado', 'completed');
                this.showResults(results);
                this.isProcessing = false;
                this.showNotification('¡Proceso completado exitosamente!', 'success');
                break;
                
            case 'error':
                this.showNotification(`Error en el proceso: ${message}`, 'error');
                this.isProcessing = false;
                break;
        }
    }
    
    updateStepProgress(stepName, progress, message, status) {
        const progressFill = document.getElementById(`${stepName}-progress`);
        const messageElement = document.getElementById(`${stepName}-message`);
        const statusElement = document.getElementById(`${stepName}-status`);
        
        if (progressFill) {
            progressFill.style.width = `${Math.max(0, Math.min(100, progress * 100))}%`;
        }
        
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        if (statusElement) {
            statusElement.className = `step-status ${status}`;
            
            const icon = statusElement.querySelector('i');
            if (icon) {
                switch (status) {
                    case 'waiting':
                        icon.className = 'fas fa-clock';
                        break;
                    case 'active':
                        icon.className = 'fas fa-spinner fa-spin';
                        break;
                    case 'completed':
                        icon.className = 'fas fa-check';
                        break;
                }
            }
        }
    }
    
    updateOverallProgress(progress, message) {
        const progressFill = document.getElementById('overall-progress');
        const messageElement = document.getElementById('overall-message');
        
        if (progressFill) {
            progressFill.style.width = `${Math.max(0, Math.min(100, progress * 100))}%`;
        }
        
        if (messageElement) {
            messageElement.textContent = message;
        }
    }
    
    showResults(results) {
        if (!results || results.length === 0) {
            this.showNotification('No se generaron clips', 'warning');
            return;
        }
        
        // Mostrar área de resultados
        const resultsArea = document.getElementById('results-area');
        resultsArea.classList.remove('hidden');
        
        // Actualizar resumen
        this.updateResultsSummary(results);
        
        // Mostrar lista de clips
        this.displayClipsList(results);
        
        // Scroll a resultados
        resultsArea.scrollIntoView({ behavior: 'smooth' });
    }
    
    updateResultsSummary(results) {
        const clipsCount = document.getElementById('clips-count');
        const totalDuration = document.getElementById('total-duration');
        const totalSize = document.getElementById('total-size');
        
        if (clipsCount) {
            clipsCount.textContent = results.length;
        }
        
        if (totalDuration) {
            const duration = results.reduce((sum, clip) => sum + clip.duration, 0);
            totalDuration.textContent = this.formatDuration(duration);
        }
        
        if (totalSize) {
            const size = results.reduce((sum, clip) => sum + (clip.file_size || 0), 0);
            totalSize.textContent = this.formatFileSize(size);
        }
    }
    
    displayClipsList(results) {
        const clipsList = document.getElementById('clips-list');
        clipsList.innerHTML = '';
        
        results.forEach((clip, index) => {
            const clipElement = this.createClipElement(clip, index);
            clipsList.appendChild(clipElement);
        });
    }
    
    createClipElement(clip, index) {
        const clipDiv = document.createElement('div');
        clipDiv.className = 'clip-item';
        
        const fileName = clip.file_path.split('/').pop() || clip.file_path.split('\\').pop();
        
        clipDiv.innerHTML = `
            <div class="clip-info">
                <div class="clip-title">${clip.title}</div>
                <div class="clip-details">
                    <i class="fas fa-clock"></i> ${this.formatTime(clip.start_time)} - ${this.formatTime(clip.end_time)} 
                    (${this.formatDuration(clip.duration)})
                    <span style="margin-left: 15px;">
                        <i class="fas fa-hdd"></i> ${this.formatFileSize(clip.file_size || 0)}
                    </span>
                </div>
                <div class="clip-description">${clip.description}</div>
            </div>
            <div class="clip-actions">
                <a href="/api/download/${fileName}" 
                   class="btn-primary" 
                   download="${fileName}">
                    <i class="fas fa-download"></i> Descargar
                </a>
            </div>
        `;
        
        return clipDiv;
    }
    
    async downloadAllClips() {
        try {
            const response = await fetch('/api/output/files');
            const data = await response.json();
            
            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const link = document.createElement('a');
                    link.href = `/api/download/${file.name}`;
                    link.download = file.name;
                    link.click();
                });
                
                this.showNotification('Descargando todos los clips...', 'info');
            } else {
                this.showNotification('No hay clips para descargar', 'warning');
            }
        } catch (error) {
            console.error('Error descargando clips:', error);
            this.showNotification('Error al descargar clips', 'error');
        }
    }
    
    handleFileChange(event) {
        const file = event.target.files[0];
        const display = document.querySelector('.file-input-display span');
        
        if (file) {
            display.textContent = `${file.name} (${this.formatFileSize(file.size)})`;
        } else {
            display.textContent = 'Seleccionar video...';
        }
    }
    
    updateFileInputDisplay() {
        const fileInput = document.getElementById('video-file');
        const display = document.querySelector('.file-input-display');
        
        if (display) {
            display.addEventListener('click', () => {
                fileInput.click();
            });
        }
    }
    
    async validateSystem() {
        try {
            const response = await fetch('/api/system/validate');
            
            if (!response.ok) {
                console.warn('Error en validación del sistema:', response.status);
                return;
            }
            
            const data = await response.json();
            
            if (!data.valid) {
                const missing = data.missing_dependencies.join(', ');
                this.showNotification(
                    `Dependencias faltantes: ${missing}. Revisa la configuración.`, 
                    'warning'
                );
            }
        } catch (error) {
            console.error('Error validando sistema:', error);
        }
    }
    
    showProgressArea() {
        const progressArea = document.getElementById('progress-area');
        const controlPanel = document.getElementById('control-panel');
        
        progressArea.classList.remove('hidden');
        controlPanel.style.opacity = '0.5';
        controlPanel.style.pointerEvents = 'none';
        
        progressArea.scrollIntoView({ behavior: 'smooth' });
    }
    
    hideProgressArea() {
        const progressArea = document.getElementById('progress-area');
        const controlPanel = document.getElementById('control-panel');
        
        progressArea.classList.add('hidden');
        controlPanel.style.opacity = '1';
        controlPanel.style.pointerEvents = 'auto';
    }
    
    resetProgress() {
        // Resetear todas las barras de progreso
        const progressBars = document.querySelectorAll('.progress-fill, .overall-progress-fill');
        progressBars.forEach(bar => {
            bar.style.width = '0%';
        });
        
        // Resetear mensajes
        const messages = document.querySelectorAll('.step-message');
        messages.forEach(msg => {
            msg.textContent = 'Esperando...';
        });
        
        // Resetear estados
        const statuses = document.querySelectorAll('.step-status');
        statuses.forEach(status => {
            status.className = 'step-status waiting';
            const icon = status.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-clock';
            }
        });
        
        // Ocultar resultados
        const resultsArea = document.getElementById('results-area');
        resultsArea.classList.add('hidden');
    }
    
    resetApplication() {
        // Cerrar WebSocket si existe
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        // Resetear estado
        this.currentJobId = null;
        this.isProcessing = false;
        
        // Resetear UI
        this.hideProgressArea();
        this.resetProgress();
        
        // Resetear formulario
        const form = document.getElementById('process-form');
        form.reset();
        
        // Resetear display de archivo
        const display = document.querySelector('.file-input-display span');
        display.textContent = 'Seleccionar video...';
        
        // Scroll al inicio
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        this.showNotification('Aplicación reiniciada', 'info');
    }
    
    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        notifications.appendChild(notification);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    // Utilidades de formato
    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Inicializar aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new SCCAApp();
});