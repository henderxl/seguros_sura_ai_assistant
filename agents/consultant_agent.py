"""
Agente Consultor - Especializado en responder preguntas sobre seguros usando RAG.
Maneja consultas generales sobre productos, coberturas, planes y condiciones.
"""

import re
from typing import Dict, Any, List
from langchain_openai import AzureChatOpenAI

from agents.base_agent import BaseAgent, AgentState, AgentCapabilities
from services.rag_service import rag_service
from utils.config import config

class ConsultantAgent(BaseAgent):
    """Agente especializado en consultas sobre seguros usando RAG"""
    
    def __init__(self):
        super().__init__("consultant")
        self.rag_service = rag_service
        self.llm = AzureChatOpenAI(
            api_key=config.azure_openai.api_key,
            azure_endpoint=config.azure_openai.endpoint,
            api_version=config.azure_openai.api_version,
            azure_deployment=config.azure_openai.chat_deployment,
            temperature=config.azure_openai.temperature
        )
        
        # Palabras clave PRIORITARIAS para consultas generales
        self.priority_consultation_phrases = [
            "qué cubre", "qué incluye", "plan básico", "plan clásico", "plan global",
            "diferencia entre", "cómo funciona", "coberturas del", "beneficios del"
        ]
        
        # Palabras clave generales para consultas
        self.consultation_keywords = [
            "cobertura", "plan", "póliza", "seguro", "deducible", "prima", 
            "asistencia", "beneficio", "condiciones", "exclusiones", "vigencia", 
            "daños", "hurto", "terceros", "vidrios", "llaves", "requisitos"
        ]
        
        # Saludos y consultas básicas
        self.greeting_keywords = [
            "hola", "buenos días", "buenas tardes", "buenas noches",
            "buen día", "saludos", "holi", "hello", "hi", "hey",
            "qué tal", "cómo está", "ayuda", "información", "ayudar"
        ]
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> bool:
        """
        Determina si puede manejar consultas generales sobre seguros
        
        Args:
            user_input: Entrada del usuario
            context: Contexto de la conversación
            
        Returns:
            True si es una consulta general sobre seguros
        """
        user_input_lower = user_input.lower()
        
        # PRIORIDAD MÁXIMA: Frases específicas de consulta
        has_priority_phrases = any(
            phrase in user_input_lower 
            for phrase in self.priority_consultation_phrases
        )
        
        # Si tiene frases prioritarias, SIEMPRE maneja consultant
        if has_priority_phrases:
            return True
        
        # Verificar palabras clave de consulta
        has_consultation_keywords = any(
            keyword in user_input_lower 
            for keyword in self.consultation_keywords
        )
        
        # Verificar saludos y consultas básicas
        has_greeting_keywords = any(
            keyword in user_input_lower 
            for keyword in self.greeting_keywords
        )
        
        # Verificar que no sea una solicitud EXPLÍCITA de cotización o expedición
        explicit_quotation_keywords = ["quiero cotizar", "cotizar mi vehículo", "precio del seguro"]
        explicit_expedition_keywords = ["comprar póliza", "expedir póliza", "emitir póliza"]
        
        is_explicit_quotation = any(kw in user_input_lower for kw in explicit_quotation_keywords)
        is_explicit_expedition = any(kw in user_input_lower for kw in explicit_expedition_keywords)
        
        # Manejar CONVERSACIONES NATURALES - si no es explícitamente otro agente
        is_conversational = len(user_input_lower.split()) <= 3 and not (is_explicit_quotation or is_explicit_expedition)
        
        # Puede manejar si:
        # 1. Tiene palabras clave de consulta y NO es cotización/expedición explícita
        # 2. Es conversacional y no es una solicitud explícita de otro agente  
        # 3. Es un saludo o respuesta corta
        return (has_consultation_keywords and not (is_explicit_quotation or is_explicit_expedition)) or has_greeting_keywords or is_conversational
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Procesa consultas generales usando RAG
        
        Args:
            state: Estado actual del agente
            
        Returns:
            Estado actualizado con respuesta
        """
        try:
            self.logger.info("Procesando consulta general", query=state.last_user_input[:100])
            
            # Verificar si es un saludo básico o conversación corta
            if self._is_basic_greeting(state.last_user_input) or len(state.last_user_input.split()) <= 2:
                response = self._get_conversational_response(state.last_user_input, state)
                state = self.update_state(state, agent_response=response["content"])
                state = self.add_message_to_history(state, "assistant", response["content"])
                return state
            
            # Verificar si el servicio RAG está inicializado
            if not self._ensure_rag_initialized():
                response = self._get_fallback_response(state.last_user_input)
                state = self.update_state(state, agent_response=response["content"])
                state = self.add_message_to_history(state, "assistant", response["content"])
                return state
            
            # Realizar consulta RAG
            rag_result = self.rag_service.query(
                question=state.last_user_input,
                include_sources=True
            )
            
            # Procesar resultado
            if rag_result.get("confidence", 0) >= config.rag.similarity_threshold:
                response = self._format_rag_response(rag_result)
            else:
                response = self._get_low_confidence_response(state.last_user_input, rag_result)
            
            # Actualizar estado
            state = self.update_state(state, agent_response=response["content"])
            state = self.add_message_to_history(
                state, 
                "assistant", 
                response["content"], 
                metadata=response.get("metadata", {})
            )
            
            # Guardar estado específico del agente
            self.save_agent_state(state, {
                "last_query": state.last_user_input,
                "rag_confidence": rag_result.get("confidence", 0),
                "sources_used": len(rag_result.get("sources", [])),
                "docs_used": rag_result.get("docs_used", 0)
            })
            
            self.log_interaction(
                state,
                state.last_user_input,
                response["content"],
                confidence=rag_result.get("confidence", 0),
                sources_count=len(rag_result.get("sources", []))
            )
            
            return state
            
        except Exception as e:
            self.log_error(e, state, {"query": state.last_user_input})
            
            error_response = (
                "Disculpa, tuve un problema procesando tu consulta. "
                "Por favor intenta reformular tu pregunta o contacta a un asesor humano."
            )
            
            state = self.update_state(state, agent_response=error_response)
            state = self.add_message_to_history(state, "assistant", error_response)
            
            return state
    
    def _ensure_rag_initialized(self) -> bool:
        """Asegura que el servicio RAG esté inicializado"""
        try:
            health = self.rag_service.health_check()
            
            if health["status"] != "healthy" or health["vector_store_docs"] == 0:
                self.logger.warning("RAG no inicializado, intentando inicializar")
                return self.rag_service.initialize_documents()
            
            return True
            
        except Exception as e:
            self.logger.error("Error verificando estado RAG", error=str(e))
            return False
    
    def _format_rag_response(self, rag_result: Dict) -> Dict[str, Any]:
        """
        Formatea la respuesta RAG para el usuario
        
        Args:
            rag_result: Resultado del sistema RAG
            
        Returns:
            Respuesta formateada
        """
        answer = rag_result["answer"]
        sources = rag_result.get("sources", [])
        confidence = rag_result.get("confidence", 0)
        
        # Enriquecer respuesta con información de fuentes si es relevante
        if sources and confidence > 0.8:
            sources_text = self._format_sources(sources)
            enhanced_answer = f"{answer}\n\n{sources_text}"
        else:
            enhanced_answer = answer
        
        # Agregar sugerencias de seguimiento si es apropiado
        if confidence < 0.9:
            enhanced_answer += "\n\n¿Te gustaría que profundice en algún aspecto específico o tienes alguna otra pregunta?"
        
        return self.format_response(
            content=enhanced_answer,
            response_type="consultation",
            metadata={
                "confidence": confidence,
                "sources_count": len(sources),
                "rag_used": True
            }
        )
    
    def _format_sources(self, sources: List[Dict]) -> str:
        """Formatea las fuentes de información"""
        if not sources:
            return ""
        
        # Agrupar por documento para evitar repetición
        docs = set(source["filename"] for source in sources)
        
        if len(docs) == 1:
            return f"\n*Información basada en: {list(docs)[0]}*"
        else:
            docs_list = ", ".join(sorted(docs))
            return f"\n*Información basada en: {docs_list}*"
    
    def _get_fallback_response(self, query: str) -> Dict[str, Any]:
        """
        Genera respuesta de fallback cuando RAG no está disponible
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Respuesta de fallback
        """
        # Usar ejemplos de Q&A cargados
        qa_examples = self.rag_service.get_qa_examples()
        
        # Buscar coincidencia en ejemplos
        best_match = self._find_best_qa_example(query, qa_examples)
        
        if best_match:
            return self.format_response(
                content=best_match["respuesta"],
                response_type="consultation",
                metadata={"source": "qa_examples", "fallback": True}
            )
        
        # Respuesta genérica
        generic_response = (
            "En Seguros Sura ofrecemos diferentes planes de autos con coberturas completas. "
            "Nuestros planes incluyen cobertura contra daños, hurto, responsabilidad civil "
            "y asistencias especializadas. Para brindarte información más específica sobre "
            "tu consulta, te recomiendo contactar a uno de nuestros asesores especializados."
        )
        
        return self.format_response(
            content=generic_response,
            response_type="consultation",
            metadata={"fallback": True, "generic": True}
        )
    
    def _find_best_qa_example(self, query: str, qa_examples: List[Dict]) -> Dict:
        """
        Encuentra el mejor ejemplo de Q&A para una consulta
        
        Args:
            query: Consulta del usuario
            qa_examples: Lista de ejemplos Q&A
            
        Returns:
            Mejor ejemplo encontrado o None
        """
        if not qa_examples:
            return None
        
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        for qa in qa_examples:
            if "pregunta" not in qa or "respuesta" not in qa:
                continue
            
            pregunta = qa["pregunta"].lower()
            
            # Calcular score simple basado en palabras coincidentes
            query_words = set(re.findall(r'\w+', query_lower))
            pregunta_words = set(re.findall(r'\w+', pregunta))
            
            if query_words and pregunta_words:
                intersection = query_words.intersection(pregunta_words)
                score = len(intersection) / len(query_words.union(pregunta_words))
                
                if score > best_score and score > 0.3:  # Threshold mínimo
                    best_score = score
                    best_match = qa
        
        return best_match
    
    def _get_low_confidence_response(self, query: str, rag_result: Dict) -> Dict[str, Any]:
        """
        Maneja respuestas con baja confianza
        
        Args:
            query: Consulta original
            rag_result: Resultado RAG con baja confianza
            
        Returns:
            Respuesta apropiada para baja confianza
        """
        confidence = rag_result.get("confidence", 0)
        
        if confidence > 0.4:  # Confianza moderada
            answer = rag_result["answer"]
            clarification = (
                "\n\nNota: La información puede no ser completamente específica para tu consulta. "
                "¿Podrías proporcionar más detalles o reformular tu pregunta?"
            )
            content = answer + clarification
        else:  # Confianza muy baja
            content = (
                "No encontré información específica sobre tu consulta en mi base de conocimientos. "
                "Te recomiendo contactar a uno de nuestros asesores especializados que podrá "
                "brindarte información detallada y personalizada sobre nuestros productos y servicios."
            )
        
        return self.format_response(
            content=content,
            response_type="consultation",
            metadata={
                "confidence": confidence,
                "low_confidence": True,
                "escalation_suggested": confidence < 0.3
            }
        )
    
    def get_consultation_summary(self, state: AgentState) -> Dict[str, Any]:
        """
        Genera resumen de las consultas realizadas en la sesión
        
        Args:
            state: Estado actual
            
        Returns:
            Resumen de consultas
        """
        consultation_messages = [
            msg for msg in state.conversation_history 
            if msg.get("agent") == "consultant" and msg.get("role") == "assistant"
        ]
        
        agent_state = self.load_agent_state(state.session_id) or {}
        
        return {
            "total_consultations": len(consultation_messages),
            "last_confidence": agent_state.get("rag_confidence", 0),
            "total_sources_used": agent_state.get("sources_used", 0),
            "consultation_topics": self._extract_topics(consultation_messages)
        }
    
    def _extract_topics(self, messages: List[Dict]) -> List[str]:
        """Extrae temas principales de las consultas"""
        topics = set()
        
        for msg in messages:
            content = msg.get("content", "").lower()
            
            # Identificar temas por palabras clave
            if any(kw in content for kw in ["cobertura", "cubre", "daños"]):
                topics.add("Coberturas")
            if any(kw in content for kw in ["plan", "planes", "diferencia"]):
                topics.add("Planes")
            if any(kw in content for kw in ["deducible", "prima", "costo", "precio"]):
                topics.add("Costos")
            if any(kw in content for kw in ["asistencia", "servicio"]):
                topics.add("Asistencias")
            if any(kw in content for kw in ["requisito", "condición", "exclusión"]):
                topics.add("Condiciones")
        
        return list(topics)
    
    def _is_basic_greeting(self, user_input: str) -> bool:
        """Detecta si es un saludo básico sin consulta específica"""
        user_input_lower = user_input.lower().strip()
        
        # Saludos simples (solo 1-3 palabras)
        words = user_input_lower.split()
        if len(words) <= 3:
            return any(greeting in user_input_lower for greeting in self.greeting_keywords)
        
        return False
    
    def _get_conversational_response(self, user_input: str, state: AgentState) -> Dict[str, Any]:
        """Genera respuesta conversacional inteligente usando LLM"""
        user_input_lower = user_input.lower().strip()
        
        # Contexto de conversación reciente
        recent_messages = state.conversation_history[-3:] if state.conversation_history else []
        conversation_context = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" 
            for msg in recent_messages
        ])
        
        # Usar LLM para respuesta contextual
        try:
            prompt = f"""
            Eres un asesor amigable de Seguros Sura Colombia. El cliente te ha escrito: "{user_input}"
            
            Contexto de la conversación reciente:
            {conversation_context}
            
            Responde de manera natural, amigable y profesional. Si es un saludo, saluda y ofrece ayuda.
            Si es una respuesta corta (como "entonces", "bien", "si"), responde apropiadamente en contexto.
            Mantén el enfoque en seguros de autos.
            
            Respuesta (máximo 100 palabras):
            """
            
            llm_response = self.rag_service.llm.invoke(prompt)
            content = llm_response.content.strip()
            
            return {
                "content": content,
                "confidence": 0.9,
                "sources": []
            }
            
        except Exception as e:
            self.logger.error(f"Error en respuesta conversacional: {str(e)}")
            # Fallback inteligente basado en input
            if any(word in user_input_lower for word in ["hola", "buenas", "buenos", "tardes", "días"]):
                content = "¡Hola! Un gusto saludarte. Soy tu asesor de Seguros Sura. ¿En qué puedo ayudarte hoy?"
            elif any(word in user_input_lower for word in ["entonces", "bien", "ok", "si"]):
                content = "Perfecto. ¿Te gustaría que te ayude con alguna consulta sobre nuestros seguros de autos?"
            else:
                content = "Te escucho. ¿En qué puedo ayudarte con tus seguros de autos?"
            
            return {
                "content": content,
                "confidence": 0.8,
                "sources": []
            }

    def _get_greeting_response(self) -> Dict[str, Any]:
        """Genera respuesta de saludo y presentación"""
        return {
            "content": "¡Hola! Soy tu asistente de Seguros Sura. Puedo ayudarte con:\n\n• **Consultas** sobre planes y coberturas de seguros\n• **Cotizaciones** de seguros (puedes subir una foto de tu vehículo)\n• **Expedición** de pólizas\n\n¿En qué puedo ayudarte hoy?",
            "confidence": 1.0,
            "sources": []
        }
