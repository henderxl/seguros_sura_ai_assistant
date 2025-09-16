"""
Agente Base - Clase padre para todos los agentes del sistema.
Define estructura común, capacidades y funcionalidades base.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
import uuid

from utils.logging_config import get_logger
from utils.database import db_manager

@dataclass
class AgentState:
    """Estado compartido entre agentes"""
    session_id: str
    user_type: str  # "client" o "advisor"
    current_agent: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    last_user_input: str = ""
    agent_response: str = ""
    conversation_context: Dict[str, Any] = field(default_factory=dict)  # Para contexto multi-turno
    user_preferences: Dict[str, Any] = field(default_factory=dict)  # Preferencias aprendidas
    needs_human_intervention: bool = False
    escalation_reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class AgentCapabilities(Enum):
    """Capacidades que pueden tener los agentes"""
    CONSULTATION = "consultation"
    QUOTATION = "quotation"
    VISION = "vision"
    EXPEDITION = "expedition"
    ESCALATION = "escalation"

class AgentRegistry:
    """Registro global de agentes y sus capacidades"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.capabilities: Dict[str, List[AgentCapabilities]] = {}
    
    def register_agent(self, agent: 'BaseAgent', capabilities: List[AgentCapabilities]):
        """Registra un agente con sus capacidades"""
        self.agents[agent.name] = agent
        self.capabilities[agent.name] = capabilities
    
    def get_agents_by_capability(self, capability: AgentCapabilities) -> List[str]:
        """Obtiene agentes que tienen una capacidad específica"""
        return [
            agent_name for agent_name, caps in self.capabilities.items()
            if capability in caps
        ]

# Instancia global del registro
agent_registry = AgentRegistry()

