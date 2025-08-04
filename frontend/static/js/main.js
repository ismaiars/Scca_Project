// Sistema de Creación de Contenido Automatizado (SCCA)
// Frontend JavaScript

class SCCAApp {
    constructor() {
        this.currentJobId = null;
        this.websocket = null;
        this.isProcessing = false;
    }
    
    init() {
        this.bindEvents();
        this.updateFileInputDisplay();
        this.validateSystem();
    }
    
    bindEvents() {
        console.log('Iniciando bindEvents...');
        
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
        
        // Configurar botón de transcripciones
        const transcriptionsBtn = document.getElementById('transcriptions-btn');
        console.log('Botón de transcripciones encontrado:', transcriptionsBtn);
        if (transcriptionsBtn) {
            console.log('Agregando evento click al botón de transcripciones');
            transcriptionsBtn.addEventListener('click', this.showTranscriptions.bind(this));
        } else {
            console.error('ERROR: Botón de transcripciones no encontrado');
        }
        
        // Botón de configuración de Whisper
        const whisperSettingsBtn = document.getElementById('whisper-settings-btn');
        console.log('Whisper settings button found:', whisperSettingsBtn);
        if (whisperSettingsBtn) {
            whisperSettingsBtn.addEventListener('click', () => {
                console.log('Whisper settings button clicked');
                this.showWhisperSettings();
            });
        } else {
            console.error('Whisper settings button not found!');
        }
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
        
        if (videoFile.size > 2 * 1024 * 1024 * 1024) { // 2GB
            this.showNotification('El archivo es demasiado grande (máximo 2GB)', 'error');
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
        const { status, progress, message, results, time_info } = data;
        
        // Actualizar progreso general con información de tiempo
        this.updateOverallProgress(progress, message, time_info);
        
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
    
    updateOverallProgress(progress, message, timeInfo = null) {
        const progressFill = document.getElementById('overall-progress');
        const messageElement = document.getElementById('overall-message');
        
        if (progressFill) {
            progressFill.style.width = `${Math.max(0, Math.min(100, progress * 100))}%`;
        }
        
        if (messageElement) {
            let displayMessage = message;
            
            // Agregar información de tiempo si está disponible
            if (timeInfo) {
                const { elapsed, remaining, current_stage, stage_progress, avg_speed } = timeInfo;
                const elapsedStr = this.formatDuration(elapsed);
                const remainingStr = this.formatDuration(remaining);
                
                displayMessage += ` | Etapa: ${current_stage}`;
                if (stage_progress !== undefined) {
                    displayMessage += ` (${Math.round(stage_progress * 100)}%)`;
                }
                displayMessage += ` | Transcurrido: ${elapsedStr}`;
                
                if (remaining > 0) {
                    displayMessage += ` | Restante: ${remainingStr}`;
                }
                
                if (avg_speed && avg_speed > 0) {
                    displayMessage += ` | Velocidad: ${avg_speed}%/s`;
                }
            }
            
            messageElement.textContent = displayMessage;
        }
        
        // Actualizar información de estimaciones si está disponible
        this.updateTimeEstimates(timeInfo);
    }
    
    updateTimeEstimates(timeInfo) {
        if (!timeInfo || !timeInfo.stage_estimates) return;
        
        const estimatesContainer = document.getElementById('time-estimates');
        if (!estimatesContainer) {
            // Crear contenedor de estimaciones si no existe
            this.createTimeEstimatesContainer();
            return this.updateTimeEstimates(timeInfo);
        }
        
        const { stage_estimates, current_stage, elapsed, remaining } = timeInfo;
        
        // Actualizar estimaciones por etapa
        const stages = [
            { key: 'transcription', name: 'Transcripción', icon: '🎤' },
            { key: 'analysis', name: 'Análisis con IA', icon: '🧠' },
            { key: 'cutting', name: 'Corte de clips', icon: '✂️' }
        ];
        
        let estimatesHTML = '<div class="time-estimates-header"><h4>⏱️ Estimaciones de Tiempo</h4></div>';
        estimatesHTML += '<div class="stages-grid">';
        
        stages.forEach(stage => {
            const estimate = stage_estimates[stage.key] || 0;
            const isActive = current_stage.toLowerCase().includes(stage.name.toLowerCase().split(' ')[0]);
            const statusClass = isActive ? 'active' : 'pending';
            
            estimatesHTML += `
                <div class="stage-estimate ${statusClass}">
                    <div class="stage-icon">${stage.icon}</div>
                    <div class="stage-info">
                        <div class="stage-name">${stage.name}</div>
                        <div class="stage-time">${this.formatDuration(estimate)}</div>
                    </div>
                </div>
            `;
        });
        
        estimatesHTML += '</div>';
        estimatesHTML += `
            <div class="total-estimate">
                <div class="estimate-row">
                    <span>⏱️ Tiempo total estimado:</span>
                    <span class="time-value">${this.formatDuration(stage_estimates.total || 0)}</span>
                </div>
                <div class="estimate-row">
                    <span>⏳ Tiempo transcurrido:</span>
                    <span class="time-value">${this.formatDuration(elapsed || 0)}</span>
                </div>
                <div class="estimate-row">
                    <span>⏰ Tiempo restante:</span>
                    <span class="time-value">${this.formatDuration(remaining || 0)}</span>
                </div>
            </div>
        `;
        
        estimatesContainer.innerHTML = estimatesHTML;
    }
    
    createTimeEstimatesContainer() {
        const progressArea = document.querySelector('.progress-area');
        if (!progressArea) return;
        
        const estimatesContainer = document.createElement('div');
        estimatesContainer.id = 'time-estimates';
        estimatesContainer.className = 'time-estimates-container';
        
        // Insertar después del progreso general
        const overallProgress = document.querySelector('.overall-progress');
        if (overallProgress && overallProgress.parentNode) {
            overallProgress.parentNode.insertBefore(estimatesContainer, overallProgress.nextSibling);
        } else {
            progressArea.appendChild(estimatesContainer);
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
    
    async handleFileChange(event) {
        const file = event.target.files[0];
        const display = document.querySelector('.file-input-display span');
        
        if (file) {
            // Mostrar información inicial
            display.textContent = `${file.name} (Analizando...)`;
            
            try {
                // Obtener información real del video
                const formData = new FormData();
                formData.append('video_file', file);
                
                const response = await fetch('/api/video/info', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const videoInfo = await response.json();
                    const realSize = this.formatFileSize(videoInfo.file_size);
                    const duration = this.formatDuration(videoInfo.duration || 0);
                    display.textContent = `${file.name} (${realSize}, ${duration})`;
                } else {
                    // Fallback al tamaño del archivo JS
                    display.textContent = `${file.name} (${this.formatFileSize(file.size)})`;
                }
            } catch (error) {
                console.error('Error obteniendo información del video:', error);
                // Fallback al tamaño del archivo JS
                display.textContent = `${file.name} (${this.formatFileSize(file.size)})`;
            }
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
                
                // Verificar específicamente si falta conexión LLM
                if (data.missing_dependencies.includes('llm_connection')) {
                    this.showNotification(
                        '⚠️ Ollama no está disponible. Instala Ollama desde https://ollama.com para usar análisis IA.', 
                        'warning'
                    );
                } else {
                    this.showNotification(
                        `Dependencias faltantes: ${missing}. Revisa la configuración.`, 
                        'warning'
                    );
                }
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
        if (!bytes || isNaN(bytes)) return 'Tamaño desconocido';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        // Asegurar que el índice esté dentro del rango
        const index = Math.min(i, sizes.length - 1);
        const size = (bytes / Math.pow(k, index)).toFixed(2);
        
        return `${size} ${sizes[index]}`;
    }
    
    async showTranscriptions() {
        console.log('showTranscriptions() llamada');
        try {
            console.log('Haciendo fetch a /api/transcriptions');
            const response = await fetch('/api/transcriptions');
            const data = await response.json();
            console.log('Datos recibidos:', data);
            
            if (data.transcriptions && data.transcriptions.length > 0) {
                this.displayTranscriptionsList(data.transcriptions);
            } else {
                this.showNotification('No hay transcripciones guardadas', 'info');
            }
        } catch (error) {
            console.error('Error cargando transcripciones:', error);
            this.showNotification('Error al cargar transcripciones', 'error');
        }
    }
    
    displayTranscriptionsList(transcriptions) {
        const resultsContainer = document.getElementById('results-container');
        resultsContainer.style.display = 'block';
        resultsContainer.classList.remove('hidden');
        
        const resultsContent = document.getElementById('results-content');
        resultsContent.innerHTML = `
            <div class="transcriptions-header">
                <h3>📝 Transcripciones Guardadas</h3>
                <p>Total: ${transcriptions.length} transcripciones</p>
            </div>
            <div class="transcriptions-list">
                ${transcriptions.map(transcript => this.createTranscriptionElement(transcript)).join('')}
            </div>
        `;
    }
    
    createTranscriptionElement(transcript) {
        const date = new Date(transcript.timestamp).toLocaleString('es-ES');
        const duration = this.formatDuration(transcript.duration);
        
        return `
            <div class="transcription-item">
                <div class="transcription-info">
                    <h4>📹 ${transcript.filename}</h4>
                    <div class="transcription-meta">
                        <span class="meta-item">📅 ${date}</span>
                        <span class="meta-item">⏱️ ${duration}</span>
                        <span class="meta-item">🆔 ${transcript.job_id}</span>
                    </div>
                </div>
                <div class="transcription-actions">
                    <button class="btn btn-secondary" onclick="app.viewTranscription('${transcript.job_id}')">
                        👁️ Ver Transcripción
                    </button>
                    <button class="btn btn-success" onclick="app.reuseTranscription('${transcript.job_id}')">
                        🔄 Reutilizar para Análisis
                    </button>
                    <button class="btn btn-primary" onclick="app.downloadTranscription('${transcript.job_id}')">
                        💾 Descargar
                    </button>
                </div>
            </div>
        `;
    }
    
    async viewTranscription(jobId) {
        try {
            const response = await fetch(`/api/transcriptions/${jobId}`);
            const data = await response.json();
            
            this.showTranscriptionModal(data);
        } catch (error) {
            console.error('Error cargando transcripción:', error);
            this.showNotification('Error al cargar transcripción', 'error');
        }
    }
    
    showTranscriptionModal(data) {
        const modal = document.createElement('div');
        modal.className = 'transcription-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>📝 Transcripción - ${data.video_info.filename}</h3>
                    <button class="close-btn" onclick="this.parentElement.parentElement.parentElement.remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="video-info">
                        <h4>📹 Información del Video</h4>
                        <div class="info-grid">
                            <div><strong>Archivo:</strong> ${data.video_info.filename}</div>
                            <div><strong>Duración:</strong> ${this.formatDuration(data.video_info.duration)}</div>
                            <div><strong>Resolución:</strong> ${data.video_info.width}x${data.video_info.height}</div>
                            <div><strong>Codec:</strong> ${data.video_info.video_codec}</div>
                            <div><strong>Tamaño:</strong> ${this.formatFileSize(data.video_info.file_size)}</div>
                            <div><strong>FPS:</strong> ${data.video_info.fps?.toFixed(2) || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="transcription-content">
                        <h4>📄 Transcripción</h4>
                        <div class="transcription-text">
                            ${data.transcription.replace(/\n/g, '<br>')}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="app.downloadTranscription('${data.job_id}')">
                        💾 Descargar Transcripción
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    async downloadTranscription(jobId) {
        try {
            const response = await fetch(`/api/transcriptions/${jobId}`);
            const data = await response.json();
            
            // Crear archivo de texto para descargar
            const blob = new Blob([data.transcription], { type: 'text/plain;charset=utf-8' });
            const url = window.URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `${data.video_info.filename}_transcription.txt`;
            link.click();
            
            window.URL.revokeObjectURL(url);
            this.showNotification('Transcripción descargada', 'success');
        } catch (error) {
            console.error('Error descargando transcripción:', error);
            this.showNotification('Error al descargar transcripción', 'error');
        }
    }
    
    async reuseTranscription(jobId) {
        try {
            // Obtener datos de la transcripción
            const response = await fetch(`/api/transcriptions/${jobId}`);
            const data = await response.json();
            
            // Crear modal para configurar nuevo análisis
            const modal = document.createElement('div');
            modal.className = 'transcription-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🔄 Reutilizar Transcripción - ${data.video_info.filename}</h3>
                        <button class="close-btn" onclick="this.parentElement.parentElement.parentElement.remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="video-info">
                            <h4>📹 Video Original</h4>
                            <div class="info-grid">
                                <div><strong>Archivo:</strong> ${data.video_info.filename}</div>
                                <div><strong>Duración:</strong> ${this.formatDuration(data.video_info.duration)}</div>
                                <div><strong>Resolución:</strong> ${data.video_info.width}x${data.video_info.height}</div>
                            </div>
                        </div>
                        <form id="reuse-form">
                            <div class="form-group">
                                <label for="reuse-context">🎯 Contexto del Video:</label>
                                <textarea id="reuse-context" name="context" rows="3" placeholder="Describe el contexto del video..." required></textarea>
                            </div>
                            <div class="form-group">
                                <label for="reuse-topics">📝 Temas de Interés:</label>
                                <textarea id="reuse-topics" name="topics" rows="3" placeholder="Especifica los temas que te interesan..." required></textarea>
                            </div>
                            <div class="form-group">
                                <label for="reuse-profile">⚙️ Perfil de Salida:</label>
                                <select id="reuse-profile" name="profile" required>
                                    <option value="">Selecciona un perfil</option>
                                    <option value="Clips para Redes Sociales">📱 Clips para Redes Sociales</option>
                                    <option value="Cápsulas Educativas">🎓 Cápsulas Educativas</option>
                                    <option value="Archivo de Referencia">📋 Archivo de Referencia</option>
                                </select>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="this.parentElement.parentElement.parentElement.remove()">Cancelar</button>
                        <button class="btn btn-success" onclick="app.startReuseProcess('${jobId}')">🚀 Iniciar Análisis</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        } catch (error) {
            console.error('Error al cargar transcripción:', error);
            this.showNotification('Error al cargar transcripción', 'error');
        }
    }
    
    async startReuseProcess(transcriptionJobId) {
        try {
            const form = document.getElementById('reuse-form');
            const formData = new FormData(form);
            
            // Validar campos requeridos
            if (!formData.get('context') || !formData.get('topics') || !formData.get('profile')) {
                this.showNotification('Por favor completa todos los campos', 'error');
                return;
            }
            
            // Cerrar modal
            document.querySelector('.transcription-modal').remove();
            
            // Mostrar área de progreso
            this.showProgressArea();
            this.resetProgress();
            
            // Agregar transcription_job_id al FormData
            formData.append('transcription_job_id', transcriptionJobId);
            
            // Enviar solicitud al backend
            const response = await fetch('/api/start_process_with_transcription', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al iniciar procesamiento');
            }
            
            const data = await response.json();
            this.currentJobId = data.job_id;
            
            // Conectar WebSocket para seguimiento
            this.connectWebSocket();
            
            this.showNotification('Procesamiento iniciado con transcripción existente', 'success');
            
        } catch (error) {
            console.error('Error al iniciar procesamiento:', error);
            this.showNotification(error.message || 'Error al iniciar procesamiento', 'error');
            this.hideProgressArea();
        }
    }
    
    async showWhisperSettings() {
        try {
            console.log('showWhisperSettings called');
            
            // Remover modal existente si existe
            const existingModal = document.querySelector('.whisper-modal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Obtener información de modelos
            console.log('Fetching whisper models...');
            const response = await fetch('/api/whisper/models');
            console.log('Response received:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Data parsed:', data);
            
            // Crear modal de configuración con estilos inline para asegurar visibilidad
            const modal = document.createElement('div');
            modal.className = 'whisper-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
            `;
            
            const modalContent = document.createElement('div');
            modalContent.style.cssText = `
                background: white;
                border-radius: 8px;
                padding: 20px;
                max-width: 600px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            `;
            
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
                    <h3 style="margin: 0; color: #333;">⚙️ Configuración de Velocidad de Transcripción</h3>
                    <button onclick="this.closest('.whisper-modal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999;">&times;</button>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h4 style="color: #007bff;">🎯 Modelo Actual: ${data.current_model.model_name.toUpperCase()}</h4>
                    <p style="color: #666; margin: 10px 0;">Selecciona un modelo según tus necesidades de velocidad vs calidad:</p>
                </div>
                
                <div id="models-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px;">
                    ${Object.entries(data.available_models).map(([name, info]) => `
                        <div class="model-option" data-model="${name}" style="
                            border: 2px solid ${name === data.current_model.model_name ? '#007bff' : '#ddd'};
                            border-radius: 8px;
                            padding: 15px;
                            cursor: pointer;
                            background: ${name === data.current_model.model_name ? '#f0f8ff' : 'white'};
                            transition: all 0.3s ease;
                        " onclick="this.parentElement.querySelectorAll('.model-option').forEach(el => {el.style.border='2px solid #ddd'; el.style.background='white';}); this.style.border='2px solid #007bff'; this.style.background='#f0f8ff'; window.selectedModel='${name}';">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <h5 style="margin: 0; color: #333;">${name.toUpperCase()}</h5>
                                <span style="background: #007bff; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">${info.size}</span>
                            </div>
                            <div style="font-size: 14px; color: #666;">
                                <div style="margin: 5px 0;"><strong>⚡ Velocidad:</strong> ${info.speed}</div>
                                <div style="margin: 5px 0;"><strong>🎯 Precisión:</strong> ${info.accuracy}</div>
                                <div style="margin: 5px 0;"><strong>💡 Recomendado para:</strong> ${info.recommended_for}</div>
                            </div>
                            ${name === data.current_model.model_name ? '<div style="background: #28a745; color: white; padding: 5px; border-radius: 4px; text-align: center; margin-top: 10px; font-size: 12px;">✅ MODELO ACTUAL</div>' : ''}
                        </div>
                    `).join('')}
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">🚀 Guía de Velocidad:</h4>
                    <div style="font-size: 14px; color: #666;">
                        <p style="margin: 5px 0;"><strong>TINY</strong> - Más rápido, menor calidad (ideal para pruebas)</p>
                        <p style="margin: 5px 0;"><strong>BASE</strong> - Balance perfecto velocidad/calidad (recomendado)</p>
                        <p style="margin: 5px 0;"><strong>SMALL+</strong> - Máxima calidad, más lento</p>
                    </div>
                </div>
                
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button onclick="this.closest('.whisper-modal').remove()" style="padding: 10px 20px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer;">Cancelar</button>
                    <button onclick="app.applyWhisperModelChange()" style="padding: 10px 20px; border: none; background: #007bff; color: white; border-radius: 4px; cursor: pointer;">💾 Aplicar Cambios</button>
                </div>
            `;
            
            modal.appendChild(modalContent);
            document.body.appendChild(modal);
            
            // Inicializar modelo seleccionado
            window.selectedModel = data.current_model.model_name;
            
            console.log('Modal created and added to DOM');
            
            // Agregar event listeners para selección de modelo
            const modelCards = modal.querySelectorAll('.model-card');
            modelCards.forEach(card => {
                card.addEventListener('click', () => {
                    // Remover selección anterior
                    modelCards.forEach(c => c.classList.remove('selected'));
                    // Agregar selección actual
                    card.classList.add('selected');
                });
            });
            
        } catch (error) {
            console.error('Error cargando configuración Whisper:', error);
            this.showNotification('Error al cargar configuración', 'error');
        }
    }
    
    async applyWhisperModelChange() {
        try {
            console.log('applyWhisperModelChange called');
            const selectedModel = window.selectedModel;
            
            if (!selectedModel) {
                this.showNotification('Por favor, selecciona un modelo', 'warning');
                return;
            }
            
            console.log('Changing model to:', selectedModel);
            
            // Enviar solicitud para cambiar modelo
            const response = await fetch('/api/whisper/change_model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ model_name: selectedModel })
            });
            
            console.log('Change model response:', response.status);
            const data = await response.json();
            console.log('Change model data:', data);
            
            if (data.success) {
                this.showNotification(`Modelo cambiado a ${selectedModel.toUpperCase()} correctamente`, 'success');
                document.querySelector('.whisper-modal').remove();
            } else {
                this.showNotification(`Error al cambiar modelo: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error cambiando modelo:', error);
            this.showNotification('Error al cambiar el modelo', 'error');
        }
    }
    
    // Mantener la función original para compatibilidad
    async changeWhisperModel() {
        try {
            const modal = document.querySelector('.transcription-modal');
            const selectedCard = modal?.querySelector('.model-card.active');
            
            if (!selectedCard) {
                // Si estamos usando la nueva interfaz
                if (window.selectedModel) {
                    return this.applyWhisperModelChange();
                }
                
                this.showNotification('Por favor, selecciona un modelo', 'warning');
                return;
            }
            
            const modelName = selectedCard.dataset.model;
            
            // Enviar solicitud para cambiar modelo
            const response = await fetch('/api/whisper/change_model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ model_name: modelName })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Modelo cambiado a ${modelName.toUpperCase()} correctamente`, 'success');
                modal.remove();
            } else {
                this.showNotification(`Error al cambiar modelo: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error cambiando modelo:', error);
            this.showNotification('Error al cambiar el modelo', 'error');
        }
    }
    

}

// Crear instancia global de la aplicación
const app = new SCCAApp();

// Inicializar aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});