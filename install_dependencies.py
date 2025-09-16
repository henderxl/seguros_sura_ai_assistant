#!/usr/bin/env python3
"""
Script de instalación inteligente para resolver problemas de dependencias.
Maneja incompatibilidades comunes y ofrece alternativas.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Verifica versión de Python"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version >= (3, 13):
        print("⚠️  Python 3.13 detectado - usando versiones compatibles")
        return "3.13+"
    elif version >= (3, 9):
        print("✅ Versión de Python compatible")
        return "3.9+"
    else:
        print("❌ Python 3.9+ requerido")
        sys.exit(1)

def install_package_safely(package_spec, fallback_spec=None, description=""):
    """Instala un paquete con fallback en caso de error"""
    print(f"\n📦 Instalando {description or package_spec}...")
    
    try:
        # Intentar instalación principal
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package_spec
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {package_spec} instalado exitosamente")
            return True
        else:
            print(f"⚠️  Error instalando {package_spec}: {result.stderr[:200]}")
            
            # Intentar fallback si existe
            if fallback_spec:
                print(f"🔄 Intentando versión alternativa: {fallback_spec}")
                
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", fallback_spec
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print(f"✅ {fallback_spec} instalado exitosamente")
                    return True
                else:
                    print(f"❌ También falló {fallback_spec}")
            
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout instalando {package_spec}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def main():
    """Función principal de instalación"""
    print("🔧 Script de Instalación Inteligente - Seguros Sura AI")
    print("=" * 60)
    
    # Verificar Python
    python_version = check_python_version()
    
    # Actualizar pip primero
    print("\n🔄 Actualizando pip...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                  capture_output=True)
    
    # Lista de paquetes críticos con alternativas
    critical_packages = [
        # Core Streamlit (más importante)
        ("streamlit>=1.29.0,<2.0.0", "streamlit==1.29.0", "Streamlit (interfaz principal)"),
        
        # Procesamiento de datos (versión validada)
        ("pandas>=2.2.0,<2.3.0", "pandas==2.2.3", "Pandas (manejo de datos)"),
        
        # Imágenes y vision
        ("pillow>=10.0.0", "pillow==10.2.0", "Pillow (procesamiento imágenes)"),
        ("requests>=2.31.0", "requests==2.31.0", "Requests (APIs)"),
        
        # APIs web
        ("flask>=3.1.0,<4.0.0", "flask==3.1.2", "Flask (API expedición)"),
        
        # Base de datos
        ("sqlalchemy>=2.0.0,<3.0.0", "sqlalchemy==2.0.23", "SQLAlchemy (base de datos)"),
        ("openpyxl>=3.1.0", "openpyxl==3.1.2", "OpenPyXL (archivos Excel)"),
    ]
    
    # Paquetes opcionales (para funcionalidad completa)
    optional_packages = [
        ("langchain>=0.3.0,<0.4.0", "langchain==0.3.27", "LangChain (agentes IA)"),
        ("langchain-openai>=0.3.0,<0.4.0", "langchain-openai==0.3.32", "LangChain OpenAI"),
        ("openai>=1.100.0,<2.0.0", "openai==1.107.0", "OpenAI Python client"),
        ("chromadb>=1.0.0,<2.0.0", "chromadb==1.0.20", "ChromaDB (vector store)"),
        ("sentence-transformers>=2.2.0", None, "Sentence Transformers (embeddings)"),
    ]
    
    successful_installs = 0
    total_critical = len(critical_packages)
    
    print(f"\n🔥 Instalando {total_critical} paquetes críticos...")
    
    # Instalar paquetes críticos
    for package_spec, fallback, description in critical_packages:
        if install_package_safely(package_spec, fallback, description):
            successful_installs += 1
    
    print(f"\n📊 Paquetes críticos: {successful_installs}/{total_critical} instalados")
    
    if successful_installs < total_critical:
        print("⚠️  Algunos paquetes críticos fallaron. El sistema funcionará con limitaciones.")
    
    # Instalar paquetes opcionales (para funcionalidad IA completa)
    print(f"\n🤖 Instalando paquetes de IA (opcional)...")
    ai_installs = 0
    
    for package_spec, fallback, description in optional_packages:
        if install_package_safely(package_spec, fallback, description):
            ai_installs += 1
    
    print(f"\n📊 Paquetes de IA: {ai_installs}/{len(optional_packages)} instalados")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE INSTALACIÓN:")
    print(f"✅ Paquetes críticos: {successful_installs}/{total_critical}")
    print(f"🤖 Paquetes de IA: {ai_installs}/{len(optional_packages)}")
    
    if successful_installs >= total_critical - 1:  # Permitir 1 fallo
        print("\n🎉 INSTALACIÓN EXITOSA!")
        print("   El sistema debería funcionar correctamente.")
        print("\n📚 Próximos pasos:")
        print("   1. Configurar archivo .env con tus API keys")
        print("   2. Ejecutar: python run_client.py")
        print("   3. Ejecutar: python run_advisor.py")
    else:
        print("\n⚠️  INSTALACIÓN PARCIAL")
        print("   Algunas funcionalidades pueden no estar disponibles.")
        print("   Revisa los errores arriba e intenta instalar manualmente.")
    
    # Verificar instalación
    print("\n🔍 Verificando instalación...")
    try:
        import streamlit
        print("✅ Streamlit disponible")
        
        try:
            import pandas
            print("✅ Pandas disponible")
        except:
            print("❌ Pandas no disponible - funcionalidad limitada")
        
        try:
            import langchain
            print("✅ LangChain disponible - funcionalidad completa de IA")
        except:
            print("⚠️  LangChain no disponible - funcionalidad básica únicamente")
            
    except ImportError:
        print("❌ Error crítico: Streamlit no disponible")
        return False
    
    return True

if __name__ == "__main__":
    main()
