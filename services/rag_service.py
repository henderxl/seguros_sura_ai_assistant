"""
Servicio RAG (Retrieval-Augmented Generation) para consultas sobre seguros.
Procesa documentos PDF y proporciona búsqueda semántica con respuestas contextualizadas.
"""

import os
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pypdf
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain.schema import Document

from utils.config import config
from utils.logging_config import get_logger

logger = get_logger("rag_service")

class DocumentProcessor:
    """Procesador de documentos PDF para el sistema RAG"""
    
    def __init__(self):
        self.logger = get_logger("document_processor")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extrae texto de un archivo PDF
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n\n--- Página {page_num + 1} ---\n\n"
                            text += page_text
                    except Exception as e:
                        self.logger.warning(f"Error extrayendo página {page_num + 1} de {pdf_path.name}: {str(e)}")
                
                self.logger.info(f"Texto extraído de {pdf_path.name}: {len(text)} caracteres")
                return text
                
        except Exception as e:
            self.logger.error(f"Error procesando PDF {pdf_path.name}: {str(e)}")
            return ""
    
    def process_documents(self, documents_dir: Path) -> List[Document]:
        """
        Procesa todos los documentos PDF en un directorio
        
        Args:
            documents_dir: Directorio con documentos PDF
            
        Returns:
            Lista de documentos procesados y chunkeados
        """
        self.logger.info(f"Procesando documentos en: {documents_dir}")
        
        documents = []
        pdf_files = list(documents_dir.glob("*.pdf"))
        
        for pdf_path in pdf_files:
            try:
                # Extraer texto
                text = self.extract_text_from_pdf(pdf_path)
                
                if text.strip():
                    # Crear documento base
                    doc = Document(
                        page_content=text,
                        metadata={
                            "source": str(pdf_path),
                            "filename": pdf_path.name,
                            "type": "insurance_document"
                        }
                    )
                    
                    # Dividir en chunks
                    chunks = self.text_splitter.split_documents([doc])
                    
                    # Agregar metadata adicional a cada chunk
                    for i, chunk in enumerate(chunks):
                        chunk.metadata.update({
                            "chunk_id": f"{pdf_path.stem}_{i}",
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        })
                    
                    documents.extend(chunks)
                    
                    self.logger.info(f"Procesado {pdf_path.name}: {len(chunks)} chunks")
                
            except Exception as e:
                self.logger.error(f"Error procesando {pdf_path.name}: {str(e)}")
        
        self.logger.info(f"Total documentos procesados: {len(documents)} chunks")
        return documents

class VectorStore:
    """Gestión del vector store con ChromaDB"""
    
    def __init__(self):
        self.logger = get_logger("vector_store")
        self.embeddings = AzureOpenAIEmbeddings(
            openai_api_key=config.azure_openai.api_key,
            azure_endpoint=config.azure_openai.endpoint,
            openai_api_version=config.azure_openai.api_version,
            azure_deployment=config.azure_openai.embedding_deployment
        )
        self.client = None
        self.collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente de ChromaDB"""
        try:
            # Configurar ChromaDB para persistencia local
            vector_path = config.get_absolute_path(config.database.vector_store_path)
            vector_path.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(vector_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Crear o obtener colección
            self.collection = self.client.get_or_create_collection(
                name="seguros_sura_documents",
                metadata={"description": "Documentos de seguros Sura para RAG"}
            )
            
            self.logger.info(f"Vector store inicializado en: {vector_path}")
            
        except Exception as e:
            self.logger.error(f"Error inicializando vector store: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Document]) -> int:
        """
        Agrega documentos al vector store
        
        Args:
            documents: Lista de documentos a agregar
            
        Returns:
            Número de documentos agregados
        """
        if not documents:
            return 0
        
        try:
            # Preparar datos para ChromaDB
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            ids = [str(uuid.uuid4()) for _ in documents]
            
            # Generar embeddings
            self.logger.info(f"Generando embeddings para {len(documents)} documentos")
            embeddings = self.embeddings.embed_documents(texts)
            
            # Agregar a ChromaDB
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Agregados {len(documents)} documentos al vector store")
            return len(documents)
            
        except Exception as e:
            self.logger.error(f"Error agregando documentos: {str(e)}")
            raise
    
    def search_similar(self, query: str, k: int = None) -> List[Tuple[Document, float]]:
        """
        Busca documentos similares a una consulta
        
        Args:
            query: Consulta de búsqueda
            k: Número de resultados a retornar
            
        Returns:
            Lista de tuplas (documento, score)
        """
        k = k or config.rag.top_k_results
        
        try:
            # Generar embedding de la consulta
            query_embedding = self.embeddings.embed_query(query)
            
            # Buscar en ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convertir resultados
            documents_with_scores = []
            
            if results["documents"] and results["documents"][0]:
                for i, (text, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    doc = Document(page_content=text, metadata=metadata)
                    # Convertir distancia a score de similaridad (1 - distance)
                    score = 1.0 - distance
                    documents_with_scores.append((doc, score))
            
            self.logger.info(f"Búsqueda completada: {len(documents_with_scores)} resultados")
            return documents_with_scores
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict:
        """Obtiene estadísticas de la colección"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {"total_documents": 0, "error": str(e)}

