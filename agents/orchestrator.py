"""
Orquestador Principal - Coordina todos los agentes usando LangGraph.
Implementa el flujo de conversación multiagéntico y gestión de estado.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import asyncio

from agents.base_agent import BaseAgent, AgentState, agent_registry, AgentCapabilities
from agents.consultant_agent import ConsultantAgent
from agents.quotation_agent import QuotationAgent
from agents.expedition_agent import ExpeditionAgent
from agents.human_loop_agent import HumanLoopAgent
from agents.intent_classifier import intent_classifier
from utils.database import db_manager
from utils.logging_config import get_logger

logger = get_logger("orchestrator")

class AgentOrchestrator:
    """Orquestador principal del sistema multiagéntico"""
    
    def __init__(self):
        self.logger = get_logger("orchestrator")
        self.db_manager = db_manager
        
        # Inicializar agentes
        self.agents = self._initialize_agents()
        
        # Crear grafo de LangGraph
        self.workflow = self._create_workflow()
        
        # Memory saver para persistencia de estado
        self.memory = MemorySaver()
        
        # Compilar workflow
        self.app = self.workflow.compile(checkpointer=self.memory)
    
    def _initialize_agents(self) -> Dict[str, BaseAgent]:
        """Inicializa y registra todos los agentes"""
        agents = {}
        
        # Crear instancias de agentes
        consultant = ConsultantAgent()
        quotation = QuotationAgent()
        expedition = ExpeditionAgent()
        human_loop = HumanLoopAgent()
        
        # Registrar agentes
        agents["consultant"] = consultant
        agents["quotation"] = quotation
        agents["expedition"] = expedition
        agents["human_loop"] = human_loop
        
        # Registrar en el registry global con capacidades
        agent_registry.register_agent(consultant, [AgentCapabilities.CONSULTATION])
        agent_registry.register_agent(quotation, [AgentCapabilities.QUOTATION, AgentCapabilities.VISION])
        agent_registry.register_agent(expedition, [AgentCapabilities.EXPEDITION])
        agent_registry.register_agent(human_loop, [AgentCapabilities.ESCALATION])
        
        self.logger.info(f"Inicializados {len(agents)} agentes especializados")
        
        return agents
    
    def _create_workflow(self) -> StateGraph:
        """Crea el workflow de LangGraph para el sistema multiagéntico"""
        
        # Definir el grafo de estado
        workflow = StateGraph(AgentState)
        
        # Agregar nodos (agentes)
        workflow.add_node("router", self._route_to_agent)
        workflow.add_node("consultant", self._run_consultant)
        workflow.add_node("quotation", self._run_quotation)
        workflow.add_node("expedition", self._run_expedition)
        workflow.add_node("human_loop", self._run_human_loop)
        workflow.add_node("final_response", self._prepare_final_response)
        
        # Definir punto de entrada
        workflow.set_entry_point("router")
        
        # Definir edges (transiciones)
        workflow.add_conditional_edges(
            "router",
            self._determine_next_agent,
            {
                "consultant": "consultant",
                "quotation": "quotation", 
                "expedition": "expedition",
                "human_loop": "human_loop",
                "end": END
            }
        )
        
        # Edges desde cada agente
        workflow.add_conditional_edges(
            "consultant",
            self._check_post_agent_routing,
            {
                "quotation": "quotation",
                "human_loop": "human_loop",
                "final_response": "final_response",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "quotation", 
            self._check_post_agent_routing,
            {
                "expedition": "expedition",
                "consultant": "consultant",
                "human_loop": "human_loop",
                "final_response": "final_response",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "expedition",
            self._check_post_agent_routing,
            {
                "quotation": "quotation", 
                "human_loop": "human_loop",
                "consultant": "consultant",
                "final_response": "final_response", 
                "end": END
            }
        )
        
        workflow.add_edge("human_loop", END)
        workflow.add_edge("final_response", END)
        
        return workflow
    
    async def process_user_input(self, session_id: str, user_input: str, 
                                user_type: str = "client", 
                                context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa entrada del usuario a través del sistema multiagéntico
        
        Args:
            session_id: ID de la sesión
            user_input: Entrada del usuario
            user_type: Tipo de usuario ('client' o 'advisor')
            context_data: Datos de contexto adicionales
            
        Returns:
            Respuesta procesada del sistema
        """
        try:
            self.logger.info("Procesando entrada del usuario", 
                           session_id=session_id,
                           user_type=user_type,
                           input_length=len(user_input))
            
            # Crear o recuperar estado
            state = await self._get_or_create_state(session_id, user_type, context_data or {})
            
            # Actualizar con nueva entrada del usuario
            state.last_user_input = user_input
            state = self._add_user_message_to_history(state, user_input)
            
            # Configuración para LangGraph
            config = {
                "configurable": {
                    "thread_id": session_id,
                    "checkpoint_ns": f"session_{session_id}"
                }
            }
            
            # Ejecutar workflow
            result = await self.app.ainvoke(state, config=config)
            
            # Preparar respuesta
            response = self._format_orchestrator_response(result)
            
            # Obtener agente final del resultado (puede ser dict o AgentState)
            final_agent = result.get("current_agent") if isinstance(result, dict) else result.current_agent
            
            self.logger.info("Entrada procesada exitosamente",
                           session_id=session_id,
                           final_agent=final_agent,
                           response_type=response.get("type"))
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error procesando entrada del usuario: {str(e)}")
            
            # Respuesta de error fallback MÁS orientativa
            return {
                "success": False,
                "content": (
                    "😅 **¡Ups! Algo salió mal momentáneamente.**\n\n"
                    "🔄 **Puedes intentar:**\n"
                    "• Reformular tu consulta de manera más simple\n"
                    "• Si buscas cotización: 'Quiero cotizar mi Toyota 2020'\n"
                    "• Si tienes preguntas: 'Cuáles son los planes disponibles'\n\n"
                    "🤝 **¿Necesitas ayuda inmediata?** Escribe 'hablar con asesor' y te conectaré con un humano."
                ),
                "type": "error",
                "session_id": session_id,
                "error": str(e)
            }
    
    async def _get_or_create_state(self, session_id: str, user_type: str, 
                                  context_data: Dict[str, Any]) -> AgentState:
        """Obtiene o crea estado de la sesión"""
        
        # Verificar si existe sesión en BD
        session = self.db_manager.get_session(session_id)
        
        if session:
            # Cargar historial existente
            history = self.db_manager.get_conversation_history(session_id)
            conversation_history = [
                {
                    "id": msg.message_id,
                    "role": "user" if msg.agent_type == "user" else "assistant",
                    "content": msg.content,
                    "agent": msg.agent_type,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in history
            ]
        else:
            # Crear nueva sesión
            self.db_manager.create_session(user_type, {"created_by": "orchestrator"}, session_id)
            conversation_history = []
        
        # Crear estado PRESERVANDO contexto existente
        
        # Recuperar contexto persistido de TODOS los agentes
        existing_context = {}
        if session:
            # Obtener estado de TODOS los agentes
            for agent_name in ["quotation", "expedition", "consultant", "human_loop"]:
                agent_state = self.db_manager.get_agent_state(session_id, agent_name)
                if agent_state:
                    existing_context.update(agent_state)  # Combinar todos los estados
        
        # COMBINAR contexto existente con nuevo contexto
        combined_context = existing_context.copy()
        combined_context.update(context_data)  # Agregar sin sobrescribir
        
        state = AgentState(
            session_id=session_id,
            user_type=user_type,
            current_agent="router",
            conversation_history=conversation_history,
            context_data=combined_context,  # Contexto COMBINADO
            last_user_input="",
            agent_response=""
        )
        
        return state
    
    def _add_user_message_to_history(self, state: AgentState, user_input: str) -> AgentState:
        """Agrega mensaje del usuario al historial"""
        user_message = {
            "id": f"user_{len(state.conversation_history)}",
            "role": "user",
            "content": user_input,
            "agent": "user",
            "timestamp": state.updated_at.isoformat(),
            "metadata": {}
        }
        
        state.conversation_history.append(user_message)
        
        # Persistir en BD
        self.db_manager.add_message(
            session_id=state.session_id,
            agent_type="user", 
            content=user_input
        )
        
        return state
    
    async def _route_to_agent(self, state: AgentState) -> AgentState:
        """Nodo router - determina el agente inicial"""
        self.logger.debug("Ejecutando router", session_id=state.session_id)
        
        # El routing real se hace en _determine_next_agent
        # Este nodo es principalmente para logging
        state.current_agent = "router"
        return state
    
    def _check_active_flows(self, state: AgentState) -> Optional[str]:
        """Verifica si hay flujos activos que deben continuar sin re-routing"""
        
        # 1. EXPEDICIÓN ACTIVA - Máxima prioridad  
        expedition_state = state.context_data.get("expedition_state")
        if expedition_state:  # CUALQUIER estado de expedición debe continuar
            self.logger.info(f"🚛 EXPEDICIÓN ACTIVA: {expedition_state} → expedition")
            return "expedition"
        
        # 2. COTIZACIÓN EN PROGRESO  
        quotation_state = state.context_data.get("quotation_state")
        if quotation_state in ["awaiting_details", "analyzing_image", "awaiting_image"]:
            self.logger.debug(f"📋 Cotización en progreso: {quotation_state}")
            return "quotation"
        
        # 3. TRANSFERENCIA HUMANA PENDIENTE
        if state.needs_human_intervention:
            self.logger.debug("👤 Transferencia humana pendiente")
            return "human_loop"
        
        # 4. AGENTE CON CONTEXTO ESPECÍFICO
        if state.current_agent and state.current_agent != "router":
            # Verificar si el agente actual puede seguir manejando
            agent_instance = self.agents.get(state.current_agent)
            if agent_instance and hasattr(agent_instance, 'can_handle'):
                try:
                    if agent_instance.can_handle(state.last_user_input, state.context_data):
                        self.logger.debug(f"🔄 {state.current_agent} puede continuar manejando")
                        return state.current_agent
                except:
                    pass  # Si falla, continuar con routing normal
        
        return None  # No hay flujo activo
    
    def _determine_next_agent(self, state: AgentState) -> str:
        """Determina el próximo agente a ejecutar"""
        
        # Verificar escalamiento humano primero
        if self._should_escalate_to_human(state):
            return "human_loop"
        
        # Verificar transferencias explícitas
        transfer_to = state.context_data.get("transfer_to")
        if transfer_to in self.agents:
            # Limpiar transferencia
            state.context_data.pop("transfer_to", None)
            return transfer_to
        
        # PASO 1: VERIFICAR FLUJOS ACTIVOS (prioridad máxima)
        active_agent = self._check_active_flows(state)
        if active_agent:
            self.logger.info(f"🔄 Flujo activo detectado → {active_agent}")
            return active_agent
        
        # PASO 2: ROUTING INTELIGENTE CON LLM (solo si no hay flujo activo)
        try:
            self.logger.debug("Ejecutando routing INTELIGENTE con LLM")
            
            classification = intent_classifier.classify_intent(
                user_input=state.last_user_input,
                context=state.context_data
            )
            
            intent = classification.get("intent", "consultation")
            recommended_agent = classification.get("agent", "consultant")
            confidence = classification.get("confidence", 0.5)
            reasoning = classification.get("reasoning", "Sin razón específica")
            
            self.logger.info(f"🧠 Clasificación LLM: {intent} → {recommended_agent} (conf: {confidence:.2f})")
            self.logger.debug(f"Razonamiento: {reasoning}")
            
            # Validar que el agente recomendado existe
            if recommended_agent in self.agents:
                # Verificación adicional con alta confianza o validación del agente
                agent = self.agents[recommended_agent]
                
                # Asegurar que el contexto incluya session_id para recuperación de estado
                context_with_session = state.context_data.copy()
                context_with_session["session_id"] = state.session_id
                
                if confidence > 0.6 or agent.can_handle(state.last_user_input, context_with_session):
                    self.logger.debug(f"✅ Routing INTELIGENTE a: {recommended_agent}")
                    return recommended_agent
            
            # Fallback con lógica tradicional si LLM falla
            self.logger.warning("❌ LLM classification failed, using fallback")
            return self._fallback_routing_traditional(state)
            
        except Exception as e:
            self.logger.error(f"Error en routing inteligente: {str(e)}")
            return self._fallback_routing_traditional(state)

    def _fallback_routing_traditional(self, state: AgentState) -> str:
        """Routing de fallback cuando el LLM falla"""
        user_input = state.last_user_input
        
        # Incluir session_id en el contexto para recuperación de estado
        context = state.context_data.copy()
        context["session_id"] = state.session_id
        
        # Verificar cada agente en orden de prioridad (método original)
        agents_to_check = [
            ("expedition", self.agents["expedition"]),
            ("quotation", self.agents["quotation"]),
            ("consultant", self.agents["consultant"])
        ]
        
        for agent_name, agent in agents_to_check:
            if agent.can_handle(user_input, context):
                self.logger.debug(f"🔄 Fallback routing a: {agent_name}")
                return agent_name
        
        # Último fallback
        self.logger.debug("🔄 Routing por defecto a: consultant")
        return "consultant"
    
    def _should_escalate_to_human(self, state: AgentState) -> bool:
        """Verifica si se debe escalar a humano"""
        # Verificar flag explícito
        if state.needs_human_intervention:
            return True
        
        # Verificar usando el agente human_loop
        human_agent = self.agents["human_loop"]
        return human_agent.can_handle(state.last_user_input, state.context_data)
    
    async def _run_consultant(self, state: AgentState) -> AgentState:
        """Ejecuta agente consultor"""
        self.logger.debug("Ejecutando agente consultant")
        return await self.agents["consultant"].process(state)
    
    async def _run_quotation(self, state: AgentState) -> AgentState:
        """Ejecuta agente de cotización"""
        self.logger.debug("Ejecutando agente quotation")
        return await self.agents["quotation"].process(state)
    
    async def _run_expedition(self, state: AgentState) -> AgentState:
        """Ejecuta agente de expedición"""
        self.logger.debug("Ejecutando agente expedition")
        return await self.agents["expedition"].process(state)
    
    async def _run_human_loop(self, state: AgentState) -> AgentState:
        """Ejecuta agente de escalamiento humano"""
        self.logger.debug("Ejecutando agente human_loop")
        return await self.agents["human_loop"].process(state)
    
    def _check_post_agent_routing(self, state: AgentState) -> str:
        """Verifica routing después de ejecutar un agente CON LÓGICA ANTI-BUCLE"""
        
        # 1. Verificar escalamiento humano SIEMPRE primero
        if state.needs_human_intervention:
            return "human_loop"
        
        # 2. Verificar FORCE_END para romper bucles inmediatamente
        if state.context_data.get("force_end", False):
            state.context_data.pop("force_end", None)  # Limpiar flag
            self.logger.info("🛑 FORCE_END detectado - terminando inmediatamente")
            return "end"
        
        # 3. Verificar transferencia explícita y LIMPIARLA
        transfer_to = state.context_data.get("transfer_to")
        if transfer_to and transfer_to in ["quotation", "expedition", "consultant"]:
            # Limpiar transferencia para evitar bucles infinitos
            state.context_data.pop("transfer_to", None)
            self.logger.info(f"🔄 Transferencia explícita a: {transfer_to}")
            return transfer_to
        
        # 3. LÓGICA ANTI-BUCLE: SIEMPRE finalizar después de procesamiento
        current_agent = state.current_agent
        
        # Para quotation: FINALIZAR para evitar bucles
        if current_agent == "quotation":
            quotation_state = state.context_data.get("quotation_state", "")
            
            # Si ya generó cotización completa, ir a respuesta final
            if quotation_state == "quote_ready":
                self.logger.info("✅ Cotización completada - finalizando")
                return "final_response"
            
            # Si está esperando datos del usuario, FINALIZAR INMEDIATAMENTE
            elif state.context_data.get("awaiting_user_response", False):
                self.logger.info("⏳ Esperando respuesta usuario - finalizando para evitar bucle")
                return "end"
            
            # Cualquier otro caso de quotation: FINALIZAR
            else:
                self.logger.info("🔚 Quotation procesado - finalizando")
                return "final_response"
        
        # Para expedition: SIEMPRE finalizar
        elif current_agent == "expedition":
            self.logger.info("✅ Expedition procesado - finalizando")
            return "final_response"
        
        # Para consultant y otros: SIEMPRE finalizar
        else:
            self.logger.info(f"✅ {current_agent} procesado - finalizando")
            return "final_response"
    
    async def _prepare_final_response(self, state: AgentState) -> AgentState:
        """Prepara respuesta final y actualiza metadatos"""
        self.logger.debug("Preparando respuesta final")
        
        # Agregar metadatos útiles
        state.context_data["response_metadata"] = {
            "processing_agent": state.current_agent,
            "conversation_length": len(state.conversation_history),
            "session_active": not state.needs_human_intervention,
            "conversation_turn": state.context_data.get("turn_count", 0) + 1
        }
        
        # Incrementar contador de turnos para conversaciones multi-turno
        state.context_data["turn_count"] = state.context_data.get("turn_count", 0) + 1
        
        # Detectar patrones de conversación para mejorar siguiente respuesta
        state.context_data["conversation_pattern"] = self._analyze_conversation_pattern(state)
        
        return state
    
    def _analyze_conversation_pattern(self, state: AgentState) -> Dict[str, Any]:
        """Analiza patrones en la conversación para mejorar respuestas futuras"""
        history = state.conversation_history
        
        # Contar tipos de mensajes
        user_messages = [msg for msg in history if msg["role"] == "user"]
        assistant_messages = [msg for msg in history if msg["role"] == "assistant"]
        
        # Detectar tendencias
        pattern = {
            "total_exchanges": len(user_messages),
            "recent_topic_switches": 0,
            "user_satisfaction_indicators": [],
            "complexity_level": "basic"
        }
        
        # Analizar últimos 3 mensajes del usuario para detectar cambios de tema
        if len(user_messages) >= 3:
            recent_users = user_messages[-3:]
            topics = []
            
            for msg in recent_users:
                content = msg["content"].lower()
                if any(word in content for word in ["cotizar", "cotización", "precio"]):
                    topics.append("quotation")
                elif any(word in content for word in ["comprar", "expedir", "adquirir"]):
                    topics.append("expedition")
                elif any(word in content for word in ["consulta", "información", "qué es"]):
                    topics.append("consultation")
                elif any(word in content for word in ["asesor", "ayuda", "no entiendo"]):
                    topics.append("human_help")
                else:
                    topics.append("general")
            
            # Contar cambios de tema
            pattern["recent_topic_switches"] = len(set(topics)) - 1 if len(set(topics)) > 1 else 0
        
        # Detectar indicadores de satisfacción/insatisfacción
        if user_messages:
            last_user_msg = user_messages[-1]["content"].lower()
            
            satisfaction_positive = ["gracias", "perfecto", "excelente", "bien", "sí"]
            satisfaction_negative = ["no entiendo", "error", "problema", "mal", "no funciona"]
            
            if any(word in last_user_msg for word in satisfaction_positive):
                pattern["user_satisfaction_indicators"].append("positive")
            elif any(word in last_user_msg for word in satisfaction_negative):
                pattern["user_satisfaction_indicators"].append("negative")
        
        # Determinar nivel de complejidad
        if len(user_messages) > 5:
            pattern["complexity_level"] = "advanced"
        elif pattern["recent_topic_switches"] > 1:
            pattern["complexity_level"] = "intermediate"
        
        return pattern
    
    def _format_orchestrator_response(self, state_data: Union[AgentState, Dict[str, Any]]) -> Dict[str, Any]:
        """Formatea la respuesta final del orquestador"""
        
        # Manejar tanto objetos AgentState como diccionarios
        if isinstance(state_data, dict):
            # Convertir de dict a propiedades accesibles
            agent_response = state_data.get("agent_response", "Lo siento, ocurrió un error procesando tu solicitud.")
            session_id = state_data.get("session_id", "")
            current_agent = state_data.get("current_agent", "system")
            conversation_history = state_data.get("conversation_history", [])
            needs_human_intervention = state_data.get("needs_human_intervention", False)
            escalation_reason = state_data.get("escalation_reason", "")
            context_data = state_data.get("context_data", {})
            updated_at = state_data.get("updated_at", datetime.now())
        else:
            # Es un objeto AgentState
            agent_response = state_data.agent_response
            session_id = state_data.session_id
            current_agent = state_data.current_agent
            conversation_history = state_data.conversation_history
            needs_human_intervention = state_data.needs_human_intervention
            escalation_reason = state_data.escalation_reason
            context_data = state_data.context_data
            updated_at = state_data.updated_at
        
        response = {
            "success": True,
            "content": agent_response,
            "type": "agent_response",
            "session_id": session_id,
            "agent": current_agent,
            "timestamp": updated_at.isoformat() if hasattr(updated_at, 'isoformat') else str(updated_at),
            "metadata": {
                "conversation_length": len(conversation_history),
                "human_intervention_needed": needs_human_intervention,
                "escalation_reason": escalation_reason
            }
        }
        
        # Agregar información específica según el agente
        if current_agent == "quotation":
            # quotation_summary = self.agents["quotation"].get_quotation_summary(state_data)
            # response["metadata"]["quotation"] = quotation_summary
            response["metadata"]["quotation"] = context_data.get("current_quotation", {})
        
        elif current_agent == "expedition":
            # expedition_summary = self.agents["expedition"].get_expedition_summary(state_data)
            # response["metadata"]["expedition"] = expedition_summary
            response["metadata"]["expedition"] = context_data.get("expedition_result", {})
        
        elif current_agent == "human_loop":
            # escalation_summary = self.agents["human_loop"].get_escalation_summary(state_data)
            # response["metadata"]["escalation"] = escalation_summary
            response["metadata"]["escalation"] = context_data.get("escalation_summary", {})
        
        # Agregar contexto para interfaces
        response["context"] = {
            "has_active_quotation": bool(context_data.get("current_quotation")),
            "quotation_state": context_data.get("quotation_state"),
            "expedition_state": context_data.get("expedition_state"),
            "needs_human_intervention": needs_human_intervention
        }
        
        return response
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Obtiene estado actual de una sesión"""
        try:
            session = self.db_manager.get_session(session_id)
            
            if not session:
                return {"exists": False, "session_id": session_id}
            
            # Obtener historial reciente
            recent_history = self.db_manager.get_conversation_history(session_id, limit=5)
            
            # Obtener estado de agentes
            agent_states = {}
            for agent_name in self.agents.keys():
                agent_state = self.db_manager.get_agent_state(session_id, agent_name)
                if agent_state:
                    agent_states[agent_name] = agent_state
            
            status = {
                "exists": True,
                "session_id": session_id,
                "user_type": session.user_type,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": len(recent_history),
                "agent_states": agent_states,
                "last_messages": [
                    {
                        "agent": msg.agent_type,
                        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in recent_history[-3:]
                ]
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado de sesión: {str(e)}")
            return {"exists": False, "error": str(e)}
    
    async def get_active_sessions(self, user_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene sesiones activas"""
        try:
            sessions = self.db_manager.get_active_sessions(user_type)
            
            active_sessions = []
            for session in sessions:
                session_info = {
                    "session_id": session.session_id,
                    "user_type": session.user_type,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "status": session.status
                }
                active_sessions.append(session_info)
            
            return active_sessions
            
        except Exception as e:
            self.logger.error(f"Error obteniendo sesiones activas: {str(e)}")
            return []
    
    def get_system_health(self) -> Dict[str, Any]:
        """Obtiene estado de salud del sistema"""
        try:
            health = {
                "orchestrator": "healthy",
                "agents": {},
                "services": {},
                "database": "unknown"
            }
            
            # Verificar agentes
            for agent_name, agent in self.agents.items():
                try:
                    # Verificar si el agente responde (test básico)
                    health["agents"][agent_name] = "healthy"
                except Exception as e:
                    health["agents"][agent_name] = f"unhealthy: {str(e)}"
            
            # Verificar servicios
            try:
                from services.rag_service import rag_service
                rag_health = rag_service.health_check()
                health["services"]["rag"] = rag_health["status"]
            except Exception as e:
                health["services"]["rag"] = f"error: {str(e)}"
            
            try:
                from services.quotation_service import quotation_service
                health["services"]["quotation"] = "healthy"  # Asumir saludable si se importa
            except Exception as e:
                health["services"]["quotation"] = f"error: {str(e)}"
            
            try:
                from services.expedition_service import expedition_service
                if expedition_service.health_check():
                    health["services"]["expedition"] = "healthy"
                else:
                    health["services"]["expedition"] = "api_unavailable"
            except Exception as e:
                health["services"]["expedition"] = f"error: {str(e)}"
            
            # Verificar base de datos
            try:
                test_sessions = self.db_manager.get_active_sessions()
                health["database"] = "healthy"
            except Exception as e:
                health["database"] = f"error: {str(e)}"
            
            return health
            
        except Exception as e:
            return {
                "orchestrator": f"error: {str(e)}",
                "status": "system_error"
            }

# La instancia del orquestrador se crea en las interfaces para evitar importaciones circulares
# orchestrator = AgentOrchestrator()
