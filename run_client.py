"""
Script para ejecutar la interfaz cliente de manera independiente.
Configura el entorno y ejecuta Streamlit con la configuración correcta.
"""

import os
import sys
import subprocess
from pathlib import Path

# Agregar el directorio raíz al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Configura variables de entorno necesarias"""
    
    # Configurar paths
    os.environ["PYTHONPATH"] = str(project_root)
    
    # Verificar AzureOpenAI API Key
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("⚠️  ADVERTENCIA: AZURE_OPENAI_API_KEY no está configurada")
        print("   Configura tu API key con: export AZURE_OPENAI_API_KEY=tu-api-key")
        print("   O crea un archivo .env con: AZURE_OPENAI_API_KEY=tu-api-key")
    
    # Configurar logging
    os.environ.setdefault("LOG_LEVEL", "INFO")
    
    # Configurar puertos
    os.environ.setdefault("CLIENT_PORT", "8501")
    os.environ.setdefault("EXPEDITION_API_URL", "http://localhost:8000")

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    required_packages = {
        'streamlit': 'streamlit>=1.29.0',
        'langchain': 'langchain>=0.1.0',
        'chromadb': 'chromadb>=0.4.0',
        'openai': 'openai (para Azure OpenAI)',
        'PIL': 'pillow (para procesamiento de imágenes)',
        'requests': 'requests (para APIs)'
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            if package == 'PIL':
                from PIL import Image
            else:
                __import__(package)
            print(f"✅ {description}")
        except ImportError:
            missing_packages.append(description)
            print(f"❌ {description}")
    
    if missing_packages:
        print(f"\n🔧 Para instalar dependencias faltantes:")
        print(f"   pip install -r requirements/local.txt")
        print(f"\n📖 Guía de instalación completa en README.md")
        return False
    
    print("✅ Todas las dependencias están instaladas")
    return True

def start_expedition_api():
    """Inicia la API de expedición si no está corriendo"""
    try:
        import requests
        response = requests.get("http://localhost:8000/", timeout=5)
        print("✅ API de expedición ya está ejecutándose")
        return True
    except:
        print("🚀 Iniciando API de expedición...")
        
        api_script = project_root / "services" / "expedition_api" / "app.py"
        if api_script.exists():
            # Ejecutar en background
            subprocess.Popen([
                sys.executable, str(api_script)
            ], cwd=str(api_script.parent))
            print("✅ API de expedición iniciada en puerto 8000")
            return True
        else:
            print("❌ No se encontró script de API de expedición")
            return False

def initialize_system():
    """Inicializa sistemas necesarios"""
    try:
        print("📚 Inicializando sistema RAG...")
        from services.rag_service import rag_service
        rag_service.initialize_documents()
        print("✅ Sistema RAG inicializado")
        
        print("🗄️ Verificando base de datos...")
        from utils.database import db_manager
        # Verificar que la BD funciona
        test_sessions = db_manager.get_active_sessions()
        print(f"✅ Base de datos funcional ({len(test_sessions)} sesiones activas)")
        
        print("🤖 Verificando orquestador...")
        from agents.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()
        health = orchestrator.get_system_health()
        if health.get("orchestrator") == "healthy":
            print("✅ Orquestador funcional")
        else:
            print("⚠️ Orquestador con problemas, pero continuando")
        
        return True
    except Exception as e:
        print(f"⚠️ Error inicializando sistema: {e}")
        print(f"   El sistema puede funcionar con limitaciones")
        return False

def main():
    """Función principal"""
    print("🏢 Iniciando Interfaz Cliente - Seguros Sura")
    print("=" * 50)
    
    # Setup
    setup_environment()
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Iniciar API de expedición
    start_expedition_api()
    
    # Inicializar sistema
    initialize_system()
    
    # Configurar comando Streamlit
    client_port = os.getenv("CLIENT_PORT", "8501")
    interface_script = project_root / "interfaces" / "client_interface.py"
    
    streamlit_cmd = [
        "streamlit", "run", str(interface_script),
        "--server.port", client_port,
        "--server.address", "localhost",
        "--browser.gatherUsageStats", "false"
    ]
    
    print(f"🚀 Iniciando interfaz cliente en puerto {client_port}")
    print(f"🌐 Accede en: http://localhost:{client_port}")
    print("=" * 50)
    
    try:
        subprocess.run(streamlit_cmd, cwd=str(project_root))
    except KeyboardInterrupt:
        print("\n👋 Cerrando aplicación...")
    except Exception as e:
        print(f"❌ Error ejecutando aplicación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
