"""
Agente de Expedición - Especializado en la emisión de pólizas.
Maneja recolección de datos del cliente y expedición usando la API existente.
"""

import re
from typing import Dict, Any, List, Optional

from agents.base_agent import BaseAgent, AgentState, AgentCapabilities
from services.expedition_service import expedition_service
from utils.config import config

class ExpeditionAgent(BaseAgent):
    """Agente especializado en expedición de pólizas"""
    
    def __init__(self):
        super().__init__("expedition")
        self.expedition_service = expedition_service
        
        # Palabras clave que indican solicitudes de expedición
        self.expedition_keywords = [
            "comprar", "adquirir", "expedir", "emitir", "contratar",
            "quiero la póliza", "proceder", "acepto", "confirmo",
            "datos personales", "cédula", "teléfono"
        ]
        
        # Estados del proceso de expedición
        self.STATES = {
            "NEEDS_QUOTATION": "needs_quotation",  # Nuevo estado
            "REQUESTING_CLIENT_DATA": "requesting_client_data",
            "VALIDATING_DATA": "validating_data",
            "CONFIRMING_PURCHASE": "confirming_purchase",
            "PROCESSING_EXPEDITION": "processing_expedition",
            "EXPEDITION_COMPLETED": "expedition_completed"
        }
        
        # Campos requeridos del cliente
        self.REQUIRED_FIELDS = [
            "identificacion_tomador",
            "celular_tomador", 
            "email_tomador"
        ]
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> bool:
        """
        Determina si puede manejar solicitudes de expedición
        
        Args:
            user_input: Entrada del usuario
            context: Contexto de la conversación
            
        Returns:
            True si es una solicitud de expedición
        """
        user_input_lower = user_input.lower()
        
        # Verificar palabras clave de expedición
        has_expedition_keywords = any(
            keyword in user_input_lower 
            for keyword in self.expedition_keywords
        )
        
        # Verificar si fue transferido desde cotización
        is_transfer_from_quotation = context.get("transfer_to") == "expedition"
        
        # Verificar si ya está en proceso de expedición
        is_in_expedition_process = context.get("expedition_state") in self.STATES.values()
        
        # Verificar si hay cotización lista para expedir
        has_quotation = bool(context.get("current_quotation"))
        
        return has_expedition_keywords or is_transfer_from_quotation or is_in_expedition_process
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Procesa solicitudes de expedición
        
        Args:
            state: Estado actual del agente
            
        Returns:
            Estado actualizado con respuesta
        """
        try:
            # Obtener estado específico de expedición
            expedition_state = state.context_data.get("expedition_state", "")
            
            self.logger.info("Procesando expedición", 
                           expedition_state=expedition_state)
            
            # Verificar que hay cotización disponible
            current_quotation = state.context_data.get("current_quotation")
            expedition_ready = state.context_data.get("expedition_ready", False)
            
            # MANEJAR ESTADO NEEDS_QUOTATION
            if expedition_state == self.STATES["NEEDS_QUOTATION"]:
                # ANTI-BUCLE: Verificar intentos previos
                transfer_attempts = state.context_data.get("transfer_attempts", 0)
                if transfer_attempts >= 3:
                    self.logger.error("🚫 Máximo de transferencias alcanzado, escalando a humano")
                    state.needs_human_intervention = True
                    state.escalation_reason = "No se pudo recuperar cotización después de múltiples intentos"
                    return state
                
                # Esperando que regresen de quotation con cotización
                if current_quotation:
                    # Ya hay cotización en memoria, proceder
                    return await self._start_expedition_process(state)
                elif expedition_ready:
                    # Recuperar cotización de BD primero
                    self.logger.info(f"🔍 expedition_ready=True, recuperando cotización de BD para session_id: {state.session_id}")
                    
                    try:
                        with self.db_manager.get_connection() as conn:
                            count_row = conn.execute("""
                                SELECT COUNT(*) as count FROM quotations WHERE session_id = ?
                            """, (state.session_id,)).fetchone()
                            self.logger.info(f"🔍 Cotizaciones encontradas: {count_row['count'] if count_row else 0}")
                            
                            row = conn.execute("""
                                SELECT vehicle_data, quotation_result 
                                FROM quotations 
                                WHERE session_id = ? 
                                ORDER BY created_at DESC 
                                LIMIT 1
                            """, (state.session_id,)).fetchone()
                            
                            if row:
                                import json
                                vehicle_data = json.loads(row['vehicle_data'])
                                quotation_result = json.loads(row['quotation_result'])
                                
                                current_quotation = {
                                    "quotations": quotation_result.get("quotations", {}),
                                    "vehicle_details": vehicle_data
                                }
                                state.context_data["current_quotation"] = current_quotation
                                state.context_data.pop("expedition_ready", None)
                                self.logger.info("✅ Cotización recuperada de BD para expedición")
                                
                                # Ahora proceder con expedición
                                return await self._start_expedition_process(state)
                            else:
                                raise Exception("No se encontró cotización en BD")
                                
                    except Exception as e:
                        self.logger.warning(f"No se pudo recuperar cotización: {e}")
                        # Incrementar contador de intentos
                        state.context_data["transfer_attempts"] = transfer_attempts + 1
                        return await self._no_quotation_available(state)
                else:
                    # Incrementar contador de intentos
                    state.context_data["transfer_attempts"] = transfer_attempts + 1
                    # Aún no hay cotización, re-transferir
                    return await self._no_quotation_available(state)
            
            # Cualquier otro caso - proceder normalmente
            
            # Procesar según el estado actual
            if not expedition_state or expedition_state == "":
                # Iniciar proceso de expedición
                return await self._start_expedition_process(state)
            
            elif expedition_state == self.STATES["REQUESTING_CLIENT_DATA"]:
                # Procesar datos del cliente proporcionados
                return await self._process_client_data(state)
            
            elif expedition_state == self.STATES["CONFIRMING_PURCHASE"]:
                # Procesar confirmación de compra
                return await self._process_purchase_confirmation(state)
            
            elif expedition_state == self.STATES["EXPEDITION_COMPLETED"]:
                # Manejar interacciones post-expedición
                return await self._handle_post_expedition(state)
            
            else:
                # Estado desconocido, reiniciar proceso
                return await self._start_expedition_process(state)
        
        except Exception as e:
            self.log_error(e, state, {
                "expedition_state": expedition_state,
                "has_quotation": bool(current_quotation)
            })
            
            error_response = (
                "Disculpa, tuve un problema procesando tu solicitud de expedición. "
                "Por favor intenta nuevamente o te conecto con un asesor humano."
            )
            
            state = self.update_state(state, agent_response=error_response)
            state = self.add_message_to_history(state, "assistant", error_response)
            
            # Marcar para escalamiento en caso de error
            state.needs_human_intervention = True
            state.escalation_reason = "Error técnico en proceso de expedición"
            
            return state
    
    async def _start_expedition_process(self, state: AgentState) -> AgentState:
        """Inicia el proceso de expedición"""
        current_quotation = state.context_data.get("current_quotation")
        
        # VALIDACIÓN CRÍTICA: Verificar que current_quotation existe
        if not current_quotation or not current_quotation.get("quotations"):
            self.logger.error("❌ No se encontró cotización válida para iniciar expedición")
            return await self._no_quotation_available(state)
        
        plans = list(current_quotation["quotations"].keys())
        
        # Si hay múltiples planes, solicitar selección
        if len(plans) > 1:
            response = self._request_plan_selection(current_quotation)
            # Cambiar estado para procesar selección de plan
            state.context_data["expedition_state"] = self.STATES["REQUESTING_CLIENT_DATA"]
            
            # Persistir estado de selección de plan
            self.save_agent_state(state, {
                "expedition_state": self.STATES["REQUESTING_CLIENT_DATA"],
                "awaiting_plan_selection": True,
                "quotation_available": True
            })
        else:
            # Un solo plan, proceder con datos del cliente
            selected_plan = plans[0]
            state.context_data["selected_plan"] = selected_plan
            response = self._request_client_data(selected_plan, current_quotation)
            state.context_data["expedition_state"] = self.STATES["REQUESTING_CLIENT_DATA"]
            
            # Persistir estado solo cuando hay plan seleccionado
            self.save_agent_state(state, {
                "expedition_state": self.STATES["REQUESTING_CLIENT_DATA"],
                "selected_plan": selected_plan,
                "quotation_available": True
            })
        
        state = self.update_state(state, agent_response=response["content"])
        state = self.add_message_to_history(
            state, "assistant", response["content"],
            metadata=response.get("metadata", {})
        )
        
        return state
    
    async def _process_client_data(self, state: AgentState) -> AgentState:
        """Procesa datos del cliente proporcionados"""
        user_input = state.last_user_input
        
        # Verificar si el usuario está seleccionando plan primero
        selected_plan = state.context_data.get("selected_plan")
        self.logger.info(f"🔍 _process_client_data: selected_plan={selected_plan}, user_input='{user_input}'")
        
        if not selected_plan:
            current_quotation = state.context_data.get("current_quotation", {})
            self.logger.info(f"🔍 current_quotation disponible: {bool(current_quotation)}")
            self.logger.info(f"🔍 quotations en current_quotation: {list(current_quotation.get('quotations', {}).keys())}")
            
            # SI NO HAY COTIZACIÓN EN CONTEXT, RECUPERAR DE BD
            if not current_quotation or not current_quotation.get("quotations"):
                self.logger.info("🔍 Recuperando cotización desde BD...")
                try:
                    with self.db_manager.get_connection() as conn:
                        row = conn.execute("""
                            SELECT vehicle_data, quotation_result 
                            FROM quotations 
                            WHERE session_id = ? 
                            ORDER BY created_at DESC 
                            LIMIT 1
                        """, (state.session_id,)).fetchone()
                        
                        if row:
                            import json
                            vehicle_data = json.loads(row['vehicle_data'])
                            quotation_result = json.loads(row['quotation_result'])
                            
                            current_quotation = {
                                "quotations": quotation_result.get("quotations", {}),
                                "vehicle_details": vehicle_data
                            }
                            state.context_data["current_quotation"] = current_quotation
                            self.logger.info(f"✅ Cotización recuperada: {list(current_quotation['quotations'].keys())}")
                        else:
                            self.logger.error("❌ No se encontró cotización en BD")
                except Exception as e:
                    self.logger.error(f"❌ Error recuperando cotización: {e}")
            
            plan_selection = self._parse_plan_selection(user_input, current_quotation)
            self.logger.info(f"🔍 Plan selection result: {plan_selection}")
            if plan_selection:
                state.context_data["selected_plan"] = plan_selection
                response = self._request_client_data(plan_selection, current_quotation)
                state.context_data["expedition_state"] = self.STATES["REQUESTING_CLIENT_DATA"]
                
                # Persistir estado cuando se selecciona plan
                self.save_agent_state(state, {
                    "expedition_state": self.STATES["REQUESTING_CLIENT_DATA"],
                    "selected_plan": plan_selection,
                    "quotation_available": True
                })
                
                state = self.update_state(state, agent_response=response["content"])
                state = self.add_message_to_history(state, "assistant", response["content"])
                return state
        
        # Parsear datos del cliente y combinar con datos parciales
        client_data = self._parse_client_data(user_input)
        
        # ACUMULACIÓN CRÍTICA: Combinar con datos parciales existentes
        partial_data = state.context_data.get("partial_client_data", {})
        combined_data = partial_data.copy()
        combined_data.update(client_data)
        client_data = combined_data
        
        # GUARDAR PROGRESO SIEMPRE
        state.context_data["partial_client_data"] = client_data
        self.logger.info(f"🔍 Datos acumulados: {client_data}")
        
        # Validar y solicitar datos faltantes progresivamente
        required_fields = ["identificacion_tomador", "celular_tomador", "email_tomador"]
        
        # Verificar qué datos faltan
        missing_fields = []
        for field in required_fields:
            if field not in client_data or not client_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            # PEDIR TODOS LOS DATOS FALTANTES EN UN SOLO MENSAJE
            response = self._request_comprehensive_data(missing_fields, client_data)
            state = self.update_state(state, agent_response=response["content"])
            state = self.add_message_to_history(state, "assistant", response["content"])
            
            # Guardar datos parciales
            state.context_data["partial_client_data"] = client_data
            self.logger.info(f"📝 Guardando datos parciales: {client_data}")
            
            return state
        
        # Todos los datos están completos, validar formatos
        validation_errors = self.expedition_service.validate_client_data(client_data)
        
        if validation_errors:
            # Solicitar corrección de datos
            response = self._request_data_correction(validation_errors, client_data)
            state = self.update_state(state, agent_response=response["content"])
            state = self.add_message_to_history(state, "assistant", response["content"])
            return state
        
        # VERIFICAR QUE TENEMOS PLAN SELECCIONADO
        selected_plan = state.context_data.get("selected_plan")
        if not selected_plan:
            self.logger.error("❌ No hay plan seleccionado para confirmación")
            # Escalar a humano
            state.needs_human_intervention = True
            state.escalation_reason = "Error técnico: plan no seleccionado"
            return state
        
        # ASEGURAR QUE COTIZACIÓN ESTÉ DISPONIBLE ANTES DE CONFIRMACIÓN
        current_quotation = state.context_data.get("current_quotation")
        if not current_quotation:
            # Recuperar cotización de BD si no está en contexto
            try:
                with self.db_manager.get_connection() as conn:
                    row = conn.execute("""
                        SELECT vehicle_data, quotation_result 
                        FROM quotations 
                        WHERE session_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (state.session_id,)).fetchone()
                    
                    if row:
                        import json
                        vehicle_data = json.loads(row['vehicle_data'])
                        quotation_result = json.loads(row['quotation_result'])
                        
                        current_quotation = {
                            "quotations": quotation_result.get("quotations", {}),
                            "vehicle_details": vehicle_data
                        }
                        state.context_data["current_quotation"] = current_quotation
                        self.logger.info("✅ Cotización recuperada para confirmación")
                    else:
                        self.logger.error("❌ No se encontró cotización para confirmación")
                        state.needs_human_intervention = True
                        state.escalation_reason = "No se encontró cotización para confirmación"
                        return state
            except Exception as e:
                self.logger.error(f"❌ Error recuperando cotización para confirmación: {e}")
                state.needs_human_intervention = True
                state.escalation_reason = "Error técnico recuperando cotización"
                return state
        
        # Datos válidos, solicitar confirmación
        state.context_data["client_data"] = client_data
        response = self._request_purchase_confirmation(client_data, state.context_data)
        state.context_data["expedition_state"] = self.STATES["CONFIRMING_PURCHASE"]
        
        # PERSISTIR DATOS DEL CLIENTE EN BD
        self.save_agent_state(state, {
            "expedition_state": self.STATES["CONFIRMING_PURCHASE"],
            "client_data": client_data,
            "selected_plan": state.context_data.get("selected_plan"),
            "quotation_available": True
        })
        
        state = self.update_state(state, agent_response=response["content"])
        state = self.add_message_to_history(state, "assistant", response["content"])
        
        return state
    
    async def _process_purchase_confirmation(self, state: AgentState) -> AgentState:
        """Procesa confirmación de compra"""
        user_input_lower = state.last_user_input.lower()
        
        # Verificar confirmación (MÁS FLEXIBLE)
        confirmation_words = ["sí", "si", "confirmo", "acepto", "correcto", "proceder", "continuar", "ok", "vale"]
        cancellation_words = ["no", "cancelar", "cambiar", "modificar", "negar"]
        
        # También aceptar respuestas numéricas o cortas como confirmación
        if user_input_lower.strip() in ["1", "si", "s", "y", "yes", "ok"]:
            return await self._execute_expedition(state)
        
        if any(word in user_input_lower for word in confirmation_words):
            # Proceder con expedición
            return await self._execute_expedition(state)
        
        elif any(word in user_input_lower for word in cancellation_words):
            # Cancelar o modificar
            response = (
                "Entiendo que quieres hacer cambios. ¿Qué te gustaría modificar?\n"
                "• Datos personales\n"
                "• Plan seleccionado\n"
                "• Cancelar completamente\n\n"
                "O puedes solicitar hablar con un asesor humano."
            )
            
            # Volver a solicitar datos
            state.context_data["expedition_state"] = self.STATES["REQUESTING_CLIENT_DATA"]
        
        else:
            # Solicitar confirmación más clara
            response = (
                "Por favor confirma si deseas proceder con la expedición escribiendo 'Sí, confirmo' "
                "o 'No, quiero hacer cambios'."
            )
        
        state = self.update_state(state, agent_response=response)
        state = self.add_message_to_history(state, "assistant", response)
        
        return state
    
    async def _execute_expedition(self, state: AgentState) -> AgentState:
        """Ejecuta la expedición de la póliza"""
        try:
            self.logger.info("Ejecutando expedición de póliza")
            
            state.context_data["expedition_state"] = self.STATES["PROCESSING_EXPEDITION"]
            
            # Preparar payload para expedición
            client_data = state.context_data.get("client_data")
            if not client_data:
                # RECUPERAR DATOS DEL CLIENTE DESDE BD
                self.logger.info("🔍 Recuperando datos del cliente para ejecución...")
                try:
                    agent_state = self.db_manager.get_agent_state(state.session_id, "expedition")
                    if agent_state and agent_state.get("client_data"):
                        client_data = agent_state["client_data"]
                        state.context_data["client_data"] = client_data
                        self.logger.info("✅ Datos del cliente recuperados para ejecución")
                    else:
                        self.logger.error("❌ No se encontraron datos del cliente en BD")
                        state.needs_human_intervention = True
                        state.escalation_reason = "Error técnico: datos del cliente no disponibles"
                        return state
                except Exception as e:
                    self.logger.error(f"❌ Error recuperando datos del cliente: {e}")
                    state.needs_human_intervention = True
                    state.escalation_reason = "Error técnico: datos del cliente no disponibles"
                    return state
            current_quotation = state.context_data.get("current_quotation", {})
            if not current_quotation:
                # RECUPERAR COTIZACIÓN DE BD TAMBIÉN AQUÍ
                self.logger.info("🔍 Recuperando cotización para ejecución...")
                try:
                    with self.db_manager.get_connection() as conn:
                        row = conn.execute("""
                            SELECT vehicle_data, quotation_result 
                            FROM quotations 
                            WHERE session_id = ? 
                            ORDER BY created_at DESC 
                            LIMIT 1
                        """, (state.session_id,)).fetchone()
                        
                        if row:
                            import json
                            vehicle_data = json.loads(row['vehicle_data'])
                            quotation_result = json.loads(row['quotation_result'])
                            
                            current_quotation = {
                                "quotations": quotation_result.get("quotations", {}),
                                "vehicle_details": vehicle_data
                            }
                            state.context_data["current_quotation"] = current_quotation
                            self.logger.info("✅ Cotización recuperada para ejecución")
                        else:
                            self.logger.error("❌ No se encontró cotización en BD para ejecución")
                            state.needs_human_intervention = True
                            state.escalation_reason = "Error técnico: cotización no disponible"
                            return state
                except Exception as e:
                    self.logger.error(f"❌ Error recuperando cotización para ejecución: {e}")
                    state.needs_human_intervention = True
                    state.escalation_reason = "Error técnico: cotización no disponible"
                    return state
            
            vehicle_data = current_quotation.get("vehicle_details", current_quotation.get("vehicle_info", {}))
            quotation_data = current_quotation
            selected_plan = state.context_data.get("selected_plan")
            if not selected_plan:
                self.logger.error("❌ No hay plan seleccionado para ejecutar expedición")
                return await self._start_expedition_process(state)
            
            expedition_payload = self.expedition_service.prepare_expedition_payload(
                client_data=client_data,
                vehicle_data=vehicle_data,
                quotation_data=quotation_data,
                selected_plan=selected_plan
            )
            
            # Ejecutar expedición
            expedition_result = self.expedition_service.expedite_policy(expedition_payload)
            
            if expedition_result["success"]:
                # Expedición exitosa
                response = self._format_success_response(expedition_result, selected_plan)
                
                # Persistir póliza en BD
                self.db_manager.save_policy(
                    policy_number=expedition_result["numero_poliza"],
                    session_id=state.session_id,
                    quotation_id=state.context_data.get("quotation_id"),
                    client_data=client_data,
                    policy_data=expedition_result
                )
                
                state.context_data["expedition_result"] = expedition_result
                state.context_data["expedition_state"] = self.STATES["EXPEDITION_COMPLETED"]
                
            else:
                # Error en expedición
                response = self._format_error_response(expedition_result)
                
                # Marcar para escalamiento
                state.needs_human_intervention = True
                state.escalation_reason = f"Error en expedición: {expedition_result.get('error', 'Error desconocido')}"
            
            # Guardar estado del agente
            self.save_agent_state(state, {
                "expedition_executed": True,
                "success": expedition_result["success"],
                "policy_number": expedition_result.get("numero_poliza"),
                "client_data": client_data,
                "selected_plan": selected_plan
            })
            
            self.log_interaction(
                state, expedition_payload, expedition_result,
                policy_number=expedition_result.get("numero_poliza"),
                success=expedition_result["success"]
            )
            
            state = self.update_state(state, agent_response=response["content"])
            state = self.add_message_to_history(
                state, "assistant", response["content"],
                metadata=response.get("metadata", {})
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error ejecutando expedición: {str(e)}")
            
            error_response = (
                "Lo siento, ocurrió un error durante la expedición de tu póliza. "
                "Te voy a conectar con un asesor humano para que pueda asistirte "
                "completando el proceso manualmente."
            )
            
            state = self.update_state(state, agent_response=error_response)
            state = self.add_message_to_history(state, "assistant", error_response)
            
            # Marcar para escalamiento
            state.needs_human_intervention = True
            state.escalation_reason = f"Error técnico en expedición: {str(e)}"
            
            return state
    
    async def _handle_post_expedition(self, state: AgentState) -> AgentState:
        """Maneja interacciones después de expedición exitosa"""
        expedition_result = state.context_data.get("expedition_result", {})
        policy_number = expedition_result.get("numero_poliza")
        
        user_input_lower = state.last_user_input.lower()
        
        if any(word in user_input_lower for word in ["consultar", "estado", "información", "detalles"]):
            response = self._provide_policy_details(expedition_result, state.context_data)
        
        elif any(word in user_input_lower for word in ["problema", "error", "asesor", "ayuda"]):
            response = "Te conecto con un asesor humano para que pueda ayudarte con cualquier consulta sobre tu póliza."
            state.needs_human_intervention = True
            state.escalation_reason = "Cliente solicita ayuda post-expedición"
        
        else:
            response = (
                f"Tu póliza {policy_number} ha sido expedida exitosamente. "
                "¿Hay algo más en lo que pueda ayudarte? Puedo:\n"
                "• Darte detalles sobre tu póliza\n"
                "• Ayudarte con otra cotización\n" 
                "• Conectarte con un asesor para consultas específicas"
            )
        
        state = self.update_state(state, agent_response=response)
        state = self.add_message_to_history(state, "assistant", response)
        
        return state
    
    async def _no_quotation_available(self, state: AgentState) -> AgentState:
        """Maneja caso cuando no hay cotización disponible"""
        response = (
            "Para proceder con la expedición de una póliza, primero necesito "
            "generar una cotización. ¿Te gustaría que te ayude a cotizar tu seguro de autos?"
        )
        
        # PRESERVAR estado de expedición - solo marcar transferencia
        state.context_data["expedition_state"] = self.STATES["NEEDS_QUOTATION"] 
        state.context_data["transfer_to"] = "quotation"
        state.context_data["previous_agent"] = "expedition"  # ANTI-BUCLE
        
        # Persistir estado para recuperación posterior
        self.save_agent_state(state, {
            "expedition_state": self.STATES["NEEDS_QUOTATION"],
            "quotation_available": False
        })
        
        state = self.update_state(state, agent_response=response)
        state = self.add_message_to_history(state, "assistant", response)
        
        return state
    
    def _parse_client_data(self, user_input: str) -> Dict[str, str]:
        """
        PARSING INTELIGENTE CON LLM - Captura TODOS los datos de una vez
        """
        self.logger.info(f"🔍 PARSING INTELIGENTE: '{user_input}'")
        
        # PASO 1: LLM PARSING COMPLETO (prioridad máxima)
        try:
            llm_data = self._extract_all_client_data_with_llm(user_input)
            if llm_data:
                self.logger.info(f"🧠 LLM extrajo: {llm_data}")
                return llm_data
        except Exception as e:
            self.logger.warning(f"⚠️ LLM parsing falló: {e}")
        
        # PASO 2: REGEX MULTIPLES (respaldo)
        client_data = {}
        
        # EMAIL (más específico)
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_input)
        if email_match:
            client_data["email_tomador"] = email_match.group(1)
            self.logger.info(f"✅ Email: {email_match.group(1)}")
        
        # TELÉFONO (10 dígitos, empieza con 3)
        phone_matches = re.findall(r'\b(3\d{9})\b', user_input)
        if phone_matches:
            client_data["celular_tomador"] = phone_matches[0]
            self.logger.info(f"✅ Teléfono: {phone_matches[0]}")
        
        # CÉDULA (6-11 dígitos, NO empieza con 3)
        cedula_matches = re.findall(r'\b(\d{6,11})\b', user_input)
        for cedula in cedula_matches:
            if not cedula.startswith('3'):  # No es teléfono
                client_data["identificacion_tomador"] = cedula
                self.logger.info(f"✅ Cédula: {cedula}")
                break
        
        # NOMBRE (letras y espacios, mínimo 2 palabras)
        name_match = re.search(r'\b([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)+)\b', user_input)
        if name_match:
            client_data["nombre_tomador"] = name_match.group(1).strip()
            self.logger.info(f"✅ Nombre: {name_match.group(1)}")
        
        return client_data
    
    def _extract_all_client_data_with_llm(self, user_input: str) -> Dict[str, str]:
        """
        EXTRACCIÓN COMPLETA CON LLM - Sin bucles infinitos
        """
        try:
            from openai import AzureOpenAI
            
            client = AzureOpenAI(
                api_key=config.azure_openai.api_key,
                api_version=config.azure_openai.api_version,
                azure_endpoint=config.azure_openai.endpoint
            )
            
            system_prompt = """Eres un experto extractor de datos personales.
EXTRAE TODOS los datos que puedas identificar del texto del usuario.

CAMPOS A BUSCAR:
- nombre_tomador: Nombre completo (ej: "Juan Ramirez", "María González")
- identificacion_tomador: Cédula (6-11 dígitos, NO teléfono)
- celular_tomador: Teléfono celular (10 dígitos, empieza con 3)
- email_tomador: Correo electrónico

IMPORTANTE:
- Extrae TODOS los datos que encuentres
- NO inventes datos que no están
- Diferencia entre cédula (ej: 123456789) y teléfono (ej: 3001234567)
- El nombre debe tener al menos 2 palabras

Responde SOLO en formato JSON:
{"nombre_tomador": "...", "identificacion_tomador": "...", "celular_tomador": "...", "email_tomador": "..."}

Si no encuentras algún campo, omítelo del JSON."""

            response = client.chat.completions.create(
                model=config.azure_openai.chat_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            self.logger.info(f"🧠 LLM response: {result_text}")
            
            # Parse JSON response
            import json
            result = json.loads(result_text)
            
            # Validar que los datos tienen sentido
            validated_result = {}
            
            if "nombre_tomador" in result and len(result["nombre_tomador"].split()) >= 2:
                validated_result["nombre_tomador"] = result["nombre_tomador"]
                
            if "identificacion_tomador" in result and result["identificacion_tomador"].isdigit():
                cedula = result["identificacion_tomador"]
                if 6 <= len(cedula) <= 11 and not cedula.startswith('3'):
                    validated_result["identificacion_tomador"] = cedula
                    
            if "celular_tomador" in result and result["celular_tomador"].isdigit():
                phone = result["celular_tomador"]
                if len(phone) == 10 and phone.startswith('3'):
                    validated_result["celular_tomador"] = phone
                    
            if "email_tomador" in result and "@" in result["email_tomador"]:
                validated_result["email_tomador"] = result["email_tomador"]
            
            return validated_result
            
        except Exception as e:
            self.logger.error(f"❌ LLM extraction error: {e}")
            return {}
        
        # Buscar datos estructurados (formato "Campo: Valor")
        lines = user_input.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'cedula' in key or 'identificacion' in key:
                    client_data["identificacion_tomador"] = value
                elif 'telefono' in key or 'celular' in key:
                    client_data["celular_tomador"] = re.sub(r'[-\s]', '', value)
                elif 'email' in key or 'correo' in key:
                    client_data["email_tomador"] = value
        
        return client_data
    
    def _parse_plan_selection(self, user_input: str, quotation: Dict) -> Optional[str]:
        """Parsea selección de plan desde entrada del usuario"""
        if not quotation or "quotations" not in quotation:
            return None
        
        available_plans = list(quotation["quotations"].keys())
        user_input_lower = user_input.lower().strip()
        
        # MANEJAR SELECCIONES NUMÉRICAS (1, 2, 3) - también buscar en texto mixto
        if user_input_lower.isdigit():
            plan_index = int(user_input_lower) - 1  # Convertir a índice (1->0, 2->1, 3->2)
            if 0 <= plan_index < len(available_plans):
                selected_plan = available_plans[plan_index]
                self.logger.info(f"✅ Plan seleccionado por número: {user_input_lower} → {selected_plan}")
                return selected_plan
        
        # Buscar números al inicio del texto (ej: "1 Me gusta...")
        import re
        number_match = re.match(r'^(\d+)', user_input_lower.strip())
        if number_match:
            plan_number = int(number_match.group(1))
            plan_index = plan_number - 1
            if 0 <= plan_index < len(available_plans):
                selected_plan = available_plans[plan_index]
                self.logger.info(f"✅ Plan seleccionado por número al inicio: {plan_number} → {selected_plan}")
                return selected_plan
        
        # Buscar coincidencias directas
        for plan in available_plans:
            if plan.lower() in user_input_lower:
                return plan
        
        # Buscar por palabras clave
        if "basico" in user_input_lower:
            basic_plans = [p for p in available_plans if "basico" in p.lower()]
            if basic_plans:
                return basic_plans[0]
        
        if "clasico" in user_input_lower:
            classic_plans = [p for p in available_plans if "clasico" in p.lower()]
            if classic_plans:
                return classic_plans[0]
        
        if "global" in user_input_lower:
            global_plans = [p for p in available_plans if "global" in p.lower()]
            if global_plans:
                return global_plans[0]
        
        return None
    
    def _request_plan_selection(self, quotation: Dict) -> Dict[str, Any]:
        """Solicita selección de plan"""
        plans = quotation["quotations"]
        
        response_parts = [
            "Perfecto! Para proceder con la expedición, necesito que selecciones el plan que te interesa:",
            ""
        ]
        
        for i, (plan_name, plan_data) in enumerate(plans.items(), 1):
            prima_mensual = f"${plan_data['prima_mensual']:,.0f}"
            response_parts.append(f"{i}. **{plan_name}** - Prima mensual: {prima_mensual}")
        
        response_parts.extend([
            "",
            "Por favor escribe el nombre del plan que quieres contratar."
        ])
        
        return self.format_response(
            content="\n".join(response_parts),
            response_type="plan_selection"
        )
    
    def _request_client_data(self, selected_plan: str, quotation: Dict) -> Dict[str, Any]:
        """Solicita datos del cliente"""
        plan_data = quotation["quotations"][selected_plan]
        prima_mensual = f"${plan_data['prima_mensual']:,.0f}"
        
        response = (
            f"Excelente elección! Has seleccionado el **{selected_plan}** "
            f"con prima mensual de {prima_mensual}.\n\n"
            f"Para proceder con la expedición de tu póliza, necesito los siguientes datos:\n\n"
            f"• **Número de cédula**\n"
            f"• **Número de celular** (10 dígitos)\n"
            f"• **Correo electrónico**\n\n"
            f"Puedes enviarlos en el formato que prefieras, por ejemplo:\n"
            f"'Cédula: 12345678, Celular: 3001234567, Email: ejemplo@correo.com'"
        )
        
        return self.format_response(
            content=response,
            response_type="client_data_request",
            metadata={"selected_plan": selected_plan}
        )
    
    def _request_data_correction(self, validation_errors: Dict, current_data: Dict) -> Dict[str, Any]:
        """Solicita corrección de datos inválidos"""
        response_parts = [
            "He encontrado algunos problemas con los datos proporcionados:",
            ""
        ]
        
        for field, error in validation_errors.items():
            response_parts.append(f"• {error}")
        
        if current_data:
            response_parts.extend([
                "",
                "Datos que están correctos:"
            ])
            
            field_names = {
                "identificacion_tomador": "Cédula",
                "celular_tomador": "Celular", 
                "email_tomador": "Email"
            }
            
            for field, value in current_data.items():
                if field not in validation_errors:
                    field_name = field_names.get(field, field)
                    response_parts.append(f"• {field_name}: {value}")
        
        response_parts.extend([
            "",
            "Por favor corrige la información y envíala nuevamente."
        ])
        
        return self.format_response(
            content="\n".join(response_parts),
            response_type="data_correction_request"
        )
    
    def _request_purchase_confirmation(self, client_data: Dict, context_data: Dict) -> Dict[str, Any]:
        """Solicita confirmación de compra"""
        selected_plan = context_data.get("selected_plan")
        if not selected_plan:
            raise ValueError("No hay plan seleccionado")
            
        quotation = context_data.get("current_quotation", {})
        if not quotation:
            raise ValueError("No hay cotización disponible")
            
        plan_data = quotation.get("quotations", {}).get(selected_plan, {})
        vehicle_info = quotation.get("vehicle_details", quotation.get("vehicle_info", {}))
        
        response_parts = [
            "**Resumen de tu póliza:**",
            "",
            f"**Vehículo:** {vehicle_info['marca']} {vehicle_info['modelo']} {vehicle_info['linea']}",
            f"**Plan:** {selected_plan}",
            f"**Prima anual:** ${plan_data['prima_anual']:,.0f}",
            f"**Prima mensual:** ${plan_data['prima_mensual']:,.0f}",
            "",
            "**Datos del tomador:**",
            f"• Cédula: {client_data['identificacion_tomador']}",
            f"• Celular: {client_data['celular_tomador']}",
            f"• Email: {client_data['email_tomador']}",
            "",
            "**¿Confirmas que toda la información está correcta y deseas proceder con la expedición?**",
            "",
            "Responde 'Sí, confirmo' para proceder o 'No, quiero hacer cambios' para modificar."
        ]
        
        return self.format_response(
            content="\n".join(response_parts),
            response_type="purchase_confirmation"
        )
    
    def _format_success_response(self, expedition_result: Dict, selected_plan: str) -> Dict[str, Any]:
        """Formatea respuesta de expedición exitosa"""
        policy_number = expedition_result["numero_poliza"]
        
        response = (
            f"🎉 **¡Felicitaciones! Tu póliza ha sido expedida exitosamente.**\n\n"
            f"**Número de póliza:** {policy_number}\n"
            f"**Plan contratado:** {selected_plan}\n"
            f"**Fecha de emisión:** {expedition_result.get('fecha_expedicion', 'Hoy')}\n\n"
            f"**Próximos pasos:**\n"
            f"• Recibirás un correo con los detalles de tu póliza\n"
            f"• Un asesor se comunicará contigo para el seguimiento\n"
            f"• Puedes descargar la App Seguros SURA para gestionar tu póliza\n\n"
            f"¡Gracias por confiar en Seguros SURA! ¿Hay algo más en lo que pueda ayudarte?"
        )
        
        return self.format_response(
            content=response,
            response_type="expedition_success",
            metadata={
                "policy_number": policy_number,
                "expedition_result": expedition_result
            }
        )
    
    def _format_error_response(self, expedition_result: Dict) -> Dict[str, Any]:
        """Formatea respuesta de error en expedición"""
        error_msg = expedition_result.get("error", "Error desconocido")
        
        response = (
            f"Lo siento, ocurrió un problema durante la expedición de tu póliza:\n\n"
            f"**Error:** {error_msg}\n\n"
            f"No te preocupes, te voy a conectar con un asesor humano que podrá "
            f"completar el proceso manualmente y resolver cualquier inconveniente."
        )
        
        return self.format_response(
            content=response,
            response_type="expedition_error",
            metadata={"error_details": expedition_result}
        )
    
    def _provide_policy_details(self, expedition_result: Dict, context_data: Dict) -> str:
        """Proporciona detalles de la póliza expedida"""
        policy_number = expedition_result.get("numero_poliza")
        selected_plan = context_data.get("selected_plan")
        quotation = context_data.get("current_quotation", {})
        
        if quotation and selected_plan:
            plan_data = quotation["quotations"][selected_plan]
            vehicle_info = quotation["vehicle_info"]
            
            return (
                f"**Detalles de tu póliza {policy_number}:**\n\n"
                f"**Vehículo asegurado:**\n"
                f"• {vehicle_info['marca']} {vehicle_info['modelo']}\n"
                f"• Línea: {vehicle_info['linea']}\n"
                f"• Color: {vehicle_info['color']}\n\n"
                f"**Plan contratado:** {selected_plan}\n"
                f"**Prima mensual:** ${plan_data['prima_mensual']:,.0f}\n"
                f"**Prima anual:** ${plan_data['prima_anual']:,.0f}\n\n"
                f"Para más detalles sobre coberturas y condiciones, "
                f"consulta tu correo o contacta a tu asesor asignado."
            )
        else:
            return f"Tu póliza {policy_number} ha sido expedida. Para consultar detalles específicos, te recomiendo contactar a tu asesor."
    
    def get_expedition_summary(self, state: AgentState) -> Dict[str, Any]:
        """Genera resumen del proceso de expedición"""
        agent_state = self.load_agent_state(state.session_id) or {}
        
        return {
            "expedition_executed": agent_state.get("expedition_executed", False),
            "success": agent_state.get("success", False),
            "policy_number": agent_state.get("policy_number"),
            "selected_plan": agent_state.get("selected_plan"),
            "expedition_state": state.context_data.get("expedition_state")
        }
    
    def _request_missing_data(self, missing_fields: list, current_data: Dict) -> Dict[str, Any]:
        """Solicita datos faltantes específicos al cliente"""
        field_names = {
            "identificacion_tomador": "número de cédula",
            "celular_tomador": "número de teléfono",
            "email_tomador": "correo electrónico"
        }
        
        # Mostrar datos ya recibidos
        response_parts = []
        if current_data:
            response_parts.append("📝 **Información recibida:**")
            for key, value in current_data.items():
                if key == "nombre_tomador":
                    response_parts.append(f"• **Nombre:** {value}")
                elif key == "identificacion_tomador":
                    response_parts.append(f"• **Cédula:** {value}")
            response_parts.append("")
        
        # Solicitar siguiente dato
        next_field = missing_fields[0]
        field_description = field_names.get(next_field, next_field)
        
        response_parts.extend([
            f"Para continuar, necesito tu **{field_description}**.",
            "",
            "📱 Por favor envíamelo en tu próximo mensaje."
        ])
        
        return {
            "content": "\n".join(response_parts),
            "metadata": {"request_type": "missing_data", "missing_field": next_field}
        }
    
    def _extract_client_data_with_llm(self, user_input: str) -> Dict[str, str]:
        """Extrae datos del cliente usando LLM para entender lenguaje natural"""
        try:
            system_prompt = """Eres un experto en extraer información personal de mensajes.
Extrae ÚNICAMENTE los datos que puedas identificar con certeza absoluta.

CAMPOS A BUSCAR:
- nombre_tomador: Nombre completo de la persona (ej: Juan Pérez, María González)
- identificacion_tomador: Número de cédula/documento (solo números, 6-12 dígitos)
- celular_tomador: Número de teléfono (10 dígitos, puede tener espacios/guiones)
- email_tomador: Correo electrónico válido

IMPORTANTE: 
- Solo incluye campos que estés 100% seguro
- Para teléfonos, extrae solo los números (sin espacios/guiones)
- Para nombres, incluye nombre completo
- Si no estás seguro de un campo, NO lo incluyas

Responde en formato JSON estricto:
{"nombre_tomador": "...", "identificacion_tomador": "...", "celular_tomador": "...", "email_tomador": "..."}"""

            user_prompt = f"Extrae información personal de: '{user_input}'"
            
            from utils.config import config
            response = self.llm_client.chat.completions.create(
                model=config.azure_openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Filtrar campos vacíos
            filtered_result = {}
            for key, value in result.items():
                if value and str(value).strip() and str(value).lower() not in ["", "n/a", "null", "none"]:
                    filtered_result[key] = str(value).strip()
            
            self.logger.info(f"✅ LLM extrajo datos: {filtered_result} de '{user_input}'")
            return filtered_result
            
        except Exception as e:
            self.logger.warning(f"LLM extraction falló: {e}")
            return {}
    
    def _request_comprehensive_data(self, missing_fields: list, current_data: Dict) -> Dict[str, Any]:
        """SOLICITA TODOS LOS DATOS FALTANTES - SIN BUCLES"""
        field_names = {
            "identificacion_tomador": "número de cédula",
            "celular_tomador": "número de teléfono celular", 
            "email_tomador": "correo electrónico"
        }
        
        # Mostrar progreso de datos confirmados
        completed_fields = []
        for field_key, field_display in field_names.items():
            if field_key in current_data and current_data[field_key]:
                completed_fields.append(f"✅ {field_display.title()}: {current_data[field_key]}")
        
        # Datos faltantes
        missing_names = [field_names.get(field, field) for field in missing_fields]
        
        progress_text = ""
        if completed_fields:
            progress_text = f"📝 **Datos confirmados:**\n" + "\n".join(completed_fields) + "\n\n"
        
        if len(missing_fields) == 1:
            message = f"{progress_text}Para completar tu expedición, necesito tu **{missing_names[0]}**.\n\n📱 Envíamelo en tu próximo mensaje."
        else:
            missing_list = "\n".join([f"• {name}" for name in missing_names])
            message = f"{progress_text}🚀 **Para completar tu expedición, necesito:**\n\n{missing_list}\n\n📱 **Puedes enviarme todo junto en un solo mensaje.**"
        
        return {
            "content": message,
            "metadata": {"requesting_fields": missing_fields}
        }
