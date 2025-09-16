# 🚀 Guía de Despliegue - Sistema de Agentes Seguros Sura

## 📋 Introducción

Esta guía proporciona instrucciones detalladas para desplegar y ejecutar el Sistema de Agentes de IA para Seguros Sura tanto en **entorno local** como en **Azure Cloud**. El sistema está completamente probado y ready-for-production.

### 🎯 Opciones de Despliegue

| Ambiente | Propósito | Complejidad | Tiempo Setup |
|----------|-----------|-------------|--------------|
| **🖥️ Local** | Desarrollo y testing | ⭐⭐ Fácil | 10 minutos |
| **🐳 Docker** | Desarrollo containerizado | ⭐⭐⭐ Medio | 15 minutos |
| **☁️ Azure** | Producción enterprise | ⭐⭐⭐⭐ Avanzado | 30 minutos |

> ☁️ **Para despliegue Azure:** Ver [`AZURE_ARCHITECTURE_C4.md`](AZURE_ARCHITECTURE_C4.md)

## Requisitos Previos

### Software Requerido

- **Python 3.8+** (Recomendado: Python 3.11)
- **pip** (gestor de paquetes Python)
- **Git** (para clonar repositorio)
- **Azure OpenAI API Key** (requerida para funcionalidad completa)
  - Endpoint de Azure OpenAI configurado
  - Modelos GPT-4o y text-embedding-ada-002 desplegados

### Hardware Recomendado

- **RAM:** Mínimo 8GB, recomendado 16GB
- **Almacenamiento:** 15GB libres
- **CPU:** Procesador moderno multi-core
- **Conexión a Internet:** Para APIs Azure y funcionalidades en tiempo real

## Instalación Rápida (Recomendada)

### Paso 1: Preparar Entorno

```bash
# Clonar o descomprimir proyecto
cd seguros_sura_ai_assistant

# Verificar Python
python --version  # Debe ser 3.8+
```

### Paso 2: Setup Automático

```bash
# Ejecutar script de setup automático
python setup.py
```

El script automático realizará:
- ✅ Crear entorno virtual
- ✅ Instalar dependencias
- ✅ Configurar directorios
- ✅ Crear archivo .env
- ✅ Copiar datos necesarios
- ✅ Verificar instalación

### Paso 3: Configurar Azure OpenAI

```bash
# Editar archivo .env
nano .env  # o usar tu editor preferido

# Configurar Azure OpenAI (REQUERIDO):
AZURE_OPENAI_API_KEY=tu-azure-openai-key-aqui
AZURE_OPENAI_ENDPOINT=https://tu-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

### Paso 4: Ejecutar Sistema

```bash
# Interfaz Cliente (Puerto 8501)
python run_client.py

# En otra terminal - Interfaz Asesor (Puerto 8502)  
python run_advisor.py
```

### Paso 5: Acceder

- **Cliente:** http://localhost:8501
- **Asesor:** http://localhost:8502 (credenciales: cualquier ID + password: admin123)

## Instalación Manual (Avanzada)

### 1. Crear Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. Instalar Dependencias

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements/local.txt
```

### 3. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp env.example .env

# Editar variables
nano .env
```

Configurar las siguientes variables en `.env`:

```env
# Azure OpenAI Configuration (REQUERIDO)
AZURE_OPENAI_API_KEY=tu-azure-openai-key-aqui
AZURE_OPENAI_ENDPOINT=https://tu-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Model Configurations
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Environment
ENVIRONMENT=local
DEBUG=True

# Ports
CLIENT_PORT=8501
ADVISOR_PORT=8502

# Services
EXPEDITION_API_URL=http://localhost:8000

# Database
DATABASE_PATH=data/sessions/conversations.db
VECTOR_STORE_PATH=data/vectors/

