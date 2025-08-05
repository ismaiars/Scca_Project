#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar recortes usando el caché de análisis existente
"""

import asyncio
import json
import os
from pathlib import Path
from backend.core.cutter import VideoCutter
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def progress_callback(stage, progress, message):
    """Callback para mostrar el progreso"""
    print(f"[{stage.upper()}] {progress:.1%} - {message}")

async def cut_clips_from_cache(cache_file_path):
    """
    Genera recortes usando un archivo de caché existente
    """
    try:
        # Cargar el caché
        print(f"\n📁 Cargando caché: {cache_file_path}")
        with open(cache_file_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Mostrar información del caché
        print(f"\n📊 Información del caché:")
        print(f"   🎬 Video: {cache_data['video_path']}")
        print(f"   📅 Fecha: {cache_data['timestamp']}")
        print(f"   🎯 Contexto: {cache_data['analysis_params']['context']}")
        print(f"   📝 Temas: {cache_data['analysis_params']['topics']}")
        print(f"   👤 Perfil: {cache_data['analysis_params']['profile']}")
        print(f"   🎞️ Clips encontrados: {cache_data['clips_count']}")
        
        # Verificar que el video existe
        video_path = cache_data['video_path']
        if not os.path.exists(video_path):
            print(f"❌ Error: El video no existe en {video_path}")
            return
        
        # Mostrar lista de clips
        print(f"\n📋 Lista de clips a generar:")
        for i, clip in enumerate(cache_data['clips'], 1):
            duration_min = clip['duration'] // 60
            duration_sec = clip['duration'] % 60
            print(f"   {i:2d}. {clip['title']} ({duration_min}:{duration_sec:02d})")
        
        # Confirmar antes de proceder
        response = input(f"\n¿Deseas generar los {len(cache_data['clips'])} clips? (s/n): ")
        if response.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
            print("❌ Operación cancelada")
            return
        
        # Crear directorio de salida
        output_dir = Path("output/clips")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar el cortador
        cutter = VideoCutter(str(output_dir))
        
        # Generar los clips
        print(f"\n🎬 Iniciando generación de clips...")
        results = await cutter.cut_clips(
            video_path=video_path,
            clips=cache_data['clips'],
            progress_callback=progress_callback
        )
        
        # Mostrar resultados
        print(f"\n✅ Generación completada!")
        print(f"   📁 Clips generados: {len(results)}")
        print(f"   📂 Directorio: {output_dir.absolute()}")
        
        # Mostrar detalles de cada clip generado
        total_size = 0
        for i, result in enumerate(results, 1):
            size_mb = result['file_size'] / (1024 * 1024)
            total_size += result['file_size']
            print(f"   {i:2d}. {result['title']} - {size_mb:.1f} MB")
        
        total_size_mb = total_size / (1024 * 1024)
        print(f"\n📊 Tamaño total: {total_size_mb:.1f} MB")
        
    except Exception as e:
        logger.error(f"Error generando clips: {str(e)}")
        print(f"❌ Error: {str(e)}")

async def main():
    """
    Función principal
    """
    print("🎬 SCCA - Generador de Clips desde Caché")
    print("=" * 50)
    
    # Buscar archivos de caché disponibles
    cache_dir = Path("output/analysis_cache")
    if not cache_dir.exists():
        print("❌ No se encontró el directorio de caché")
        return
    
    cache_files = list(cache_dir.glob("*_analysis.json"))
    if not cache_files:
        print("❌ No se encontraron archivos de caché")
        return
    
    # Ordenar por fecha de modificación (más reciente primero)
    cache_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"\n📁 Archivos de caché disponibles:")
    for i, cache_file in enumerate(cache_files, 1):
        # Cargar información básica
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            timestamp = data['timestamp'][:19].replace('T', ' ')
            clips_count = data['clips_count']
            context = data['analysis_params']['context'][:50] + "..." if len(data['analysis_params']['context']) > 50 else data['analysis_params']['context']
            print(f"   {i}. {cache_file.name} - {timestamp} - {clips_count} clips")
            print(f"      Contexto: {context}")
        except:
            print(f"   {i}. {cache_file.name} - (Error leyendo archivo)")
    
    # Seleccionar archivo
    try:
        selection = input(f"\nSelecciona el archivo de caché (1-{len(cache_files)}) o Enter para el más reciente: ")
        if selection.strip() == "":
            selected_file = cache_files[0]
        else:
            index = int(selection) - 1
            if 0 <= index < len(cache_files):
                selected_file = cache_files[index]
            else:
                print("❌ Selección inválida")
                return
    except ValueError:
        print("❌ Selección inválida")
        return
    
    # Generar clips
    await cut_clips_from_cache(selected_file)

if __name__ == "__main__":
    asyncio.run(main())