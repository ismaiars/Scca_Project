#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar la generación de clips
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from backend.core.cutter import VideoCutter
import logging

# Configurar logging detallado
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_single_clip():
    """
    Prueba generar un solo clip para diagnóstico
    """
    print("🔍 Diagnóstico de generación de clips")
    print("=" * 50)
    
    # Cargar el caché más reciente
    cache_dir = Path("output/analysis_cache")
    cache_files = list(cache_dir.glob("*_analysis.json"))
    if not cache_files:
        print("❌ No hay archivos de caché")
        return
    
    cache_file = max(cache_files, key=lambda x: x.stat().st_mtime)
    print(f"📁 Usando caché: {cache_file.name}")
    
    with open(cache_file, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
    
    video_path = cache_data['video_path']
    print(f"🎬 Video: {video_path}")
    print(f"📁 Existe: {os.path.exists(video_path)}")
    
    if not os.path.exists(video_path):
        print("❌ El video no existe")
        return
    
    # Verificar FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        print(f"✅ FFmpeg disponible: {result.stdout.split()[2]}")
    except FileNotFoundError:
        print("❌ FFmpeg no encontrado")
        return
    
    # Crear directorio de prueba
    test_dir = Path("output/test_clips")
    test_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 Directorio de prueba: {test_dir.absolute()}")
    
    # Tomar el primer clip
    first_clip = cache_data['clips'][0]
    print(f"\n🎞️ Clip de prueba:")
    print(f"   Título: {first_clip['title']}")
    print(f"   Inicio: {first_clip['start_time']}s")
    print(f"   Duración: {first_clip['duration']}s")
    
    # Crear cutter
    cutter = VideoCutter(str(test_dir))
    
    try:
        print(f"\n🔄 Generando clip de prueba...")
        
        # Generar solo un clip
        results = await cutter.cut_clips(
            video_path=video_path,
            clips=[first_clip],
            progress_callback=None
        )
        
        print(f"\n📊 Resultados:")
        print(f"   Clips generados: {len(results)}")
        
        if results:
            result = results[0]
            print(f"   Archivo: {result['file_path']}")
            print(f"   Existe: {os.path.exists(result['file_path'])}")
            print(f"   Tamaño: {result['file_size']} bytes")
            
            if os.path.exists(result['file_path']):
                actual_size = os.path.getsize(result['file_path'])
                print(f"   Tamaño real: {actual_size} bytes")
                print(f"✅ Clip generado exitosamente")
            else:
                print(f"❌ El archivo no existe en el sistema")
        else:
            print(f"❌ No se generaron clips")
        
        # Listar archivos en el directorio
        print(f"\n📁 Contenido del directorio:")
        for item in test_dir.iterdir():
            if item.is_file():
                size = item.stat().st_size
                print(f"   📄 {item.name} - {size} bytes")
            else:
                print(f"   📁 {item.name}/")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logger.exception("Error detallado:")

async def test_ffmpeg_direct():
    """
    Prueba FFmpeg directamente
    """
    print(f"\n🔧 Prueba directa de FFmpeg")
    print("=" * 30)
    
    # Cargar datos del caché
    cache_dir = Path("output/analysis_cache")
    cache_files = list(cache_dir.glob("*_analysis.json"))
    if not cache_files:
        return
    
    cache_file = max(cache_files, key=lambda x: x.stat().st_mtime)
    with open(cache_file, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
    
    video_path = cache_data['video_path']
    first_clip = cache_data['clips'][0]
    
    # Crear directorio de prueba
    test_dir = Path("output/test_clips")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = test_dir / "test_direct.mp4"
    
    # Comando FFmpeg directo
    cmd = [
        'ffmpeg',
        '-ss', str(first_clip['start_time']),
        '-t', str(first_clip['duration']),
        '-i', video_path,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'medium',
        '-crf', '23',
        str(output_file),
        '-y'
    ]
    
    print(f"🔧 Comando: {' '.join(cmd)}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        print(f"📤 Código de salida: {process.returncode}")
        
        if stderr:
            stderr_text = stderr.decode()
            print(f"📝 Stderr: {stderr_text[-500:]}")
        
        if stdout:
            stdout_text = stdout.decode()
            print(f"📝 Stdout: {stdout_text[-500:]}")
        
        if output_file.exists():
            size = output_file.stat().st_size
            print(f"✅ Archivo creado: {output_file.name} ({size} bytes)")
        else:
            print(f"❌ Archivo no creado")
            
    except Exception as e:
        print(f"❌ Error ejecutando FFmpeg: {str(e)}")

async def main():
    await test_single_clip()
    await test_ffmpeg_direct()

if __name__ == "__main__":
    asyncio.run(main())