import json
import asyncio
import aiohttp
from typing import List, Dict, Callable, Optional
import logging
import re

logger = logging.getLogger(__name__)

class LLMAnalyzer:
    def __init__(self, api_url: str = "http://localhost:11434/v1/chat/completions"):
        self.api_url = api_url
        self.model_name = "mistral:7b-instruct"
        
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
Eres un experto editor de video especializado en crear clips temáticos de alta calidad.

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

INSTRUCCIONES:
Analiza la transcripción y identifica segmentos que cumplan con los siguientes criterios:
1. Relevancia temática con los temas especificados
2. Duración apropiada para el perfil seleccionado
3. Contenido completo y coherente
4. Valor para la audiencia objetivo

Para cada clip identificado, proporciona la siguiente información en formato JSON:
{{
  "clips": [
    {{
      "title": "Título descriptivo del clip",
      "start_time": tiempo_inicio_en_segundos,
      "end_time": tiempo_fin_en_segundos,
      "duration": duración_en_segundos,
      "description": "Descripción del contenido y por qué es relevante",
      "topics": ["tema1", "tema2"],
      "confidence": puntuación_de_confianza_0_a_1
    }}
  ]
}}

IMPORTANTE:
- Los tiempos deben ser precisos y basados en la transcripción
- Cada clip debe ser independiente y comprensible por sí mismo
- Prioriza calidad sobre cantidad
- Asegúrate de que los clips no se superpongan
- Incluye solo clips con confidence > 0.7
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
                if progress_callback:
                    progress = 0.3 + (0.6 * (i + 1) / len(chunks))
                    await progress_callback("analyzing", progress, f"Analizando segmento {i+1}/{len(chunks)}...")
                
                chunk_prompt = prompt.replace(transcription, chunk)
                clips = await self._query_llm(chunk_prompt)
                all_clips.extend(clips)
            
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
    
    async def _query_llm(self, prompt: str) -> List[Dict]:
        """
        Consulta al LLM local
        """
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, timeout=120) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        return self._parse_llm_response(content)
                    else:
                        logger.error(f"Error en LLM API: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error consultando LLM: {str(e)}")
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
        # Filtrar clips con confidence > 0.7
        filtered = [clip for clip in clips if clip.get("confidence", 0) > 0.7]
        
        # Ordenar por tiempo de inicio
        filtered.sort(key=lambda x: x.get("start_time", 0))
        
        # Eliminar superposiciones
        non_overlapping = []
        for clip in filtered:
            if not non_overlapping:
                non_overlapping.append(clip)
            else:
                last_clip = non_overlapping[-1]
                if clip["start_time"] >= last_clip["end_time"]:
                    non_overlapping.append(clip)
        
        return non_overlapping
    
    async def test_connection(self) -> bool:
        """
        Prueba la conexión con el LLM
        """
        try:
            test_payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=test_payload, timeout=10) as response:
                    return response.status == 200
        except:
            return False