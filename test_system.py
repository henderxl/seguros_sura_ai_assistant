"""
Test del sistema completo - Verificación de funcionalidad
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Prueba todas las importaciones críticas"""
    results = {}
    
    try:
        import streamlit
        results["streamlit"] = "✅ OK"
    except ImportError as e:
        results["streamlit"] = f"❌ Error: {e}"
    
    try:
        import openai
        results["openai"] = "✅ OK"
    except ImportError as e:
        results["openai"] = f"❌ Error: {e}"
    
    try:
        import pandas
        results["pandas"] = "✅ OK"
    except ImportError as e:
        results["pandas"] = f"❌ Error: {e}"
    
    try:
        import requests
        results["requests"] = "✅ OK"
    except ImportError as e:
        results["requests"] = f"❌ Error: {e}"
    
    try:
        from PIL import Image
        results["pillow"] = "✅ OK"
    except ImportError as e:
        results["pillow"] = f"❌ Error: {e}"
    
    try:
        import structlog
        results["structlog"] = "✅ OK"
    except ImportError as e:
        results["structlog"] = f"❌ Error: {e}"
    
    try:
        import langchain
        results["langchain"] = "✅ OK"
    except ImportError as e:
        results["langchain"] = f"❌ Error: {e}"
    
    try:
        from langgraph.graph import StateGraph
        results["langgraph"] = "✅ OK"
    except ImportError as e:
        results["langgraph"] = f"❌ Error: {e}"
    
    try:
        import chromadb
        results["chromadb"] = "✅ OK"
    except ImportError as e:
        results["chromadb"] = f"❌ Error: {e}"
    
    return results

def test_file_structure():
    """Verifica estructura de archivos"""
    files_to_check = [
        "agents/base_agent.py",
        "agents/consultant_agent.py", 
        "agents/quotation_agent.py",
        "agents/expedition_agent.py",
        "agents/human_loop_agent.py",
        "agents/orchestrator.py",
        "services/rag_service.py",
        "services/quotation_service.py",
        "services/expedition_service.py",
        "utils/config.py",
        "utils/database.py",
        "utils/logging_config.py",
        "interfaces/client_interface.py",
        "interfaces/advisor_interface.py",
        "data/documents",
        "data/images",
        "data/vehicles",
        "services/expedition_api/app.py"
    ]
    
    results = {}
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            results[file_path] = "✅ Existe"
        else:
            results[file_path] = "❌ Falta"
    
    return results

def test_data_files():
    """Verifica archivos de datos copiados"""
    data_files = [
        "data/documents/Ejemplos preguntas respuestas.txt",
        "data/images/vehiculos_combinado_v2.csv",
        "data/vehicles/Listado de carros asegurables.xlsx",
        "services/cotizacion_original/cotizacion.py",
        "services/expedition_api/app.py"
    ]
    
    results = {}
    for file_path in data_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size if path.is_file() else len(list(path.iterdir()))
            results[file_path] = f"✅ Existe ({size} bytes)"
        else:
            results[file_path] = "❌ Falta"
    
    return results

def main():
    """Ejecuta todas las pruebas"""
    print("="*60)
    print("🔍 DIAGNÓSTICO COMPLETO DEL SISTEMA")
    print("="*60)
    
    print("\n📦 ESTADO DE DEPENDENCIAS:")
    import_results = test_imports()
    for lib, status in import_results.items():
        print(f"  {lib}: {status}")
    
    print("\n📁 ESTRUCTURA DE ARCHIVOS:")
    file_results = test_file_structure()
    for file_path, status in file_results.items():
        print(f"  {file_path}: {status}")
    
    print("\n📋 ARCHIVOS DE DATOS:")
    data_results = test_data_files()
    for file_path, status in data_results.items():
        print(f"  {file_path}: {status}")
    
    print("\n🏥 RESUMEN:")
    
    # Contar estados
    imports_ok = sum(1 for status in import_results.values() if "✅" in status)
    imports_total = len(import_results)
    
    files_ok = sum(1 for status in file_results.values() if "✅" in status)
    files_total = len(file_results)
    
    data_ok = sum(1 for status in data_results.values() if "✅" in status)
    data_total = len(data_results)
    
    print(f"  Dependencias: {imports_ok}/{imports_total}")
    print(f"  Archivos: {files_ok}/{files_total}")
    print(f"  Datos: {data_ok}/{data_total}")
    
    if imports_ok == imports_total and files_ok == files_total and data_ok == data_total:
        print("\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
        print("   Puedes ejecutar las interfaces:")
        print("   - Cliente: python -m streamlit run interfaces/client_interface.py --server.port 8501")
        print("   - Asesor: python -m streamlit run interfaces/advisor_interface.py --server.port 8502")
        print("   - API Expedición: cd services/expedition_api && python app.py")
    else:
        print("\n⚠️  SISTEMA REQUIERE REPARACIONES")
        print("   Revisa los errores listados arriba")
    
    print("="*60)

if __name__ == "__main__":
    main()
