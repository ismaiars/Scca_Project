#!/usr/bin/env python3
"""
Script de prueba para verificar que todos los componentes del sistema SCCA funcionen correctamente
"""

import asyncio
import aiohttp
import sys
import os
from pathlib import Path

# Agregar el directorio backend al path
sys.path.append(str(Path(__file__).parent / "backend"))

from backend.core.transcriber import WhisperTranscriber
from backend.core.analyzer import LLMAnalyzer
from backend.core.cutter import VideoCutter

async def test_whisper():
    """Prueba el transcriptor Whisper"""
    print("🎤 Probando Whisper...")
    try:
        transcriber = WhisperTranscriber()
        if transcriber.validate_model():
            print("✅ Whisper: Modelo cargado correctamente")
            return True
        else:
            print("❌ Whisper: Error cargando modelo")
            return False
    except Exception as e:
        print(f"❌ Whisper: Error - {e}")
        return False

async def test_llm():
    """Prueba la conexión con el LLM"""
    print("🤖 Probando conexión LLM...")
    try:
        analyzer = LLMAnalyzer()
        if await analyzer.test_connection():
            print("✅ LLM: Conexión exitosa")
            return True
        else:
            print("❌ LLM: No se pudo conectar al servidor")
            print("   Asegúrate de que Ollama esté ejecutándose en puerto 11434")
            return False
    except Exception as e:
        print(f"❌ LLM: Error - {e}")
        return False

async def test_ffmpeg():
    """Prueba FFmpeg"""
    print("🎬 Probando FFmpeg...")
    try:
        cutter = VideoCutter()
        # FFmpeg se valida automáticamente al importar
        print("✅ FFmpeg: Disponible")
        return True
    except Exception as e:
        print(f"❌ FFmpeg: Error - {e}")
        return False

async def test_server():
    """Prueba el servidor web"""
    print("🌐 Probando servidor web...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:8000/health", timeout=5) as response:
                if response.status == 200:
                    print("✅ Servidor: Funcionando correctamente")
                    return True
                else:
                    print(f"❌ Servidor: Error {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Servidor: No disponible - {e}")
        print("   Asegúrate de que el servidor esté ejecutándose")
        return False

async def main():
    """Ejecuta todas las pruebas"""
    print("🔍 VERIFICACIÓN DEL SISTEMA SCCA")
    print("=" * 40)
    
    tests = [
        ("Whisper", test_whisper()),
        ("LLM", test_llm()),
        ("FFmpeg", test_ffmpeg()),
        ("Servidor", test_server())
    ]
    
    results = []
    for name, test in tests:
        result = await test
        results.append((name, result))
        print()
    
    print("=" * 40)
    print("📊 RESUMEN DE RESULTADOS:")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 40)
    if all_passed:
        print("🎉 ¡TODOS LOS COMPONENTES FUNCIONAN CORRECTAMENTE!")
        print("   El sistema SCCA está listo para usar.")
    else:
        print("⚠️  ALGUNOS COMPONENTES NECESITAN ATENCIÓN")
        print("   Revisa los errores arriba y sigue las instrucciones.")
    
    print("\n📖 Para más ayuda, consulta el README.md")

if __name__ == "__main__":
    asyncio.run(main())