class BaseAgent:
    """Clase base para todos los agentes del sistema"""
    
    def __init__(self, name: str):
        self.name = name
        self.agent_type = name  # CRÍTICO: Definir agent_type
        self.logger = get_logger(f"agent_{name}")
        self.db_manager = db_manager
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Método principal para procesar una solicitud
        Debe ser implementado por cada agente específico
        """
        raise NotImplementedError("Cada agente debe implementar el método process")
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> bool:
        """
        Determina si este agente puede manejar la entrada del usuario
        Debe ser implementado por cada agente específico
        """
        raise NotImplementedError("Cada agente debe implementar el método can_handle")
    
    def update_state(self, state: AgentState, **kwargs) -> AgentState:
        """Actualiza el estado del agente con nuevos datos"""
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        state.current_agent = self.name
        state.updated_at = datetime.now()
        
        return state
    
    def add_message_to_history(self, state: AgentState, role: str, content: str, 
                              metadata: Optional[Dict[str, Any]] = None) -> AgentState:
        """Agrega un mensaje al historial de conversación"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        state.conversation_history.append(message)
        
        # Persistir en base de datos
        self.db_manager.add_message(
            session_id=state.session_id,
            agent_type=self.name,
            content=content,
            metadata=metadata
        )
        
        return state
    
    def format_response(self, content: str, response_type: str = "standard", 
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Formatea una respuesta estándar del agente"""
        return {
            "content": content,
            "type": response_type,
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
    
    def save_agent_state(self, state: AgentState, agent_data: Dict[str, Any]):
        """Guarda estado específico del agente en la base de datos"""
        try:
            self.db_manager.save_agent_state(
                session_id=state.session_id,
                agent_type=self.name,
                state_data=agent_data
            )
        except Exception as e:
            self.logger.error(f"Error guardando estado del agente: {str(e)}")
    
    def load_agent_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Carga estado específico del agente desde la base de datos"""
        try:
            return self.db_manager.get_agent_state(session_id, self.name)
        except Exception as e:
            self.logger.error(f"Error cargando estado del agente: {str(e)}")
            return None
    
    def log_interaction(self, state: AgentState, user_input: Any, agent_response: Any, **kwargs):
        """Registra interacción para análisis y debugging"""
        interaction_data = {
            "session_id": state.session_id,
            "agent": self.name,
            "user_input": str(user_input)[:500],  # Limitar tamaño
            "agent_response": str(agent_response)[:500],
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        self.logger.info("Interacción registrada", **interaction_data)
    
    def log_error(self, error: Exception, state: AgentState, context: Dict[str, Any]):
        """Registra errores con contexto completo"""
        error_data = {
            "session_id": state.session_id,
            "agent": self.name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.error("Error en agente", **error_data)
    
    def update_state(self, state: AgentState, **kwargs) -> AgentState:
        """Actualiza el estado del agente con GESTIÓN PROFESIONAL multi-turno"""
        
        # Mantener historial de estados para conversaciones multi-turno
        if 'state_history' not in state.context_data:
            state.context_data['state_history'] = []
        
        # Guardar estado anterior SIN recursión
        # Solo incluir datos esenciales, NO el history completo
        essential_context = {
            k: v for k, v in state.context_data.items() 
            if k not in ['state_history']  # EXCLUIR history para evitar recursión
        }
        
        state.context_data['state_history'].append({
            'timestamp': datetime.now().isoformat(),
            'agent_type': self.agent_type,
            'previous_agent': state.current_agent,
            'context_snapshot': essential_context  # Solo contexto esencial
        })
        
        # Limitar historial a últimos 10 estados
        if len(state.context_data['state_history']) > 10:
            state.context_data['state_history'] = state.context_data['state_history'][-10:]
        
        # Actualizar campos específicos
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                state.context_data[key] = value
        
        state.current_agent = self.name
        state.updated_at = datetime.now()
        return state
    
    
    def set_escalation(self, state: AgentState, reason: str):
        """Marca el estado para escalamiento humano"""
        state.needs_human_intervention = True
        state.escalation_reason = reason
        state.updated_at = datetime.now()
        
        self.logger.warning(f"Escalamiento activado: {reason}", session_id=state.session_id)
    
    def extract_conversation_context(self, state: AgentState) -> Dict[str, Any]:
        """
        Extrae contexto relevante de la conversación para mejorar respuestas multi-turno
        
        Args:
            state: Estado actual del agente
            
        Returns:
            Dict con contexto relevante extraído
        """
        context = {
            "conversation_length": len(state.conversation_history),
            "recent_topics": [],
            "user_sentiment": "neutral",
            "unresolved_questions": [],
            "mentioned_entities": []
        }
        
        # Analizar últimos 5 mensajes
        recent_messages = state.conversation_history[-5:] if state.conversation_history else []
        
        for msg in recent_messages:
            if msg["role"] == "user":
                content = msg["content"].lower()
                
                # Detectar temas
                if any(word in content for word in ["cotizar", "cotización", "precio"]):
                    context["recent_topics"].append("quotation")
                elif any(word in content for word in ["comprar", "expedir", "contratar"]):
                    context["recent_topics"].append("purchase")
                elif any(word in content for word in ["problema", "error", "no funciona"]):
                    context["recent_topics"].append("issue")
                elif any(word in content for word in ["ayuda", "asesor", "hablar"]):
                    context["recent_topics"].append("help")
                
                # Detectar sentimiento básico
                if any(word in content for word in ["gracias", "perfecto", "excelente", "bien"]):
                    context["user_sentiment"] = "positive"
                elif any(word in content for word in ["problema", "mal", "no entiendo", "error"]):
                    context["user_sentiment"] = "negative"
                
                # Detectar preguntas no resueltas (que terminan en ?)
                if "?" in content and not any(word in content for word in ["gracias", "perfecto"]):
                    context["unresolved_questions"].append(content.strip())
        
        # Remover duplicados
        context["recent_topics"] = list(set(context["recent_topics"]))
        
        return context
    
    def update_user_preferences(self, state: AgentState, preference_key: str, preference_value: Any):
        """
        Actualiza preferencias del usuario aprendidas durante la conversación
        
        Args:
            state: Estado actual del agente
            preference_key: Clave de la preferencia
            preference_value: Valor de la preferencia
        """
        if not state.user_preferences:
            state.user_preferences = {}
        
        state.user_preferences[preference_key] = preference_value
        
        # Persistir en base de datos
        try:
            self.db_manager.save_user_preference(
                session_id=state.session_id,
                preference_key=preference_key,
                preference_value=preference_value
            )
        except Exception as e:
            self.logger.error(f"Error guardando preferencia: {str(e)}")
    
    def should_suggest_human_escalation(self, state: AgentState) -> tuple[bool, str]:
        """
        Determina si debería sugerir escalamiento humano basado en patrones de conversación
        
        Args:
            state: Estado actual del agente
            
        Returns:
            Tuple (should_escalate, reason)
        """
        context = self.extract_conversation_context(state)
        
        # Escalamiento por longitud de conversación sin resolución (más restrictivo)
        if context["conversation_length"] > 20 and context["user_sentiment"] == "negative":
            return True, "Conversación muy larga con sentimiento negativo"
        
        # Escalamiento por preguntas repetidas no resueltas (más restrictivo)
        if len(context["unresolved_questions"]) > 5:
            return True, "Muchas preguntas sin resolver"
        
        # Escalamiento por solicitud explícita
        if "help" in context["recent_topics"] and context["user_sentiment"] in ["negative", "neutral"]:
            return True, "Usuario solicita ayuda con posible frustración"
        
        # Escalamiento por cambios frecuentes de tema
        if len(context["recent_topics"]) > 3:
            return True, "Usuario cambia de tema frecuentemente, posible confusión"
        
        return False, ""

class AgentLogger:
    """Logger especializado para agentes"""
    
    def __init__(self, agent_name: str):
        self.logger = get_logger(f"agent_{agent_name}")
        self.agent_name = agent_name
    
    def info(self, message: str, **kwargs):
        """Log de información"""
        self.logger.info(f"[{self.agent_name}] {message}", **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log de advertencia"""
        self.logger.warning(f"[{self.agent_name}] {message}", **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log de error"""
        self.logger.error(f"[{self.agent_name}] {message}", **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log de debug"""
        self.logger.debug(f"[{self.agent_name}] {message}", **kwargs)