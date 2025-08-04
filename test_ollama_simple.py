#!/usr/bin/env python3
"""
Test simple para verificar la conexión con Ollama
"""

import asyncio
import aiohttp
import sys
import os
from pathlib import Path

# Agregar el directorio backend al path
sys.path.append(str(Path(__file__).parent / "backend"))

async def test_ollama_direct():
    """Prueba directa de la API de Ollama"""
    print("🤖 Probando conexión directa con Ollama...")
    
    url = "http://localhost:11434/v1/chat/completions"
    payload = {
        "model": "mistral:7b-instruct",
        "messages": [{"role": "user", "content": "Hola, responde solo 'OK'"}],
        "max_tokens": 10
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    print(f"✅ Ollama responde: {content}")
                    return True
                else:
                    print(f"❌ Error HTTP: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_analyzer_class():
    """Prueba la clase LLMAnalyzer"""
    print("🔍 Probando clase LLMAnalyzer...")
    
    try:
        from backend.core.analyzer import LLMAnalyzer
        analyzer = LLMAnalyzer()
        
        result = await analyzer.test_connection()
        if result:
            print("✅ LLMAnalyzer: Conexión exitosa")
            return True
        else:
            print("❌ LLMAnalyzer: Falló la conexión")
            return False
    except Exception as e:
        print(f"❌ Error en LLMAnalyzer: {e}")
        return False

async def main():
    print("🧪 TEST SIMPLE DE OLLAMA")
    print("=" * 40)
    
    # Test 1: Conexión directa
    direct_ok = await test_ollama_direct()
    print()
    
    # Test 2: Clase analyzer
    analyzer_ok = await test_analyzer_class()
    print()
    
    print("=" * 40)
    if direct_ok and analyzer_ok:
        print("🎉 ¡TODO FUNCIONA CORRECTAMENTE!")
    else:
        print("⚠️  HAY PROBLEMAS:")
        if not direct_ok:
            print("   - Conexión directa falló")
        if not analyzer_ok:
            print("   - Clase LLMAnalyzer falló")

if __name__ == "__main__":
    asyncio.run(main())