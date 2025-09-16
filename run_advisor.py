"""
Script para ejecutar la interfaz asesor de manera independiente.
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
    
    # Verificar OpenAI API Key (opcional para asesor)
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("⚠️  ADVERTENCIA: AZURE_OPENAI_API_KEY no está configurada")
        print("   La interfaz funcionará con funcionalidad limitada")
    
    # Configurar logging
    os.environ.setdefault("LOG_LEVEL", "INFO")
    
    # Configurar puertos
    os.environ.setdefault("ADVISOR_PORT", "8502")
    os.environ.setdefault("EXPEDITION_API_URL", "http://localhost:8000")

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    required_packages = {
        'streamlit': 'streamlit>=1.29.0',
        'pandas': 'pandas (para tablas)',
        'langchain': 'langchain (para agentes)',
        'sqlite3': 'sqlite3 (built-in)'
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            if package == 'sqlite3':
                import sqlite3
            else:
                __import__(package)
            print(f"✅ {description}")
        except ImportError:
            missing_packages.append(description)
            print(f"❌ {description}")
    
    if missing_packages:
        print(f"\n🔧 Para instalar dependencias faltantes:")
        print(f"   pip install -r requirements/local.txt")
        return False
    
    return True

def check_database():
    """Verifica que la base de datos esté accesible"""
    try:
        from utils.database import db_manager
        
        # Test básico de conexión
        test_sessions = db_manager.get_active_sessions()
        print("✅ Base de datos accesible")
        return True
    except Exception as e:
        print(f"⚠️  Advertencia con base de datos: {e}")
        print("   La interfaz funcionará con funcionalidad limitada")
        return False

def main():
    """Función principal"""
    print("👨‍💼 Iniciando Interfaz Asesor - Seguros Sura")
    print("=" * 50)
    
    # Setup
    setup_environment()
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Verificar base de datos
    check_database()
    
    # Configurar comando Streamlit
    advisor_port = os.getenv("ADVISOR_PORT", "8502")
    interface_script = project_root / "interfaces" / "advisor_interface.py"
    
    streamlit_cmd = [
        "streamlit", "run", str(interface_script),
        "--server.port", advisor_port,
        "--server.address", "localhost",
        "--browser.gatherUsageStats", "false"
    ]
    
    print(f"🚀 Iniciando interfaz asesor en puerto {advisor_port}")
    print(f"🌐 Accede en: http://localhost:{advisor_port}")
    print("📋 Credenciales demo: cualquier ID con contraseña 'admin123'")
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
