"""
Configuración centralizada del sistema de agentes de IA para Seguros Sura.
Maneja variables de entorno, configuraciones por ambiente y parámetros del sistema.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

@dataclass
class DatabaseConfig:
    """Configuración de bases de datos"""
    sqlite_path: str = "data/sessions/conversations.db"
    vector_store_path: str = "data/vectors/chroma_db"
    
@dataclass 
class AzureOpenAIConfig:
    """Configuración de Azure OpenAI"""
    api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    chat_deployment: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
    embedding_deployment: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    temperature: float = 0.1
    max_tokens: int = 2000
    
@dataclass
class RAGConfig:
    """Configuración del sistema RAG"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    similarity_threshold: float = 0.3  # Threshold más permisivo para mejor recall
    
@dataclass
class AgentConfig:
    """Configuración de agentes"""
    max_iterations: int = 10
    timeout_seconds: int = 30
    memory_window: int = 10
    
@dataclass
class InterfaceConfig:
    """Configuración de interfaces"""
    client_port: int = 8501
    advisor_port: int = 8502
    page_title: str = "Seguros Sura - Asistente IA"
    page_icon: str = "🏢"
    
@dataclass
class ServicesConfig:
    """Configuración de servicios externos"""
    cotizacion_excel_path: str = "data/vehicles/carros.xlsx"
    expedition_api_url: str = "http://localhost:8000"
    documents_path: str = "data/documents"
    images_path: str = "data/images"

class Config:
    """Configuración principal del sistema"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local")
        self.debug = os.getenv("DEBUG", "True").lower() == "true"
        self.project_root = Path(__file__).parent.parent
        
        # Configuraciones por componente
        self.database = DatabaseConfig()
        self.azure_openai = AzureOpenAIConfig()
        self.rag = RAGConfig()
        self.agents = AgentConfig()
        self.interface = InterfaceConfig()
        self.services = ServicesConfig()
        
        # Validar configuraciones críticas
        self._validate_config()
        
    def _validate_config(self):
        """Valida configuraciones críticas"""
        import warnings
        
        if not self.azure_openai.api_key:
            warnings.warn("⚠️  AZURE_OPENAI_API_KEY no configurada - algunas funciones estarán limitadas", UserWarning)
            print("💡 Para configurar: edita el archivo .env y agrega AZURE_OPENAI_API_KEY=tu-api-key")
        
        if not self.azure_openai.endpoint:
            warnings.warn("⚠️  AZURE_OPENAI_ENDPOINT no configurado - usando valor por defecto", UserWarning)
            
        # Crear directorios necesarios
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Crea directorios necesarios si no existen"""
        dirs_to_create = [
            Path(self.database.sqlite_path).parent,
            Path(self.database.vector_store_path).parent,
            Path(self.services.documents_path),
            Path(self.services.images_path),
            self.project_root / "logs"
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convierte ruta relativa a absoluta desde project_root"""
        return self.project_root / relative_path

# Instancia global de configuración
config = Config()
