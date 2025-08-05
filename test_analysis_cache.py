#!/usr/bin/env python3
"""
Script de prueba para el sistema de caché de análisis
"""

import asyncio
import json
import os
from pathlib import Path
from backend.core.job_manager import JobManager
from backend.core.transcriber import WhisperTranscriber
from backend.core.analyzer import LLMAnalyzer
from backend.core.cutter import VideoCutter

async def test_analysis_cache():
    """
    Prueba el sistema de caché de análisis
    """
    print("🧪 INICIANDO PRUEBA DEL SISTEMA DE CACHÉ DE ANÁLISIS")
    print("=" * 60)
    
    # Buscar video más reciente
    videos_dir = Path("output/videos")
    if not videos_dir.exists():
        print("❌ No se encontró el directorio de videos")
        return
    
    video_files = list(videos_dir.glob("*.mp4"))
    if not video_files:
        print("❌ No se encontraron videos para probar")
        return
    
    # Usar el video más reciente
    video_path = str(max(video_files, key=os.path.getmtime))
    print(f"📹 Video seleccionado: {video_path}")
    
    # Inicializar componentes
    job_manager = JobManager()
    
    # Parámetros de prueba
    test_params = {
        "context": "Video de prueba para sistema de caché",
        "topics": "tecnología, programación, desarrollo",
        "profile": "Clips para Redes Sociales"
    }
    
    print(f"\n📋 Parámetros de análisis:")
    print(f"   Contexto: {test_params['context']}")
    print(f"   Temas: {test_params['topics']}")
    print(f"   Perfil: {test_params['profile']}")
    
    # Simular transcripción (usar una simple para la prueba)
    transcription = "Este es un video de prueba sobre tecnología y programación. Hablamos sobre desarrollo de software y las mejores prácticas en el campo de la tecnología moderna."
    
    print(f"\n📝 Transcripción simulada: {transcription[:100]}...")
    
    # Generar clave de caché
    cache_key = job_manager._generate_analysis_cache_key(
        video_path,
        transcription,
        test_params["context"],
        test_params["topics"],
        test_params["profile"]
    )
    
    print(f"\n🔑 Clave de caché generada: {cache_key}")
    
    # Verificar si existe caché
    print("\n🔍 VERIFICANDO CACHÉ EXISTENTE...")
    cached_clips = await job_manager._load_analysis_cache(cache_key)
    
    if cached_clips:
        print(f"✅ Caché encontrado: {len(cached_clips)} clips")
        print("📋 Clips en caché:")
        for i, clip in enumerate(cached_clips[:3], 1):  # Mostrar solo los primeros 3
            print(f"   {i}. {clip.get('title', 'Sin título')} ({clip.get('duration', 0):.1f}s)")
        if len(cached_clips) > 3:
            print(f"   ... y {len(cached_clips) - 3} clips más")
    else:
        print("❌ No se encontró caché existente")
        
        # Crear clips de prueba para simular análisis
        print("\n🧠 SIMULANDO ANÁLISIS Y CREANDO CACHÉ...")
        
        test_clips = [
            {
                "title": "Introducción a la Tecnología",
                "description": "Clip sobre conceptos básicos de tecnología",
                "start_time": 0.0,
                "end_time": 30.0,
                "duration": 30.0,
                "relevance_score": 0.9,
                "topics": ["tecnología"],
                "segment_id": 1
            },
            {
                "title": "Desarrollo de Software",
                "description": "Clip sobre mejores prácticas en programación",
                "start_time": 30.0,
                "end_time": 60.0,
                "duration": 30.0,
                "relevance_score": 0.85,
                "topics": ["programación", "desarrollo"],
                "segment_id": 2
            },
            {
                "title": "Tecnología Moderna",
                "description": "Clip sobre tendencias actuales en tecnología",
                "start_time": 60.0,
                "end_time": 90.0,
                "duration": 30.0,
                "relevance_score": 0.8,
                "topics": ["tecnología"],
                "segment_id": 3
            }
        ]
        
        # Guardar en caché
        await job_manager._save_analysis_cache(
            cache_key,
            test_clips,
            "test_job_123",
            video_path,
            test_params["context"],
            test_params["topics"],
            test_params["profile"]
        )
        
        print(f"✅ Caché creado con {len(test_clips)} clips de prueba")
    
    # Verificar caché después de crearlo
    print("\n🔍 VERIFICANDO CACHÉ DESPUÉS DE CREACIÓN...")
    cached_clips_after = await job_manager._load_analysis_cache(cache_key)
    
    if cached_clips_after:
        print(f"✅ Caché verificado: {len(cached_clips_after)} clips")
    else:
        print("❌ Error: No se pudo verificar el caché")
    
    # Mostrar información del directorio de caché
    print("\n📁 INFORMACIÓN DEL DIRECTORIO DE CACHÉ:")
    cache_dir = Path("output/analysis_cache")
    
    if cache_dir.exists():
        cache_files = list(cache_dir.glob("*_analysis.json"))
        print(f"   Directorio: {cache_dir}")
        print(f"   Archivos de caché: {len(cache_files)}")
        
        total_size = sum(f.stat().st_size for f in cache_files)
        print(f"   Tamaño total: {total_size / 1024:.2f} KB")
        
        if cache_files:
            print("   Archivos:")
            for cache_file in cache_files:
                size_kb = cache_file.stat().st_size / 1024
                print(f"     - {cache_file.name} ({size_kb:.2f} KB)")
    else:
        print("   ❌ Directorio de caché no existe")
    
    # Probar limpieza de caché antiguo (comentado para mantener el caché)
    print("\n🧹 LIMPIEZA DE CACHÉ OMITIDA PARA VERIFICACIÓN...")
    # job_manager._cleanup_old_cache(max_age_days=0)  # Limpiar todo para la prueba
    
    print("\n✅ PRUEBA DEL SISTEMA DE CACHÉ COMPLETADA")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_analysis_cache())