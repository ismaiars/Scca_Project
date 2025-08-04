#!/usr/bin/env python3
"""
Script de configuración automática para Ollama con SCCA
"""

import subprocess
import time
import sys
import asyncio
import aiohttp

def run_command(command, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Exitoso")
            return True
        else:
            print(f"❌ {description} - Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Excepción: {e}")
        return False

async def test_ollama_connection():
    """Prueba la conexión con Ollama"""
    print("🔄 Probando conexión con Ollama...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=5) as response:
                if response.status == 200:
                    print("✅ Ollama está funcionando correctamente")
                    return True
                else:
                    print(f"❌ Ollama responde con error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ No se pudo conectar a Ollama: {e}")
        return False

def main():
    """Configuración automática de Ollama"""
    print("🐋 CONFIGURACIÓN AUTOMÁTICA DE OLLAMA PARA SCCA")
    print("=" * 50)
    
    # Verificar si Ollama está instalado
    if not run_command("ollama --version", "Verificando instalación de Ollama"):
        print("\n❌ Ollama no está instalado.")
        print("📥 Por favor:")
        print("   1. Descarga Ollama desde: https://ollama.com/download/windows")
        print("   2. Instala el archivo OllamaSetup.exe")
        print("   3. Reinicia la terminal")
        print("   4. Ejecuta este script nuevamente")
        return False
    
    print("\n🎯 Ollama detectado. Continuando con la configuración...")
    
    # Verificar si el servidor está ejecutándose
    print("\n🔄 Verificando servidor Ollama...")
    server_running = subprocess.run("tasklist | findstr ollama", shell=True, capture_output=True)
    
    if server_running.returncode != 0:
        print("🚀 Iniciando servidor Ollama...")
        # Iniciar servidor en segundo plano
        subprocess.Popen("ollama serve", shell=True)
        print("⏳ Esperando 5 segundos para que el servidor inicie...")
        time.sleep(5)
    else:
        print("✅ Servidor Ollama ya está ejecutándose")
    
    # Descargar modelo Mistral
    print("\n📦 Descargando modelo Mistral (esto puede tomar varios minutos)...")
    if run_command("ollama pull mistral:7b-instruct", "Descargando Mistral 7B Instruct"):
        print("✅ Modelo Mistral descargado exitosamente")
    else:
        print("❌ Error descargando modelo. Verifica tu conexión a internet.")
        return False
    
    # Probar conexión
    print("\n🧪 Probando conexión con el modelo...")
    if asyncio.run(test_ollama_connection()):
        print("✅ Configuración completada exitosamente")
        
        print("\n🎉 ¡OLLAMA CONFIGURADO CORRECTAMENTE!")
        print("=" * 50)
        print("📋 Próximos pasos:")
        print("   1. El servidor Ollama está ejecutándose")
        print("   2. El modelo Mistral está descargado")
        print("   3. Ejecuta: python test_system.py")
        print("   4. ¡Disfruta creando clips automáticamente!")
        
        return True
    else:
        print("❌ Error en la configuración. Revisa los logs arriba.")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🚀 Ejecuta 'python test_system.py' para verificar todo el sistema")
    else:
        print("\n📖 Consulta el README.md para solución de problemas")