class RAGService:
    """Servicio principal RAG para consultas sobre seguros"""
    
    def __init__(self):
        self.logger = get_logger("rag_service")
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.llm = AzureChatOpenAI(
            api_key=config.azure_openai.api_key,
            azure_endpoint=config.azure_openai.endpoint,
            api_version=config.azure_openai.api_version,
            azure_deployment=config.azure_openai.chat_deployment,
            temperature=config.azure_openai.temperature,
            max_tokens=config.azure_openai.max_tokens
        )
        
        # Cargar preguntas y respuestas de ejemplo
        self.qa_examples = self._load_qa_examples()
    
    def _load_qa_examples(self) -> List[Dict]:
        """Carga ejemplos de preguntas y respuestas desde el archivo proporcionado"""
        try:
            qa_file = config.get_absolute_path("data/documents/Ejemplos preguntas respuestas.txt")
            
            if qa_file.exists():
                with open(qa_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parsear contenido (formato simple por ahora)
                examples = []
                lines = content.split('\n')
                current_qa = {}
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("Pregunta:"):
                        if current_qa:
                            examples.append(current_qa)
                        current_qa = {"pregunta": line.replace("Pregunta:", "").strip()}
                    elif line.startswith("Respuesta:"):
                        current_qa["respuesta"] = line.replace("Respuesta:", "").strip()
                
                if current_qa:
                    examples.append(current_qa)
                
                self.logger.info(f"Cargados {len(examples)} ejemplos de Q&A")
                return examples
            
        except Exception as e:
            self.logger.warning(f"No se pudieron cargar ejemplos Q&A: {str(e)}")
        
        return []
    
    def initialize_documents(self, force_reload: bool = False) -> bool:
        """
        Inicializa los documentos en el vector store
        
        Args:
            force_reload: Si True, recarga todos los documentos
            
        Returns:
            True si se inicializó correctamente
        """
        try:
            # Verificar si ya hay documentos cargados
            stats = self.vector_store.get_collection_stats()
            
            if stats["total_documents"] > 0 and not force_reload:
                self.logger.info(f"Vector store ya tiene {stats['total_documents']} documentos cargados")
                return True
            
            # Procesar documentos
            documents_dir = config.get_absolute_path("data/documents")
            
            if not documents_dir.exists():
                self.logger.error(f"Directorio de documentos no existe: {documents_dir}")
                return False
            
            documents = self.document_processor.process_documents(documents_dir)
            
            if documents:
                self.vector_store.add_documents(documents)
                self.logger.info("Documentos inicializados en vector store")
                return True
            else:
                self.logger.warning("No se encontraron documentos para procesar")
                return False
        
        except Exception as e:
            self.logger.error(f"Error inicializando documentos: {str(e)}")
            return False
    
    def query(self, question: str, include_sources: bool = True) -> Dict:
        """
        Procesa una consulta usando RAG
        
        Args:
            question: Pregunta del usuario
            include_sources: Si incluir fuentes en la respuesta
            
        Returns:
            Dict con respuesta y metadata
        """
        self.logger.info(f"Procesando consulta: {question[:100]}...")
        
        try:
            # Buscar documentos relevantes
            relevant_docs = self.vector_store.search_similar(question)
            
            if not relevant_docs:
                return {
                    "answer": "No encontré información específica sobre tu consulta en los documentos de Seguros Sura. ¿Podrías reformular tu pregunta o ser más específico?",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Filtrar por threshold de similaridad
            filtered_docs = [
                (doc, score) for doc, score in relevant_docs 
                if score >= config.rag.similarity_threshold
            ]
            
            if not filtered_docs:
                return {
                    "answer": "La información disponible no parece ser muy relevante para tu consulta. Te recomiendo contactar a un asesor para una respuesta más precisa.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Preparar contexto para el LLM
            context = self._prepare_context(filtered_docs)
            
            # Generar respuesta
            answer = self._generate_answer(question, context)
            
            # Preparar fuentes
            sources = []
            if include_sources:
                sources = self._extract_sources(filtered_docs)
            
            # Calcular confianza promedio
            confidence = sum(score for _, score in filtered_docs) / len(filtered_docs)
            
            result = {
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "docs_used": len(filtered_docs)
            }
            
            self.logger.info(
                "Consulta procesada",
                docs_used=len(filtered_docs),
                confidence=confidence,
                answer_length=len(answer)
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error procesando consulta: {str(e)}")
            return {
                "answer": "Lo siento, ocurrió un error procesando tu consulta. Por favor intenta nuevamente o contacta a un asesor.",
                "sources": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _prepare_context(self, docs_with_scores: List[Tuple[Document, float]]) -> str:
        """Prepara contexto para el LLM desde documentos relevantes"""
        context_parts = []
        
        for i, (doc, score) in enumerate(docs_with_scores):
            source_info = f"[Fuente: {doc.metadata.get('filename', 'Desconocida')}]"
            context_parts.append(f"{source_info}\n{doc.page_content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str) -> str:
        """Genera respuesta usando el LLM con contexto RAG"""
        
        prompt = f"""
        Eres un asesor amigable y experto de Seguros Sura Colombia que ayuda a clientes con sus consultas sobre seguros de autos.
        
        Responde la siguiente pregunta basándote ÚNICAMENTE en la información proporcionada del contexto.
        
        INSTRUCCIONES PARA RESPONDER:
        - Sé amigable, cercano y empático, como un asesor humano experimentado
        - Analiza cuidadosamente tablas, listas y datos estructurados en el contexto
        - Para tablas de "Coberturas": si una cobertura no tiene deducible especificado, significa que no aplica deducible
        - Para "Pérdida total hurto" vs "Pérdida total daños", son coberturas distintas con reglas diferentes
        - Proporciona información precisa con montos, porcentajes y condiciones específicas
        - Si no tienes la información específica, sugiere contactar a un asesor para mayor claridad
        - Evita mencionar "contexto proporcionado", "sistema", "base de datos" - habla de forma natural
        - Incluye detalles relevantes y menciona todas las opciones disponibles
        - Usa expresiones naturales como "Te cuento que...", "En nuestros planes...", "Lo que puedo decirte es..."
        
        CONTEXTO:
        {context}
        
        PREGUNTA: {question}
        
        RESPUESTA:
        """
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            self.logger.error(f"Error generando respuesta con LLM: {str(e)}")
            return "Lo siento, no pude generar una respuesta en este momento. Por favor contacta a un asesor."
    
    def _extract_sources(self, docs_with_scores: List[Tuple[Document, float]]) -> List[Dict]:
        """Extrae información de fuentes de los documentos"""
        sources = []
        
        for doc, score in docs_with_scores:
            source = {
                "filename": doc.metadata.get('filename', 'Desconocido'),
                "chunk_id": doc.metadata.get('chunk_id', ''),
                "similarity_score": round(score, 3)
            }
            sources.append(source)
        
        return sources
    
    def get_qa_examples(self) -> List[Dict]:
        """Retorna ejemplos de preguntas y respuestas cargados"""
        return self.qa_examples
    
    def health_check(self) -> Dict:
        """Verifica el estado del servicio RAG"""
        try:
            stats = self.vector_store.get_collection_stats()
            
            return {
                "status": "healthy",
                "vector_store_docs": stats.get("total_documents", 0),
                "qa_examples_loaded": len(self.qa_examples),
                "llm_configured": bool(self.llm),
                "embeddings_configured": bool(self.vector_store.embeddings)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Instancia global del servicio RAG
rag_service = RAGService()