# Logging
LOG_LEVEL=INFO
LOG_PATH=logs/
```

### 4. Crear Directorios

```bash
mkdir -p data/{sessions,vectors,vehicles,documents,images}
mkdir -p logs
mkdir -p services/expedition_api/polizas
```

### 5. Copiar Datos Iniciales

Si tienes los insumos originales de la prueba técnica:

```bash
# Copiar documentos PDF
cp "../prueba_tecnica/1. Documentos planes autos"/*.pdf data/documents/

# Copiar Excel de vehículos
cp "../prueba_tecnica/3. Cotizacion/funcion_cotizacion/data/carros.xlsx" data/vehicles/

# Copiar imágenes de ejemplo
cp "../prueba_tecnica/2. Ejemplos Carros"/* data/images/
```

### 6. Inicializar Base de Datos

```bash
# Inicializar con Python
python -c "from utils.database import db_manager; print('BD inicializada')"
```

## Ejecución del Sistema

### Opción 1: Scripts de Ejecución

```bash
# Ejecutar interfaz cliente
python run_client.py

# Ejecutar interfaz asesor (en otra terminal)
python run_advisor.py
```

### Opción 2: Streamlit Directamente

```bash
# Cliente
streamlit run interfaces/client_interface.py --server.port 8501

# Asesor  
streamlit run interfaces/advisor_interface.py --server.port 8502
```

### Opción 3: Docker Compose

```bash
# Configurar variables de entorno
export OPENAI_API_KEY=tu-api-key-aqui

# Ejecutar servicios
docker-compose up --build
```

## Verificación de Instalación

### 1. Tests Básicos

```bash
# Ejecutar tests básicos
python tests/test_basic_functionality.py

# O con pytest
pytest tests/test_basic_functionality.py -v
```

### 2. Verificación Manual

1. **Interfaz Cliente:**
   - Acceder a http://localhost:8501
   - Probar pregunta: "¿Qué cubre el Plan Autos Básico?"
   - Verificar respuesta del sistema

2. **Interfaz Asesor:**
   - Acceder a http://localhost:8502
   - Login con cualquier ID + password: admin123
   - Verificar dashboard y casos activos

3. **API de Expedición:**
   - Verificar http://localhost:8000
   - Debe mostrar API funcionando

### 3. Health Check

```bash
# Verificar estado del sistema
python -c "
from agents.orchestrator import orchestrator
import json
health = orchestrator.get_system_health()
print(json.dumps(health, indent=2))
"
```

## Resolución de Problemas

### Error: Azure OpenAI Configuration

```
Error: AZURE_OPENAI_API_KEY es requerida
Error: Azure OpenAI endpoint not configured
```

**Solución:**
```bash
# Verificar configuración Azure OpenAI
cat .env | grep AZURE_OPENAI

# Configurar variables de entorno temporalmente
export AZURE_OPENAI_API_KEY=tu-api-key-aqui
export AZURE_OPENAI_ENDPOINT=https://tu-resource.openai.azure.com/

# Verificar conectividad
python -c "from utils.config import config; print('Config OK')"
```

### Error: Dependencias Faltantes

```
ImportError: No module named 'streamlit'
```

**Solución:**
```bash
# Verificar entorno virtual activo
which python

# Reinstalar dependencias
pip install -r requirements/local.txt
```

### Error: Puerto Ocupado

```
OSError: [Errno 48] Address already in use
```

**Solución:**
```bash
# Verificar procesos usando puertos
lsof -i :8501
lsof -i :8502

# Terminar procesos o usar puertos diferentes
streamlit run interfaces/client_interface.py --server.port 8503
```

### Error: Documentos No Encontrados

```
No se encontraron documentos para procesar
```

**Solución:**
```bash
# Verificar directorio de documentos
ls -la data/documents/

# Copiar documentos manualmente
cp path/to/pdfs/* data/documents/
```

### Error: Base de Datos

```
Error inicializando base de datos
```

**Solución:**
```bash
# Verificar permisos de directorio
chmod 755 data/sessions/

# Recrear base de datos
rm -f data/sessions/conversations.db
python -c "from utils.database import db_manager; print('BD recreada')"
```

## Configuración Avanzada

### Personalizar Puertos

```bash
# Variables de entorno
export CLIENT_PORT=8601
export ADVISOR_PORT=8602

# O en .env
CLIENT_PORT=8601
ADVISOR_PORT=8602
```

### Configurar Logging

```bash
# Nivel de logging en .env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Archivos de log
tail -f logs/application.log
```

### Datos Personalizados

```bash
# Agregar PDFs propios
cp mis_documentos/*.pdf data/documents/

# Agregar Excel de vehículos personalizado
cp mi_catalogo.xlsx data/vehicles/carros.xlsx
```

## Monitoreo y Mantenimiento

### Logs del Sistema

```bash
# Ver logs en tiempo real
tail -f logs/*.log

# Logs por componente
grep "consultant" logs/application.log
grep "quotation" logs/application.log
```

### Limpieza de Datos

```bash
# Limpiar sesiones antiguas (cuidado en producción)
rm -f data/sessions/conversations.db

# Limpiar vector store (se reconstruirá automáticamente)
rm -rf data/vectors/*
```

### Backup de Datos

```bash
# Backup de base de datos
cp data/sessions/conversations.db backup/conversations_$(date +%Y%m%d).db

# Backup de configuración
cp .env backup/env_$(date +%Y%m%d).backup
```

## Próximos Pasos

Después de la instalación exitosa:

1. **Revisar Casos de Uso:** `docs/USE_CASES.md`
2. **Entender Arquitectura:** `docs/ARCHITECTURE.md`  
3. **Despliegue en Nube:** `docs/CLOUD_DEPLOYMENT.md`
4. **Personalización:** Modificar prompts y configuraciones según necesidades

## Soporte

Para problemas técnicos:

1. Revisar logs en `logs/`
2. Ejecutar tests: `python tests/test_basic_functionality.py`
3. Verificar health check del sistema
4. Consultar documentación adicional en `docs/`

El sistema está diseñado para ser robusto y proporcionar mensajes de error detallados para facilitar la resolución de problemas.
