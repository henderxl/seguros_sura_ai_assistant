"""
Script de setup automático para el Sistema de Agentes Seguros Sura.
Configura el entorno, instala dependencias y prepara datos iniciales.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_banner():
    """Imprime banner del sistema"""
    print("=" * 60)
    print("🏢 SISTEMA DE AGENTES SEGUROS SURA - SETUP")
    print("Sistema Multiagéntico para Asesoría y Venta de Pólizas")
    print("=" * 60)

def check_python_version():
    """Verifica versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def setup_virtual_environment():
    """Configura entorno virtual si no existe"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Entorno virtual ya existe")
        return True
    
    print("🔧 Creando entorno virtual...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Entorno virtual creado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creando entorno virtual: {e}")
        return False

def install_dependencies():
    """Instala dependencias del requirements"""
    requirements_file = Path("requirements/local.txt")
    
    if not requirements_file.exists():
        print("❌ Error: archivo requirements/local.txt no encontrado")
        return False
    
    print("📦 Instalando dependencias...")
    
    # Determinar comando pip
    if os.name == 'nt':  # Windows
        pip_cmd = ["venv\\Scripts\\pip"]
    else:  # Unix/Linux/Mac
        pip_cmd = ["venv/bin/pip"]
    
    try:
        # Actualizar pip
        subprocess.run(pip_cmd + ["install", "--upgrade", "pip"], check=True)
        
        # Instalar dependencias
        subprocess.run(pip_cmd + ["install", "-r", str(requirements_file)], check=True)
        
        print("✅ Dependencias instaladas")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        print("💡 Intenta manualmente: pip install -r requirements/local.txt")
        return False

def setup_directories():
    """Crea directorios necesarios"""
    print("📁 Configurando directorios...")
    
    directories = [
        "data/sessions",
        "data/vectors", 
        "data/vehicles",
        "data/documents",
        "data/images",
        "logs",
        "services/expedition_api/polizas"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directorios configurados")

def setup_environment_file():
    """Configura archivo de entorno"""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("✅ Archivo .env ya existe")
        return True
    
    if env_example.exists():
        print("📝 Creando archivo .env desde ejemplo...")
        shutil.copy(env_example, env_file)
        print("✅ Archivo .env creado")
        print("⚠️  IMPORTANTE: Edita .env y agrega tu OPENAI_API_KEY")
        return True
    else:
        print("📝 Creando archivo .env básico...")
        with open(env_file, 'w') as f:
            f.write("""# Configuración Sistema Agentes Seguros Sura
AZURE_OPENAI_API_KEY=tu-api-key-aqui
ENVIRONMENT=local
DEBUG=True
CLIENT_PORT=8501
ADVISOR_PORT=8502
EXPEDITION_API_URL=http://localhost:8000
""")
        print("✅ Archivo .env creado")
        print("⚠️  IMPORTANTE: Edita .env y agrega tu OPENAI_API_KEY")
        return True

def copy_original_data():
    """Copia datos originales si están disponibles"""
    print("📊 Verificando datos originales...")
    
    # Verificar si existen datos originales
    original_base = Path("../prueba_tecnica")
    
    if not original_base.exists():
        print("⚠️  Datos originales no encontrados en ../prueba_tecnica")
        print("   Asegúrate de que los insumos estén disponibles")
        return False
    
    # Copiar archivos si no existen
    copies_needed = []
    
    # Verificar Excel de vehículos
    vehicles_excel = Path("data/vehicles/carros.xlsx")
    if not vehicles_excel.exists():
        original_excel = original_base / "3. Cotizacion" / "funcion_cotizacion" / "data" / "carros.xlsx"
        if original_excel.exists():
            copies_needed.append((original_excel, vehicles_excel))
    
    # Verificar documentos PDF
    docs_dir = Path("data/documents")
    if not any(docs_dir.glob("*.pdf")):
        original_docs = original_base / "1. Documentos planes autos"
        if original_docs.exists():
            for pdf_file in original_docs.glob("*.pdf"):
                copies_needed.append((pdf_file, docs_dir / pdf_file.name))
    
    # Realizar copias
    if copies_needed:
        print(f"📋 Copiando {len(copies_needed)} archivos de datos...")
        for src, dst in copies_needed:
            try:
                shutil.copy2(src, dst)
                print(f"   ✅ {dst.name}")
            except Exception as e:
                print(f"   ❌ Error copiando {dst.name}: {e}")
    else:
        print("✅ Datos ya están disponibles")
    
    return True

def verify_installation():
    """Verifica que la instalación sea correcta"""
    print("🔍 Verificando instalación...")
    
    # Verificar imports principales
    try:
        sys.path.insert(0, str(Path.cwd()))
        
        from utils.config import config
        from utils.database import db_manager
        from agents.orchestrator import orchestrator
        
        print("✅ Imports principales - OK")
        
        # Verificar configuración
        if not config.azure_openai.api_key or config.azure_openai.api_key.startswith("tu-api-key"):
            print("⚠️  Advertencia: AZURE_OPENAI_API_KEY no configurada correctamente")
        else:
            print("✅ Configuración API - OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def print_next_steps():
    """Imprime próximos pasos"""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETADO")
    print("=" * 60)
    
    print("\n📋 PRÓXIMOS PASOS:")
    print("\n1. Configurar API Key:")
    print("   - Edita el archivo .env")
    print("   - Agrega tu OPENAI_API_KEY válida")
    
    print("\n2. Iniciar el sistema:")
    print("   - Cliente: python run_client.py")
    print("   - Asesor:  python run_advisor.py")
    print("   - Ambos:   docker-compose up")
    
    print("\n3. Acceder a las interfaces:")
    print("   - Cliente: http://localhost:8501")
    print("   - Asesor:  http://localhost:8502")
    
    print("\n4. Documentación:")
    print("   - Revisa docs/DEPLOYMENT.md para detalles")
    print("   - Revisa docs/USE_CASES.md para ejemplos")
    
    print("\n💡 CONSEJOS:")
    print("   - Usa 'admin123' como contraseña en interfaz asesor")
    print("   - Prueba subiendo imágenes de vehículos en interfaz cliente")
    print("   - Revisa logs/ para debugging si hay problemas")
    
    print("\n" + "=" * 60)

def main():
    """Función principal de setup"""
    print_banner()
    
    # Verificaciones previas
    if not check_python_version():
        sys.exit(1)
    
    # Setup paso a paso
    steps = [
        ("Entorno virtual", setup_virtual_environment),
        ("Dependencias", install_dependencies),
        ("Directorios", setup_directories),
        ("Archivo entorno", setup_environment_file),
        ("Datos originales", copy_original_data),
        ("Verificación", verify_installation)
    ]
    
    print(f"\n🚀 Ejecutando {len(steps)} pasos de configuración...\n")
    
    for step_name, step_func in steps:
        print(f"📍 {step_name}...")
        if not step_func():
            print(f"❌ Error en paso: {step_name}")
            print("🛑 Setup interrumpido")
            sys.exit(1)
        print()
    
    print_next_steps()

if __name__ == "__main__":
    main()
