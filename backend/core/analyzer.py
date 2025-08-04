import json
import asyncio
import aiohttp
from typing import List, Dict, Callable, Optional
import logging
import re

logger = logging.getLogger(__name__)

class LLMAnalyzer:
    def __init__(self, api_url: str = "http://localhost:11434/api/generate"):
        self.api_url = api_url
        self.model_name = "mistral:latest"
        self.tags_url = "http://localhost:11434/api/tags"
        
    def build_dynamic_prompt(self, context: str, topics: str, profile: str, transcription: str) -> str:
        """
        Construye un prompt dinámico basado en la configuración del usuario
        """
        topics_list = [topic.strip() for topic in topics.split(",") if topic.strip()]
        
        profile_instructions = {
            "Clips para Redes Sociales": {
                "duration": "15-60 segundos",
                "style": "dinámico y atractivo",
                "focus": "momentos virales, frases impactantes, contenido visual llamativo"
            },
            "Cápsulas Educativas": {
                "duration": "2-5 minutos", 
                "style": "educativo y estructurado",
                "focus": "conceptos completos, explicaciones claras, valor educativo"
            },
            "Archivo de Referencia": {
                "duration": "1-10 minutos",
                "style": "informativo y completo", 
                "focus": "información clave, datos importantes, referencias futuras"
            }
        }
        
        profile_config = profile_instructions.get(profile, profile_instructions["Clips para Redes Sociales"])
        
        prompt = f"""
Eres un experto analizador de contenido de video especializado en identificar clips valiosos. Tu misión es encontrar TODOS los segmentos potencialmente útiles de una transcripción.

CONTEXTO DEL VIDEO:
{context}

TEMAS DE INTERÉS:
{', '.join(topics_list)}

PERFIL DE SALIDA: {profile}
- Duración objetivo: {profile_config['duration']}
- Estilo: {profile_config['style']}
- Enfoque: {profile_config['focus']}

TRANSCRIPCIÓN COMPLETA:
{transcription}

IDENTIFICA CLIPS RELEVANTES considerando:

🎯 CRITERIOS DE SELECCIÓN:
- Segmentos que aborden directamente los temas de interés
- Momentos con información valiosa o insights únicos
- Explicaciones claras de conceptos importantes
- Ejemplos prácticos o casos de estudio
- Momentos de transición que conecten ideas
- Fragmentos con potencial educativo o informativo
- Segmentos con datos, estadísticas o hechos relevantes

📏 DURACIÓN ÓPTIMA:
- Clips cortos (15-45s): Para conceptos específicos o datos puntuales
- Clips medianos (45s-2min): Para explicaciones completas
- Clips largos (2-5min): Para análisis profundos o casos complejos

🔍 SÉ MUY INCLUSIVO:
- Incluye clips con confidence ≥ 0.3
- Prefiere tener más opciones que menos
- Los clips pueden superponerse si abordan aspectos diferentes
- Considera el valor educativo y la utilidad práctica

Para cada clip identificado, proporciona la siguiente información en formato JSON:
{{
  "clips": [
    {{
      "title": "Título descriptivo y atractivo del clip",
      "start_time": tiempo_inicio_en_segundos,
      "end_time": tiempo_fin_en_segundos,
      "duration": duración_en_segundos,
      "description": "Descripción detallada del valor y contenido del clip",
      "topics": ["tema1", "tema2"],
      "confidence": puntuación_de_confianza_0.3_a_1.0
    }}
  ]
}}

IMPORTANTE:
- Los tiempos deben ser precisos y basados en la transcripción
- Sé MUY generoso en la identificación de clips potencialmente útiles
- Incluye clips con confidence ≥ 0.3 para máxima diversidad
- Prioriza cantidad y diversidad para dar más opciones al usuario
- Los clips pueden superponerse si abordan diferentes aspectos
- Considera fragmentos cortos (15-30s) que puedan ser valiosos
- Incluye momentos de transición que conecten ideas importantes
- Enfócate en el valor educativo y la utilidad práctica de cada segmento
"""
        return prompt
    
    async def analyze_transcription(self, context: str, topics: str, profile: str, 
                                  transcription: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Analiza la transcripción usando el LLM local
        """
        try:
            if progress_callback:
                await progress_callback("analyzing", 0.1, "Construyendo prompt dinámico...")
            
            prompt = self.build_dynamic_prompt(context, topics, profile, transcription)
            
            if progress_callback:
                await progress_callback("analyzing", 0.3, "Enviando transcripción al LLM...")
            
            # Dividir transcripción en chunks si es muy larga
            chunks = self._split_transcription(transcription, max_tokens=3000)
            all_clips = []
            
            for i, chunk in enumerate(chunks):
                base_progress = 0.3 + (0.6 * i / len(chunks))
                segment_progress_range = 0.6 / len(chunks)
                
                if progress_callback:
                    await progress_callback("analyzing", base_progress, f"Iniciando análisis del segmento {i+1}/{len(chunks)}...")
                
                # Crear callback específico para este segmento
                async def segment_callback(status, prog, msg):
                    if progress_callback:
                        # Si prog es None, mantener el progreso base, sino interpolar
                        if prog is None:
                            segment_prog = base_progress
                        else:
                            segment_prog = base_progress + (segment_progress_range * prog)
                        await progress_callback(status, segment_prog, msg)
                
                chunk_prompt = prompt.replace(transcription, chunk)
                segment_info = f"({i+1}/{len(chunks)})"
                clips = await self._query_llm(chunk_prompt, progress_callback=segment_callback, segment_info=segment_info)
                all_clips.extend(clips)
                
                if progress_callback:
                    final_progress = 0.3 + (0.6 * (i + 1) / len(chunks))
                    await progress_callback("analyzing", final_progress, f"Segmento {i+1}/{len(chunks)} completado - {len(clips)} clips encontrados")
            
            if progress_callback:
                await progress_callback("analyzing", 0.9, "Procesando resultados...")
            
            # Filtrar y ordenar clips
            filtered_clips = self._filter_and_sort_clips(all_clips)
            
            if progress_callback:
                await progress_callback("analyzing", 1.0, f"Análisis completado. {len(filtered_clips)} clips identificados")
            
            return filtered_clips
            
        except Exception as e:
            logger.error(f"Error en análisis: {str(e)}")
            if progress_callback:
                await progress_callback("analyzing", 0.0, f"Error: {str(e)}")
            raise e
    
    def _split_transcription(self, transcription: str, max_tokens: int = 3000) -> List[str]:
        """
        Divide la transcripción en chunks manejables
        """
        words = transcription.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) > max_tokens and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    async def _query_llm(self, prompt: str, max_retries: int = 3, progress_callback: Optional[Callable] = None, segment_info: str = "") -> List[Dict]:
        """
        Consulta el LLM local con el prompt dado, con reintentos automáticos y progreso en tiempo real
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 2000
            }
        }
        
        for attempt in range(max_retries):
            try:
                # Usar timeout más largo y configuración específica
                timeout = aiohttp.ClientTimeout(total=300, connect=30, sock_read=270)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    if attempt > 0:
                        message = f"Reintentando análisis {segment_info} (intento {attempt + 1}/{max_retries})"
                        logger.info(message)
                        if progress_callback:
                            await progress_callback("analyzing", None, message)
                    else:
                        message = f"Consultando LLM {segment_info} con modelo: {self.model_name}"
                        logger.info(message)
                        if progress_callback:
                            await progress_callback("analyzing", None, message)
                    
                    async with session.post(self.api_url, json=payload) as response:
                        logger.info(f"Respuesta LLM: status={response.status}")
                        
                        if response.status == 200:
                            if progress_callback:
                                await progress_callback("analyzing", None, f"Procesando respuesta del LLM {segment_info}")
                            
                            result = await response.json()
                            content = result.get("response", "")
                            if content:
                                logger.info("Respuesta LLM procesada exitosamente")
                                return self._parse_llm_response(content)
                            else:
                                logger.error("Respuesta vacía del LLM")
                                if attempt == max_retries - 1:
                                    return []
                                continue
                        else:
                            logger.error(f"Error en LLM API: {response.status}")
                            if attempt == max_retries - 1:
                                return []
                            continue
                            
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError, aiohttp.ServerTimeoutError) as e:
                error_type = "conexión" if isinstance(e, aiohttp.ClientConnectorError) else "timeout"
                error_msg = f"Error de {error_type} con LLM (intento {attempt + 1}/{max_retries}): {e}"
                logger.error(error_msg)
                
                if progress_callback:
                    await progress_callback("analyzing", None, f"Timeout {segment_info} - reintentando...")
                
                if attempt == max_retries - 1:
                    logger.error(f"Falló después de {max_retries} intentos")
                    return []
                
                # Esperar antes del siguiente intento
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial: 1s, 2s, 4s
                
            except Exception as e:
                logger.error(f"Error inesperado consultando LLM: {type(e).__name__}: {e}")
                return []
        
        return []
    
    def _parse_llm_response(self, content: str) -> List[Dict]:
        """
        Parsea la respuesta del LLM para extraer clips
        """
        try:
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                return data.get("clips", [])
            else:
                logger.warning("No se encontró JSON válido en la respuesta del LLM")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {str(e)}")
            return []
    
    def _filter_and_sort_clips(self, clips: List[Dict]) -> List[Dict]:
        """
        Filtra y ordena los clips por calidad y relevancia
        """
        # Filtrar clips con confidence > 0.3 (más inclusivo para mayor diversidad)
        filtered = [clip for clip in clips if clip.get("confidence", 0) > 0.3]
        
        # Validar que los clips tengan duración mínima (5 segundos) y máxima (5 minutos)
        valid_clips = []
        for clip in filtered:
            duration = clip.get("end_time", 0) - clip.get("start_time", 0)
            if 5 <= duration <= 300:  # Entre 5 segundos y 5 minutos
                valid_clips.append(clip)
        
        # Ordenar por confidence primero, luego por tiempo de inicio
        valid_clips.sort(key=lambda x: (-x.get("confidence", 0), x.get("start_time", 0)))
        
        # Permitir superposiciones parciales (solo eliminar duplicados exactos)
        unique_clips = []
        for clip in valid_clips:
            # Solo eliminar si es exactamente el mismo clip (mismo inicio y fin)
            is_duplicate = any(
                abs(existing["start_time"] - clip["start_time"]) < 2 and 
                abs(existing["end_time"] - clip["end_time"]) < 2
                for existing in unique_clips
            )
            if not is_duplicate:
                unique_clips.append(clip)

        # Aumentar límite a 20 clips para mayor diversidad
        return unique_clips[:20]
    
    async def test_connection(self) -> bool:
        """
        Prueba la conexión con el LLM
        """
        try:
            test_payload = {
                "model": self.model_name,
                "prompt": "Hello",
                "stream": False
            }
            
            # Crear timeout más largo y con configuración específica
            timeout = aiohttp.ClientTimeout(total=180, connect=30, sock_read=150)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.info(f"Probando conexión con Ollama usando modelo: {self.model_name}")
                async with session.post(self.api_url, json=test_payload) as response:
                    logger.info(f"Respuesta de Ollama: status={response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info("Conexión con Ollama exitosa")
                        return 'response' in result
                    elif response.status == 404:
                        logger.error(f"Modelo '{self.model_name}' no encontrado en Ollama")
                        return False
                    else:
                        logger.error(f"Error HTTP {response.status} al conectar con Ollama")
                        return False
                        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"No se puede conectar a Ollama: {e}. Asegúrate de que esté ejecutándose en http://localhost:11434")
            return False
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout al conectar con Ollama: {e}")
            return False
        except aiohttp.ServerTimeoutError as e:
            logger.error(f"Timeout del servidor Ollama: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al probar conexión LLM: {type(e).__name__}: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """
        Obtiene la lista de modelos disponibles en Ollama
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.tags_url, timeout=15) as response:
                    if response.status == 200:
                        result = await response.json()
                        models = [model['name'] for model in result.get('models', [])]
                        return models
                    return []
        except Exception as e:
            logger.error(f"Error obteniendo modelos de Ollama: {e}")
            return []
    
    def change_model(self, model_name: str) -> bool:
        """
        Cambia el modelo LLM a usar
        """
        self.model_name = model_name
        logger.info(f"Modelo LLM cambiado a: {model_name}")
        return True