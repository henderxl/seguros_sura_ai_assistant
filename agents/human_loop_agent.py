"""
Agente Human-in-the-Loop - Especializado en detectar y manejar escalamiento a asesores humanos.
Monitorea conversaciones y facilita transferencias cuando es necesario.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent, AgentState, AgentCapabilities
from utils.config import config

class HumanLoopAgent(BaseAgent):
    """Agente especializado en escalamiento a intervención humana"""
    
    def __init__(self):
        super().__init__("human_loop")
        
        # Palabras clave que indican solicitud de humano
        self.human_request_keywords = [
            "persona", "humano", "asesor", "agente", "representante",
            "hablar con alguien", "no entiendo", "esto no funciona",
            "quiero cancelar", "mal servicio", "problema", "error",
            "no me sirve", "necesito ayuda", "confundido"
        ]
        
        # Umbral de tiempo para detectar abandono (en minutos)
        self.ABANDONMENT_THRESHOLD = 10
        
        # Número máximo de intercambios sin progreso
        self.MAX_EXCHANGES_WITHOUT_PROGRESS = 8
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> bool:
        """
        Determina si se necesita intervención humana
        
        Args:
            user_input: Entrada del usuario
            context: Contexto de la conversación
            
        Returns:
            True si se debe activar intervención humana
        """
        # Verificar solicitud explícita
        explicit_request = self._check_explicit_human_request(user_input)
        
        # Verificar patrones de frustración
        frustration_detected = self._detect_frustration_patterns(user_input, context)
        
        # Verificar si ya se marcó para escalamiento
        already_marked = context.get("needs_human_intervention", False)
        
        # Verificar abandono o falta de progreso
        abandonment_detected = self._detect_abandonment_or_stagnation(context)
        
        return explicit_request or frustration_detected or already_marked or abandonment_detected
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Procesa escalamiento a intervención humana
        
        Args:
            state: Estado actual del agente
            
        Returns:
            Estado actualizado con transferencia humana
        """
        try:
            self.logger.info("Procesando escalamiento humano", 
                           reason=state.escalation_reason,
                           session_id=state.session_id)
            
            # Determinar razón del escalamiento
            escalation_reason = self._determine_escalation_reason(state)
            
            # Generar resumen de la conversación
            conversation_summary = self._generate_conversation_summary(state)
            
            # Notificar al asesor (en implementación real, esto podría ser un webhook, email, etc.)
            advisor_notification = self._prepare_advisor_notification(state, escalation_reason, conversation_summary)
            
            # Responder al cliente
            client_response = self._generate_client_response(escalation_reason)
            
            # Actualizar estado
            state.needs_human_intervention = True
            state.escalation_reason = escalation_reason
            state.context_data["human_intervention_activated"] = True
            state.context_data["escalation_timestamp"] = datetime.now().isoformat()
            state.context_data["conversation_summary"] = conversation_summary
            state.context_data["advisor_notification"] = advisor_notification
            
            # Actualizar estado de sesión en BD
            self.db_manager.update_session_status(state.session_id, "transferred")
            
            state = self.update_state(state, agent_response=client_response)
            state = self.add_message_to_history(
                state, "assistant", client_response,
                metadata={"escalation_reason": escalation_reason}
            )
            
            # Agregar mensaje del sistema sobre la transferencia
            system_message = f"Sesión transferida a asesor humano. Razón: {escalation_reason}"
            state = self.add_message_to_history(
                state, "system", system_message,
                metadata={"advisor_notification": advisor_notification}
            )
            
            # Guardar estado del agente
            self.save_agent_state(state, {
                "escalation_executed": True,
                "escalation_reason": escalation_reason,
                "escalation_timestamp": datetime.now().isoformat(),
                "conversation_summary": conversation_summary
            })
            
            self.log_interaction(
                state, state.last_user_input, client_response,
                escalation_reason=escalation_reason,
                conversation_length=len(state.conversation_history)
            )
            
            return state
            
        except Exception as e:
            self.log_error(e, state, {"escalation_reason": state.escalation_reason})
            
            # En caso de error, al menos informar al cliente
            error_response = (
                "He detectado que necesitas asistencia especializada. "
                "Un asesor humano se comunicará contigo pronto. "
                "Disculpa cualquier inconveniente."
            )
            
            state = self.update_state(state, agent_response=error_response)
            state = self.add_message_to_history(state, "assistant", error_response)
            
            return state
    
    def _check_explicit_human_request(self, user_input: str) -> bool:
        """Verifica si el usuario solicita explícitamente hablar con humano"""
        user_input_lower = user_input.lower()
        
        return any(keyword in user_input_lower for keyword in self.human_request_keywords)
    
    def _detect_frustration_patterns(self, user_input: str, context: Dict[str, Any]) -> bool:
        """Detecta patrones de frustración en el usuario"""
        user_input_lower = user_input.lower()
        
        # Palabras de frustración (más restrictivo)
        frustration_words = [
            "frustrado", "molesto", "enojado", "cansado", "harto",
            "perdiendo tiempo", "no entiende nada", "esto no funciona para nada"
        ]
        
        # Signos de urgencia excesiva
        urgency_signs = ["!!!", "???", "AYUDA", "URGENTE", "YA"]
        
        has_frustration = any(word in user_input_lower for word in frustration_words)
        has_urgency = any(sign in user_input.upper() for sign in urgency_signs)
        
        return has_frustration or has_urgency
    
    def _detect_abandonment_or_stagnation(self, context: Dict[str, Any]) -> bool:
        """Detecta abandono o estancamiento en la conversación"""
        conversation_history = context.get("conversation_history", [])
        
        if len(conversation_history) < 12:  # Ser menos agresivo - requerir más intercambios
            return False
        
        # Verificar si hay demasiados intercambios sin progreso aparente
        recent_messages = conversation_history[-self.MAX_EXCHANGES_WITHOUT_PROGRESS:]
        user_messages = [msg for msg in recent_messages if msg.get("role") == "user"]
        
        # Si hay muchas preguntas del usuario sin resolución
        if len(user_messages) >= 4:
            # Verificar si las preguntas son similares (indicativo de no comprensión)
            questions = [msg.get("content", "").lower() for msg in user_messages]
            similar_questions = 0
            
            for i, q1 in enumerate(questions):
                for q2 in questions[i+1:]:
                    if self._are_similar_questions(q1, q2):
                        similar_questions += 1
            
            if similar_questions >= 2:
                return True
        
        # Verificar tiempo desde última interacción (para detectar abandono)
        if conversation_history:
            last_message = conversation_history[-1]
            last_timestamp = last_message.get("timestamp")
            
            if last_timestamp:
                try:
                    last_time = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                    time_diff = datetime.now() - last_time.replace(tzinfo=None)
                    
                    if time_diff > timedelta(minutes=self.ABANDONMENT_THRESHOLD):
                        return True
                except:
                    pass
        
        return False
    
    def _are_similar_questions(self, q1: str, q2: str) -> bool:
        """Verifica si dos preguntas son similares"""
        if not q1 or not q2:
            return False
        
        # Contar palabras comunes (simple similaridad)
        words1 = set(q1.split())
        words2 = set(q2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity > 0.6
    
    def _determine_escalation_reason(self, state: AgentState) -> str:
        """Determina la razón específica del escalamiento"""
        if state.escalation_reason:
            return state.escalation_reason
        
        user_input_lower = state.last_user_input.lower()
        
        # Categorizar razón basada en entrada del usuario
        if any(word in user_input_lower for word in ["persona", "humano", "asesor"]):
            return "Solicitud explícita de asesor humano"
        
        elif any(word in user_input_lower for word in ["no entiendo", "confundido", "no comprendo"]):
            return "Usuario necesita clarificación adicional"
        
        elif any(word in user_input_lower for word in ["problema", "error", "no funciona"]):
            return "Problema técnico o funcional reportado"
        
        elif any(word in user_input_lower for word in ["cancelar", "no quiero", "cambiar opinion"]):
            return "Usuario quiere cancelar o cambiar decisión"
        
        elif len(state.conversation_history) > self.MAX_EXCHANGES_WITHOUT_PROGRESS:
            return "Conversación prolongada sin resolución"
        
        else:
            return "Escalamiento automático por patrones detectados"
    
    def _generate_conversation_summary(self, state: AgentState) -> Dict[str, Any]:
        """Genera resumen detallado de la conversación para el asesor"""
        summary = {
            "session_id": state.session_id,
            "user_type": state.user_type,
            "conversation_start": state.created_at.isoformat() if state.created_at else None,
            "escalation_time": datetime.now().isoformat(),
            "total_messages": len(state.conversation_history),
            "agents_involved": list(set(msg.get("agent", "unknown") for msg in state.conversation_history if msg.get("agent"))),
            "conversation_flow": self._extract_conversation_flow(state),
            "current_context": self._extract_current_context(state),
            "user_intent": self._infer_user_intent(state),
            "pending_actions": self._identify_pending_actions(state)
        }
        
        return summary
    
    def _extract_conversation_flow(self, state: AgentState) -> List[Dict[str, Any]]:
        """Extrae flujo resumido de la conversación"""
        flow = []
        
        for msg in state.conversation_history[-10:]:  # Últimos 10 mensajes
            if msg.get("role") in ["user", "assistant"]:
                flow.append({
                    "role": msg.get("role"),
                    "agent": msg.get("agent", "unknown"),
                    "content_preview": msg.get("content", "")[:100] + "..." if len(msg.get("content", "")) > 100 else msg.get("content", ""),
                    "timestamp": msg.get("timestamp")
                })
        
        return flow
    
    def _extract_current_context(self, state: AgentState) -> Dict[str, Any]:
        """Extrae contexto actual relevante"""
        context = {}
        
        # Información de cotización si existe
        if state.context_data.get("current_quotation"):
            quotation = state.context_data["current_quotation"]
            context["quotation"] = {
                "vehicle": quotation.get("vehicle_info", {}),
                "plans_available": list(quotation.get("quotations", {}).keys()),
                "quotation_id": state.context_data.get("quotation_id")
            }
        
        # Información de expedición si existe
        if state.context_data.get("expedition_state"):
            context["expedition"] = {
                "state": state.context_data["expedition_state"],
                "selected_plan": state.context_data.get("selected_plan"),
                "client_data_collected": bool(state.context_data.get("client_data"))
            }
        
        # Estado de agentes
        context["agent_states"] = {
            "current_agent": state.current_agent,
            "quotation_state": state.context_data.get("quotation_state"),
            "expedition_state": state.context_data.get("expedition_state")
        }
        
        return context
    
    def _infer_user_intent(self, state: AgentState) -> str:
        """Infiere la intención principal del usuario"""
        context = state.context_data
        
        if context.get("current_quotation") and context.get("expedition_state"):
            return "Expedición de póliza en proceso"
        elif context.get("current_quotation"):
            return "Cotización generada, evaluando opciones"
        elif context.get("quotation_state"):
            return "Proceso de cotización en curso"
        elif any("consulta" in msg.get("agent", "") for msg in state.conversation_history[-5:]):
            return "Consultas generales sobre seguros"
        else:
            return "Intención no clara, requiere clarificación"
    
    def _identify_pending_actions(self, state: AgentState) -> List[str]:
        """Identifica acciones pendientes que el asesor debe completar"""
        pending = []
        
        context = state.context_data
        
        # Verificar expedición pendiente
        if context.get("expedition_state") == "confirming_purchase":
            pending.append("Confirmar y completar expedición de póliza")
        
        # Verificar cotización incompleta
        if context.get("quotation_state") in ["awaiting_details", "awaiting_image"]:
            pending.append("Completar información para cotización")
        
        # Verificar si hay preguntas sin responder
        recent_user_messages = [
            msg for msg in state.conversation_history[-3:] 
            if msg.get("role") == "user"
        ]
        
        if recent_user_messages:
            last_user_msg = recent_user_messages[-1].get("content", "")
            if "?" in last_user_msg:
                pending.append("Responder pregunta específica del cliente")
        
        if not pending:
            pending.append("Retomar conversación desde el punto de escalamiento")
        
        return pending
    
    def _prepare_advisor_notification(self, state: AgentState, reason: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara notificación para el asesor humano"""
        notification = {
            "priority": self._determine_priority(reason, summary),
            "session_id": state.session_id,
            "escalation_reason": reason,
            "client_waiting": True,
            "estimated_complexity": self._estimate_complexity(summary),
            "recommended_actions": summary.get("pending_actions", []),
            "conversation_summary": summary,
            "quick_context": self._generate_quick_context(summary),
            "timestamp": datetime.now().isoformat()
        }
        
        return notification
    
    def _determine_priority(self, reason: str, summary: Dict[str, Any]) -> str:
        """Determina prioridad del caso"""
        high_priority_reasons = [
            "problema técnico", "error", "expedición fallida",
            "cliente molesto", "cancelar"
        ]
        
        if any(keyword in reason.lower() for keyword in high_priority_reasons):
            return "HIGH"
        
        # Si hay expedición en proceso
        if "expedición" in summary.get("user_intent", "").lower():
            return "MEDIUM"
        
        return "LOW"
    
    def _estimate_complexity(self, summary: Dict[str, Any]) -> str:
        """Estima complejidad del caso"""
        agents_count = len(summary.get("agents_involved", []))
        pending_count = len(summary.get("pending_actions", []))
        
        if agents_count >= 3 or pending_count >= 3:
            return "HIGH"
        elif agents_count >= 2 or pending_count >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_quick_context(self, summary: Dict[str, Any]) -> str:
        """Genera contexto rápido para el asesor"""
        intent = summary.get("user_intent", "Consulta general")
        agents = ", ".join(summary.get("agents_involved", []))
        
        context_parts = [f"Intención: {intent}"]
        
        if summary.get("current_context", {}).get("quotation"):
            vehicle = summary["current_context"]["quotation"]["vehicle"]
            context_parts.append(f"Vehículo: {vehicle.get('marca', '')} {vehicle.get('modelo', '')}")
        
        if summary.get("pending_actions"):
            context_parts.append(f"Pendiente: {summary['pending_actions'][0]}")
        
        return " | ".join(context_parts)
    
    def _generate_client_response(self, escalation_reason: str) -> str:
        """Genera respuesta apropiada para el cliente"""
        base_message = (
            "He detectado que necesitas asistencia especializada. "
            "Te estoy conectando con uno de nuestros asesores humanos "
            "que podrá ayudarte de manera personalizada."
        )
        
        # Personalizar mensaje según la razón
        if "solicitud explícita" in escalation_reason.lower():
            additional_msg = "\n\nComo solicitaste, te conecto directamente con un asesor."
        
        elif "problema técnico" in escalation_reason.lower():
            additional_msg = "\n\nNuestro asesor podrá resolver el problema técnico que experimentas."
        
        elif "expedición" in escalation_reason.lower():
            additional_msg = "\n\nEl asesor completará el proceso de expedición de tu póliza."
        
        elif "clarificación" in escalation_reason.lower():
            additional_msg = "\n\nNuestro asesor te dará toda la información detallada que necesitas."
        
        else:
            additional_msg = "\n\nEn breve recibirás atención personalizada."
        
        closing = (
            "\n\nGracias por tu paciencia. Un asesor se comunicará contigo "
            "en los próximos minutos para continuar con tu consulta."
        )
        
        return base_message + additional_msg + closing
    
    def get_escalation_summary(self, state: AgentState) -> Dict[str, Any]:
        """Genera resumen del escalamiento ejecutado"""
        agent_state = self.load_agent_state(state.session_id) or {}
        
        return {
            "escalation_executed": agent_state.get("escalation_executed", False),
            "escalation_reason": agent_state.get("escalation_reason"),
            "escalation_timestamp": agent_state.get("escalation_timestamp"),
            "conversation_summary_available": bool(agent_state.get("conversation_summary"))
        }
