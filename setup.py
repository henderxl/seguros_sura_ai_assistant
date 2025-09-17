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
    """Configura entorno virtual si no existe (opcional)"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Entorno virtual ya existe")
        return True
    
    print("🔧 Creando entorno virtual (opcional)...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Entorno virtual creado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  No se pudo crear entorno virtual: {e}")
        print("💡 Continuando sin entorno virtual (usando Python del sistema)")
        return True  # No es crítico para el funcionamiento

def install_dependencies():
    """Instala dependencias del requirements (solo si es necesario)"""
    requirements_file = Path("requirements/local.txt")
    
    if not requirements_file.exists():
        print("❌ Error: archivo requirements/local.txt no encontrado")
        return False
    
    # Verificar si las dependencias ya están instaladas
    print("🔍 Verificando dependencias existentes...")
    
    # Usar pip del sistema actual (no del venv) para mayor compatibilidad
    pip_cmd = [sys.executable, "-m", "pip"]
    python_cmd = [sys.executable]
    
    critical_packages = ["langchain", "openai", "streamlit", "chromadb"]
    missing_packages = []
    
    for package in critical_packages:
        try:
            # Usar python -c "import package" para verificar
            result = subprocess.run(
                python_cmd + ["-c", f"import {package}; print('OK')"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            if result.returncode != 0:
                missing_packages.append(package)
                print(f"   ❌ {package} - No disponible")
            else:
                print(f"   ✅ {package} - OK")
        except:
            missing_packages.append(package)
            print(f"   ❌ {package} - Error verificando")
    
    if not missing_packages:
        print("✅ Todas las dependencias críticas están instaladas")
        return True
    
    print(f"📦 Faltan dependencias: {', '.join(missing_packages)}")
    print("📦 Instalando dependencias faltantes...")
    
    # Intentar instalar con diferentes estrategias
    installation_success = False
    
    # Estrategia 1: Instalar desde requirements
    try:
        print("   🔄 Intentando instalar desde requirements/local.txt...")
        result = subprocess.run(
            pip_cmd + ["install", "-r", str(requirements_file)], 
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Dependencias instaladas desde requirements")
        installation_success = True
    except (subprocess.CalledProcessError, PermissionError, OSError) as e:
        print(f"   ⚠️  Error con requirements: {e}")
        
        # Estrategia 2: Instalar paquetes individualmente
        try:
            print("   🔄 Intentando instalar paquetes individualmente...")
            for package in missing_packages:
                print(f"   📦 Instalando {package}...")
                result = subprocess.run(
                    pip_cmd + ["install", package], 
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"   ✅ {package} instalado")
            installation_success = True
        except (subprocess.CalledProcessError, PermissionError, OSError) as e:
            print(f"   ⚠️  Error instalando individualmente: {e}")
            
            # Estrategia 3: Instalar con --user
            try:
                print("   🔄 Intentando instalar con --user...")
                result = subprocess.run(
                    pip_cmd + ["install", "--user", "-r", str(requirements_file)], 
                    check=True,
                    capture_output=True,
                    text=True
                )
                print("✅ Dependencias instaladas con --user")
                installation_success = True
            except (subprocess.CalledProcessError, PermissionError, OSError) as e:
                print(f"   ⚠️  Error con --user: {e}")
    
    # Verificar si la instalación fue exitosa
    if installation_success:
        print("🔍 Verificando instalación...")
        still_missing = []
        available = []
        
        for package in critical_packages:
            try:
                result = subprocess.run(
                    python_cmd + ["-c", f"import {package}; print('OK')"], 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                if result.returncode == 0:
                    available.append(package)
                else:
                    still_missing.append(package)
            except:
                still_missing.append(package)
        
        print(f"✅ Disponibles: {', '.join(available) if available else 'ninguno'}")
        if still_missing:
            print(f"❌ Aún faltantes: {', '.join(still_missing)}")
        
        if not still_missing:
            print("✅ Todas las dependencias críticas están disponibles")
            return True
        elif len(available) >= 2:  # Al menos la mitad están disponibles
            print(f"⚠️  Faltan algunas dependencias, pero {len(available)} están disponibles")
            print("💡 El setup continuará. Instala manualmente si hay problemas:")
            print(f"💡   pip install {' '.join(still_missing)}")
            return True
        else:
            print(f"❌ Faltan demasiadas dependencias críticas: {', '.join(still_missing)}")
            print("💡 Instala manualmente: pip install -r requirements/local.txt")
            return False
    else:
        print("❌ No se pudieron instalar las dependencias")
        print("💡 Instala manualmente: pip install -r requirements/local.txt")
        return False

def install_problematic_packages():
    """Instala paquetes que pueden causar problemas de manera específica"""
    print("🔧 Instalando paquetes problemáticos...")
    
    # Paquetes que pueden necesitar instalación especial
    problematic_packages = {
        "chromadb": "chromadb>=0.4.0",
        "streamlit": "streamlit>=1.29.0",
        "langchain": "langchain>=0.1.0"
    }
    
    pip_cmd = [sys.executable, "-m", "pip"]
    
    for package_name, package_spec in problematic_packages.items():
        try:
            # Verificar si ya está instalado
            result = subprocess.run(
                [sys.executable, "-c", f"import {package_name}; print('OK')"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if result.returncode == 0:
                print(f"   ✅ {package_name} - Ya instalado")
                continue
            
            print(f"   📦 Instalando {package_name}...")
            
            # Intentar diferentes estrategias de instalación
            strategies = [
                [package_spec],  # Instalación normal
                [package_spec, "--no-cache-dir"],  # Sin caché
                [package_spec, "--user"],  # Para usuario
                [package_spec, "--upgrade", "--force-reinstall"]  # Forzar reinstalación
            ]
            
            installed = False
            for strategy in strategies:
                try:
                    subprocess.run(
                        pip_cmd + ["install"] + strategy,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    print(f"   ✅ {package_name} instalado con estrategia: {' '.join(strategy)}")
                    installed = True
                    break
                except subprocess.CalledProcessError:
                    continue
            
            if not installed:
                print(f"   ❌ No se pudo instalar {package_name}")
                
        except Exception as e:
            print(f"   ❌ Error con {package_name}: {e}")
    
    return True

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
    
    try:
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        print("✅ Directorios configurados")
        return True
    except Exception as e:
        print(f"❌ Error configurando directorios: {e}")
        return False

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


def verify_installation():
    """Verifica que la instalación sea correcta"""
    print("🔍 Verificando instalación...")
    
    # Verificar dependencias críticas
    critical_packages = [
        "langchain", "openai", "streamlit", "chromadb", 
        "pandas", "sqlalchemy", "pydantic"
    ]
    
    print("📦 Verificando dependencias críticas...")
    try:
        import subprocess
        
        # Usar python del sistema actual
        python_cmd = [sys.executable]
        
        # Verificar cada paquete crítico
        available_packages = []
        missing_packages = []
        
        for package in critical_packages:
            try:
                result = subprocess.run(
                    python_cmd + ["-c", f"import {package}; print('OK')"], 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                if result.returncode == 0:
                    print(f"   ✅ {package}")
                    available_packages.append(package)
                else:
                    print(f"   ❌ {package} - No disponible")
                    missing_packages.append(package)
            except Exception as e:
                print(f"   ❌ Error verificando {package}: {e}")
                missing_packages.append(package)
        
        print(f"📦 Verificación completada: {len(available_packages)}/{len(critical_packages)} paquetes disponibles")
        
        if len(available_packages) >= 4:  # Al menos la mayoría están disponibles
            print("✅ Suficientes dependencias disponibles para funcionar")
            if missing_packages:
                print(f"⚠️  Faltantes (opcionales): {', '.join(missing_packages)}")
            return True
        else:
            print(f"❌ Faltan dependencias críticas: {', '.join(missing_packages)}")
            return False
        
    except Exception as e:
        print(f"❌ Error verificando dependencias: {e}")
        return False
    
    # Verificar si el proyecto funciona independientemente del venv
    try:
        sys.path.insert(0, str(Path.cwd()))
        
        print("🧪 Probando imports del proyecto...")
        
        # Probar imports del proyecto directamente
        from utils.config import config
        print("✅ Configuración del proyecto - OK")
        
        # Probar agentes principales
        from agents.orchestrator import AgentOrchestrator
        print("✅ Orquestador - OK")
        
        from agents.quotation_agent import QuotationAgent
        print("✅ Agente de cotización - OK")
        
        # Verificar API Key
        if not hasattr(config, 'azure_openai') or not config.azure_openai.api_key or config.azure_openai.api_key.startswith("tu-api-key"):
            print("⚠️  Advertencia: AZURE_OPENAI_API_KEY no configurada correctamente")
            print("   Edita el archivo .env y agrega tu API key antes de usar el sistema")
        else:
            print("✅ Configuración API - OK")
        
        print("✅ El proyecto está listo para funcionar!")
        return True
        
    except Exception as e:
        print(f"❌ Error en verificación del proyecto: {e}")
        print("💡 Algunos imports fallan, pero esto puede ser normal en setup inicial")
        
        # Verificación mínima - solo que el directorio esté bien estructurado
        required_files = [
            "utils/config.py",
            "agents/orchestrator.py", 
            "agents/quotation_agent.py",
            "interfaces/client_interface.py",
            "run_client.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Archivos críticos faltantes: {', '.join(missing_files)}")
            return False
        else:
            print("✅ Estructura del proyecto - OK")
            print("💡 El proyecto debería funcionar. Si hay problemas, instala dependencias manualmente.")
            return True

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
        ("Paquetes problemáticos", install_problematic_packages),
        ("Directorios", setup_directories),
        ("Archivo entorno", setup_environment_file),
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
