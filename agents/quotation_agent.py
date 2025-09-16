"""
Agente de Cotización - Especializado en generar cotizaciones multimodales.
Maneja análisis de imágenes de vehículos y generación de cotizaciones.
"""

import base64
from typing import Dict, Any, List, Optional
from io import BytesIO
from PIL import Image

from agents.base_agent import BaseAgent, AgentState, AgentCapabilities
from services.quotation_service import quotation_service
from utils.config import config

class QuotationAgent(BaseAgent):
    """Agente especializado en cotizaciones multimodales"""
    
    def __init__(self):
        super().__init__("quotation")
        self.quotation_service = quotation_service
        
        self.quotation_keywords = [
            "quiero cotizar", "necesito cotización", "cotizar mi", 
            "precio del seguro", "cuánto me cuesta el seguro",
            "imagen del vehículo", "foto del vehículo"
        ]
        
        # Estados del proceso de cotización
        self.STATES = {
            "AWAITING_IMAGE": "awaiting_image",
            "ANALYZING_IMAGE": "analyzing_image", 
            "AWAITING_DETAILS": "awaiting_details",
            "GENERATING_QUOTE": "generating_quote",
            "QUOTE_READY": "quote_ready"
        }
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> bool:
        """
        Determina si puede manejar solicitudes de cotización
        
        Args:
            user_input: Entrada del usuario
            context: Contexto de la conversación
            
        Returns:
            True si es una solicitud de cotización
        """
        user_input_lower = user_input.lower().strip()
        
        # NO manejar saludos simples o palabras sueltas que no son cotización
        simple_words = ["entonces", "bien", "si", "ok", "hola", "como estas", "bueno", "gracias"]
        if len(user_input_lower.split()) <= 2 and any(word in user_input_lower for word in simple_words):
            return False
        
        # DETECCIÓN INTELIGENTE DE CONTINUACIÓN DE COTIZACIÓN
        # Si el input contiene información de vehículo (modelo, marca, año, línea)
        vehicle_indicators = [
            "modelo", "marca", "año", "línea", "color", "clase",
            "ford", "toyota", "chevrolet", "nissan", "hyundai", "honda", "mazda",
            "automóvil", "camioneta", "suv", "sedan", "hatchback",
            "2020", "2021", "2022", "2023", "2024", "2025",  # años comunes
            "no sé", "no se", "no conozco", "no tengo idea"  # respuestas de usuario en cotización
        ]
        
        has_vehicle_info = any(indicator in user_input_lower for indicator in vehicle_indicators)
        
        # Si hay imagen en el input
        has_image_mention = any(word in user_input_lower for word in [
            "imagen", "foto", "fotografía", "picture", "subida", "adjunta"
        ])
        
        # Verificar palabras clave de cotización ESPECÍFICAS (más restrictivas)
        explicit_quotation_keywords = [
            "cotizar", "cotización", "quiero cotizar", "precio seguro", "valor póliza", "cuánto cuesta"
        ]
        has_explicit_quotation = any(keyword in user_input_lower for keyword in explicit_quotation_keywords)
        
        # Verificar palabras clave generales solo si no es una palabra suelta
        has_quotation_keywords = any(
            keyword in user_input_lower 
            for keyword in self.quotation_keywords
        ) and len(user_input_lower.split()) > 1
        
        # Verificar si hay imagen adjunta CON contexto de cotización
        has_image = context.get("has_image", False)
        has_quotation_context = context.get("quotation_state") in self.STATES.values()
        
        # Verificar si ya está en proceso de cotización
        is_in_quotation_process = context.get("quotation_state") in self.STATES.values()
        
        # NUEVO: Recuperar estado desde BD si el contexto está vacío
        if not is_in_quotation_process and hasattr(self, 'db_manager'):
            try:
                session_id = context.get("session_id")
                if session_id:
                    saved_state = self.db_manager.get_agent_state(session_id, "quotation")
                    if saved_state and saved_state.get("quotation_state") in self.STATES.values():
                        is_in_quotation_process = True
                        self.logger.debug(f"🔄 Estado de cotización recuperado desde BD: {saved_state.get('quotation_state')}")
            except Exception as e:
                self.logger.debug(f"No se pudo recuperar estado desde BD: {e}")
        
        # CONDICIONES EXPANDIDAS para routing inteligente
        return (
            has_explicit_quotation or 
            (has_quotation_keywords and len(user_input_lower) > 10) or 
            (has_image and has_quotation_context) or 
            is_in_quotation_process or
            (has_vehicle_info and len(user_input_lower) > 5) or  # Info de vehículo
            (has_image_mention and len(user_input_lower) > 10)   # Mención de imagen
        )
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Procesa solicitudes de cotización
        
        Args:
            state: Estado actual del agente
            
        Returns:
            Estado actualizado con respuesta
        """
        try:
            # Obtener estado específico de cotización
            quotation_state = state.context_data.get("quotation_state", "")
            image_data = state.context_data.get("image_data")
            
            self.logger.info("Procesando cotización", 
                           quotation_state=quotation_state,
                           has_image=bool(image_data))
            
            # Procesar según el estado actual
            if image_data and not quotation_state:
                # Iniciar análisis de imagen
                return await self._process_image_analysis(state, image_data)
            
            elif quotation_state == self.STATES["AWAITING_DETAILS"]:
                # Procesar detalles adicionales del vehículo
                return await self._process_vehicle_details(state)
            
            elif quotation_state == self.STATES["GENERATING_QUOTE"]:
                # Ya estamos generando cotización - informar status o procesar respuesta positiva
                user_input_lower = state.last_user_input.lower()
                if any(word in user_input_lower for word in ["continua", "continúa", "excelente", "perfecto", "sí", "si", "ok", "genial"]):
                    # Usuario está entusiasmado, verificar si ya tenemos cotización lista
                    if state.context_data.get("current_quotation"):
                        # Ya tenemos cotización, pasar a quote_ready
                        state.context_data["quotation_state"] = self.STATES["QUOTE_READY"]
                        response = self._format_quotation_response(state.context_data["current_quotation"])
                        state = self.update_state(state, agent_response=response["content"])
                        state = self.add_message_to_history(state, "assistant", response["content"])
                        return state
                    else:
                        # NO hay cotización y user está esperando - generar cotización fallback
                        self.logger.warning("Usuario esperando cotización que falló - generando fallback")
                        return await self._handle_quotation_fallback(state, {"marca": "CHEVROLET", "modelo": "2015", "clase": "AUTOMOVIL"}, "Cotización original falló")
                else:
                    # Respuesta genérica para generating_quote
                    response_content = "📊 Estoy procesando tu cotización. Por favor espera un momento mientras calculo las mejores opciones para tu vehículo."
                    state = self.update_state(state, agent_response=response_content)
                    state = self.add_message_to_history(state, "assistant", response_content)
                    return state
            
            elif quotation_state == self.STATES["QUOTE_READY"]:
                # ANTI-BUCLE: No manejar interacciones si viene de transferencia expedition
                previous_agent = state.context_data.get("previous_agent", "")
                if previous_agent == "expedition":
                    # Limpiar transferencia para evitar bucle
                    state.context_data.pop("previous_agent", None)
                    
                    # Verificar si el usuario quiere comprar un plan específico
                    user_input_lower = state.last_user_input.lower()
                    if any(word in user_input_lower for word in ["comprar", "adquirir", "plan"]):
                        # Usuario quiere comprar - transferir de vuelta a expedition pero CON cotización
                        response = (
                            "Perfecto! Ya tienes tu cotización lista. "
                            "Ahora procedo con la expedición de tu póliza. "
                            "Para esto necesito algunos datos personales."
                        )
                        state.context_data["transfer_to"] = "expedition"
                        state.context_data["expedition_ready"] = True  # Marcar que cotización existe
                    else:
                        # Solo mostrar cotización disponible
                        response = "Ya tienes una cotización lista. ¿Te gustaría proceder con la expedición de algún plan específico?"
                        # NO force_end - permitir continuar flujo
                        state.context_data["transfer_to"] = "expedition"
                        state.context_data["expedition_ready"] = True
                    
                    state = self.update_state(state, agent_response=response)
                    state = self.add_message_to_history(state, "assistant", response)
                    return state
                else:
                    # Manejar interacciones normales con cotización existente
                    return await self._handle_quote_interaction(state)
                
            else:
                # Solicitar imagen o detalles
                return await self._request_quotation_info(state)
        
        except Exception as e:
            # LOGGING DETALLADO para debuggear el problema
            self.logger.error(f"💥 ERROR DETALLADO en QuotationAgent: {str(e)}", 
                            exc_info=True,
                            quotation_state=quotation_state,
                            has_image=bool(image_data),
                            user_input=state.last_user_input[:100])
            
            self.log_error(e, state, {
                "quotation_state": quotation_state,
                "has_image": bool(image_data),
                "user_input": state.last_user_input,
                "context_data": state.context_data
            })
            
            # RESPUESTA DE ERROR TEMPORAL para debugging
            error_response = (
                f"🐛 **Error DEBUG**: {str(e)[:200]}...\n\n"
                "Esto es información temporal para debugging. "
                "Escribe 'hablar con asesor' si necesitas ayuda inmediata."
            )
            
            state = self.update_state(state, agent_response=error_response)
            state = self.add_message_to_history(state, "assistant", error_response)
            
            return state
    
    
    def analyze_vehicle_image(self, image_data: str) -> Dict[str, Any]:
        """
        Método unificado para análisis de imagen utilizando QuotationService
        
        Args:
            image_data: Datos de imagen en formato base64 o bytes
            
        Returns:
            Dict con resultado del análisis
        """
        try:
            # Convertir si es necesario
            if isinstance(image_data, str):
                # Asumir que es base64 y convertir a bytes
                import base64
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            # Usar servicio de cotización para análisis
            analysis_result = self.quotation_service.analyze_vehicle_from_image(image_bytes)
            
            return {
                "success": True,
                "vehicle_info": analysis_result,
                "confidence": 0.85 if "NO_DETECTADO" not in str(analysis_result) else 0.5
            }
            
        except Exception as e:
            self.logger.error(f"Error en análisis de imagen: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vehicle_info": {},
                "confidence": 0.0
            }
    
    async def _handle_quotation_fallback(self, state: AgentState, vehicle_details: Dict[str, str], error_msg: str) -> AgentState:
        """Maneja fallback cuando la cotización exacta falla - EVITA ERROR DEBUG"""
        self.logger.warning("Activando cotización fallback inteligente")
        
        # Crear cotización genérica estimada
        estimated_quote = {
            "plans": [
                {
                    "name": "Plan Básico Estimado",
                    "annual_premium": "850,000",
                    "monthly_premium": "70,833",
                    "description": "Cobertura básica estimada para tu vehículo"
                },
                {
                    "name": "Plan Clásico Estimado", 
                    "annual_premium": "1,200,000",
                    "monthly_premium": "100,000",
                    "description": "Cobertura amplia estimada"
                }
            ],
            "vehicle_info": vehicle_details,
            "is_estimated": True
        }
        
        # Guardar cotización estimada
        state.context_data["current_quotation"] = estimated_quote
        state.context_data["quotation_state"] = self.STATES["QUOTE_READY"]
        
        # Respuesta profesional sin exponer error técnico
        response_content = f"""🚗 **Cotización Estimada para tu Vehículo**

He generado una cotización estimada basada en la información disponible:

**Vehículo:** {vehicle_details.get('marca', 'N/A')} {vehicle_details.get('modelo', 'N/A')}
**Clase:** {vehicle_details.get('clase', 'N/A')}

**📋 Planes Disponibles:**

**Plan Básico Estimado**
• Prima anual: $850,000
• Prima mensual: $70,833
• Cobertura esencial

**Plan Clásico Estimado**
• Prima anual: $1,200,000  
• Prima mensual: $100,000
• Cobertura amplia

*💡 Nota: Esta es una cotización estimada. Para obtener valores exactos y personalizados, un asesor puede ayudarte con más detalles específicos de tu vehículo.*

¿Te interesa alguno de estos planes o prefieres hablar con un asesor para más información?"""

        state = self.update_state(state, agent_response=response_content)
        state = self.add_message_to_history(state, "assistant", response_content)
        
        return state
    
    
    async def _llm_analysis_before_escalation(self, state: AgentState, vehicle_details: Dict[str, str], error_msg: str) -> AgentState:
        """Usa LLM para analizar si podemos solicitar más información antes de escalar"""
        self.logger.info(f"🧠 Análisis LLM antes de escalamiento: {vehicle_details}")
        
        try:
            # Contexto para el LLM
            context = f"""
CONTEXTO: El usuario quiere cotizar un seguro de vehículo pero faltan datos exactos.
DATOS DETECTADOS: {vehicle_details}
CATÁLOGO DISPONIBLE: CHEVROLET, HYUNDAI, RENAULT (automóviles y camionetas)
ERROR TÉCNICO: {error_msg[:200]}

TAREA: Analiza si podemos pedir información más específica al usuario antes de escalarlo.

CRITERIOS:
1. Si es una marca no cubierta (KIA, Mazda, etc.) → Ofrecer marca similar
2. Si falta clase/línea específica → Pedir aclaración  
3. Si es vehículo no asegurable (camión pesado, etc.) → Explicar limitación
4. Si datos son muy vagos → Solicitar información específica

RESPONDE EN JSON:
{{
    "accion": "pedir_info" | "ofrecer_alternativa" | "explicar_limitacion" | "escalar",
    "razon": "explicación clara",
    "mensaje_usuario": "mensaje profesional para el usuario",
    "sugerencia": "marca/datos alternativos si aplica"
}}
"""

            from openai import AzureOpenAI
            from utils.config import config
            
            client = AzureOpenAI(
                api_key=config.azure_openai.api_key,
                api_version=config.azure_openai.api_version,
                azure_endpoint=config.azure_openai.endpoint
            )
            
            response = client.chat.completions.create(
                model=config.azure_openai.chat_deployment,
                messages=[{"role": "user", "content": context}],
                temperature=0.3,
                max_tokens=500
            )
            
            llm_response = response.choices[0].message.content
            self.logger.info(f"📋 Respuesta LLM: {llm_response}")
            
            # Parsear respuesta JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                
                accion = analysis.get("accion", "escalar")
                mensaje = analysis.get("mensaje_usuario", "")
                
                if accion == "escalar":
                    # LLM determina que debemos escalar
                    return self._escalate_to_human(state, analysis.get("razon", "Análisis LLM recomienda escalamiento"))
                else:
                    # LLM sugiere pedir más información
                    self.logger.info(f"✅ LLM sugiere: {accion} - {analysis.get('razon')}")
                    
                    response_content = mensaje if mensaje else "Necesito información más específica sobre tu vehículo para poder generar una cotización adecuada. ¿Podrías proporcionar más detalles?"
                    
                    state = self.update_state(state, agent_response=response_content)
                    state = self.add_message_to_history(state, "assistant", response_content)
                    
                    # Mantener en estado awaiting_details para otra oportunidad
                    state.context_data["quotation_state"] = self.STATES["AWAITING_DETAILS"]
                    state.context_data["llm_analysis"] = analysis
                    
                    return state
            
        except Exception as e:
            self.logger.error(f"Error en análisis LLM: {str(e)}")
        
        # Si falla el LLM, escalar normalmente Y resetear estado
        state.context_data["quotation_state"] = self.STATES["AWAITING_DETAILS"]  # Reset para evitar bucle
        return self._escalate_to_human(state, f"Fallo en análisis automático: {error_msg[:100]}")
    
    def _escalate_to_human(self, state: AgentState, reason: str) -> AgentState:
        """Escala a asesor humano con razón específica"""
        self.logger.info(f"👨‍💼 Escalando a humano: {reason}")
        
        state.context_data["transfer_to"] = "human_loop"
        state.context_data["escalation_reason"] = reason
        
        return state

    async def _process_image_analysis(self, state: AgentState, image_data: str) -> AgentState:
        """Procesa análisis de imagen de vehículo con VALIDACIÓN PROFESIONAL"""
        try:
            self.logger.info("Iniciando análisis PROFESIONAL de imagen de vehículo")
            
            # Marcar inicio del análisis
            state.context_data["quotation_state"] = self.STATES["ANALYZING_IMAGE"]
            
            # Analizar imagen usando método unificado
            analysis_result = self.analyze_vehicle_image(image_data)
            
            if analysis_result.get("success", False):
                # Análisis exitoso
                vehicle_info = analysis_result.get("vehicle_info", {})
                confidence = analysis_result.get("confidence", 0.0)
                
                # DEBUG: Log análisis completo
                self.logger.info(f"🔍 ANÁLISIS IMAGEN COMPLETO:")
                self.logger.info(f"  vehicle_info: {vehicle_info}")
                self.logger.info(f"  confidence: {confidence}")
                
                # VALIDAR calidad del análisis
                required_fields = ["marca", "clase", "color"]
                detected_fields = {k: v for k, v in vehicle_info.items() if v and v != "NO_DETECTADO"}
                missing_fields = [field for field in required_fields if field not in detected_fields]
                
                self.logger.info(f"  detected_fields: {detected_fields}")
                self.logger.info(f"  missing_fields: {missing_fields}")
                
                # Guardar análisis COMPLETO en contexto
                state.context_data["vehicle_analysis"] = vehicle_info
                state.context_data["analysis_confidence"] = confidence
                state.context_data["detected_fields"] = detected_fields
                state.context_data["missing_fields"] = missing_fields
                state.context_data["quotation_state"] = self.STATES["AWAITING_DETAILS"]
                
                # Generar respuesta PROFESIONAL basada en análisis
                detected_info = []
                for field, value in detected_fields.items():
                    if field == "marca":
                        detected_info.append(f"🏭 **Marca**: {value}")
                    elif field == "clase":
                        detected_info.append(f"🚗 **Clase**: {value}")
                    elif field == "color":
                        detected_info.append(f"🎨 **Color**: {value}")
                
                if detected_info:
                    detected_text = "\n".join(detected_info)
                    
                    # Lista dinámica de datos faltantes
                    still_missing = []
                    if not detected_fields.get("marca"):
                        still_missing.append("• **Marca** del vehículo")
                    if not vehicle_info.get("modelo"):
                        still_missing.append("• **Modelo** (año del vehículo)")
                    if not vehicle_info.get("linea"):
                        still_missing.append("• **Línea** específica del vehículo")
                    
                    if still_missing:
                        missing_text = "\n".join(still_missing)
                        response_content = f"¡Perfecto! He analizado la imagen de tu vehículo. Detecté:\n\n{detected_text}\n\nPara completar tu cotización, necesito que me proporciones:\n\n{missing_text}\n\n💡 **Tip:** Puedes escribir algo como 'Toyota 2020'."
                else:
                        # Tenemos suficiente información, pero verificar si es marca asegurable
                        self.logger.info("✅ Información suficiente de imagen, verificando asegurabilidad")
                        complete_details = self._apply_smart_defaults(vehicle_info, vehicle_info)
                        
                        # Verificar si marca está en catálogo
                        marca_detectada = complete_details.get("marca", "").upper()
                        marcas_catalogadas = ["CHEVROLET", "HYUNDAI", "RENAULT", "TOYOTA"]
                        
                        if marca_detectada not in marcas_catalogadas:
                            # Marca no cubierta - usar LLM para sugerir alternativas
                            self.logger.info(f"🧠 Marca {marca_detectada} no en catálogo, activando análisis LLM")
                            return await self._llm_analysis_before_escalation(state, complete_details, f"Marca {marca_detectada} no está en catálogo")
                        else:
                            # Marca válida, proceder con cotización
                            return await self._generate_quotation(state, complete_details)
            else:
                response_content = "He recibido la imagen de tu vehículo. Para generar una cotización personalizada necesito que me proporciones:\n\n• **Marca** del vehículo\n• **Modelo** (año)\n• **Línea** específica\n• **Clase** (automóvil, camioneta, etc.)\n• **Color**\n\n💡 **Tip:** Puedes escribir algo como 'Toyota Corolla 2020' o 'no sé algunos datos'."
            
            # Establecer estado esperando detalles
            state.context_data["quotation_state"] = self.STATES["AWAITING_DETAILS"]
            
            # Actualizar estado
            state = self.update_state(state, agent_response=response_content)
            state = self.add_message_to_history(state, "assistant", response_content)
            
            # Guardar estado del agente
            self.save_agent_state(state, {
                "quotation_state": state.context_data.get("quotation_state"),
                "vehicle_analysis": state.context_data.get("vehicle_analysis", {}),
                "analysis_confidence": state.context_data.get("analysis_confidence", 0.0)
            })
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error en análisis de imagen: {str(e)}")
            
            # Respuesta de error
            error_response = "No pude procesar la imagen en este momento. Por favor, proporciona manualmente los datos de tu vehículo:\n\n• **Marca**\n• **Modelo** (año)\n• **Línea** específica\n• **Clase** (automóvil, camioneta, etc.)\n• **Color**"
            
            state.context_data["quotation_state"] = self.STATES["AWAITING_DETAILS"]
            state = self.update_state(state, agent_response=error_response)
            state = self.add_message_to_history(state, "assistant", error_response)
            
            return state
    
    async def _process_vehicle_details(self, state: AgentState) -> AgentState:
        """Procesa detalles adicionales del vehículo proporcionados por el usuario CON MANEJO INTELIGENTE"""
        try:
            vehicle_analysis = state.context_data.get("vehicle_analysis", {})
            user_input = state.last_user_input.lower()
            
            # Detectar si el usuario expresa que NO CONOCE cierta información
            user_doesnt_know = any(phrase in user_input for phrase in [
                "no sé", "no se", "no conozco", "no tengo idea", "no estoy seguro",
                "no lo sé", "no recuerdo", "no saben", "desconozco", "no tengo esa información",
                "linea no", "línea no", "no sé la", "no se la", "no conozco la",
                "no estoy segur", "no tengo claro", "no me acuerdo"
            ])
            
            # Parsear entrada del usuario para extraer detalles
            details = self._parse_vehicle_details(state.last_user_input, vehicle_analysis)
            
            # Contar cuántas veces hemos pedido información
            attempt_count = state.context_data.get("detail_request_attempts", 0)
            
            # VALIDACIÓN MUY FLEXIBLE - Solo marca es realmente esencial
            if state.context_data.get("flexible_mode"):
                essential_fields = ["marca"]  # SOLO marca es obligatoria en modo flexible
            else:
                essential_fields = ["marca", "modelo"]  # Mínimo absoluto
            
            missing_essential = [field for field in essential_fields if not details.get(field)]
            
            # LÓGICA INTELIGENTE: Si usuario no sabe o muchos intentos, usar valores por defecto
            if user_doesnt_know or attempt_count >= 1:
                self.logger.info(f"🎯 ACTIVANDO SMART DEFAULTS: user_doesnt_know={user_doesnt_know}, attempt_count={attempt_count}")
                self.logger.info(f"📝 Input del usuario: '{user_input[:100]}'")
                self.logger.info(f"📊 Detalles parseados: {details}")
                
                # Aplicar valores por defecto inteligentes
                details = self._apply_smart_defaults(details, vehicle_analysis)
                
                # Proceder con cotización usando valores estimados
                response_content = f"""Entiendo que no tienes toda la información específica. Procederé con una cotización estimada basada en los datos disponibles:

🚗 **Información del vehículo:**
- **Marca**: {details.get('marca', 'Detectada de imagen')}
- **Modelo**: {details.get('modelo', 'Estimado')}
- **Clase**: {details.get('clase', 'Detectada de imagen')}
- **Línea**: {details.get('linea', 'Estándar')} (estimada)
- **Color**: {details.get('color', 'Detectado de imagen')}

*Nota: Esta es una cotización estimada. Los valores finales pueden variar según las especificaciones exactas del vehículo.*

✅ **Procediendo a generar tu cotización...**"""
                
                state = self.update_state(state, agent_response=response_content)
                state = self.add_message_to_history(state, "assistant", response_content)
                
                return await self._generate_quotation(state, details)
            
            # Si faltan campos esenciales y el usuario no expresó desconocimiento
            if missing_essential:
                state.context_data["detail_request_attempts"] = attempt_count + 1
                has_image_analysis = bool(vehicle_analysis and len(vehicle_analysis) > 0)
                if attempt_count >= 1 or has_image_analysis:
                    self.logger.info(f"✅ Aplicando cotización inteligente con información disponible (attempt={attempt_count}, has_image={has_image_analysis})")
                    details = self._apply_smart_defaults(details, vehicle_analysis)
                    if has_image_analysis:
                        auto_message = (
                            "✅ **Perfecto!** Combinando la información de la imagen con los datos que proporcionaste.\n\n"
                            "He completado los detalles faltantes para generar tu cotización. "
                            "📊 **Generando tu cotización personalizada...**"
                        )
                    else:
                        auto_message = (
                            "✅ **Perfecto!** Tengo suficiente información para generar tu cotización.\n\n"
                            "He completado los datos faltantes con valores típicos del mercado colombiano. "
                            "📊 **Generando tu cotización personalizada...**"
                        )
                    
                    state = self.update_state(state, agent_response=auto_message)
                    state = self.add_message_to_history(state, "assistant", auto_message)
                    return await self._generate_quotation(state, details)
                
                response_content = (
                    f"🚗 **Casi listo para tu cotización!**\n\n"
                    f"Solo necesito confirmar: **{', '.join(missing_essential)}**\n\n"
                    f"💡 **Ejemplos útiles:**\n"
                    f"• Marca: Toyota, Chevrolet, Renault, Ford\n"
                    f"• Modelo: 2020, 2018, 2022\n"
                    f"• Tipo: sedán, hatchback, SUV, camioneta\n\n"
                    f"🤝 Si no conoces algún dato exacto, escribe 'no sé' y usaré valores estimados."
                )
                state = self.update_state(state, agent_response=response_content)
                state = self.add_message_to_history(state, "assistant", response_content)
                
                # MARCAR que la siguiente respuesta debe proceder directamente
                state.context_data["quotation_completed"] = False
                state.context_data["awaiting_user_response"] = True
                state.context_data["force_proceed_next"] = True  # Nuevo flag
                
                return state
            
            # Aplicar smart defaults SIEMPRE para garantizar todas las claves necesarias
                details = self._apply_smart_defaults(details, vehicle_analysis)
            
            # VERIFICAR que todas las claves necesarias existen antes de validar
            required_keys = ["marca", "modelo", "linea", "clase"]
            for key in required_keys:
                if key not in details:
                    self.logger.warning(f"🔴 Clave faltante '{key}', aplicando valor por defecto de emergencia")
                    if key == "marca":
                        details[key] = "Toyota"
                    elif key == "modelo":
                        details[key] = "2020"
                    elif key == "linea":
                        details[key] = "Estándar"
                    elif key == "clase":
                        details[key] = "Automóvil"
            
            # LOG para debugging
            self.logger.info(f"✅ Detalles finales para validación: {details}")
            
            # Validar que el vehículo sea asegurable
            is_insurable = self.quotation_service.validate_vehicle_data(
                marca=details["marca"],
                modelo=details["modelo"],
                linea=details["linea"],
                clase=details["clase"]
            )
            
            if not is_insurable:
                # INTENTAR ALTERNATIVAS antes de escalar
                alternative_details = self._try_vehicle_alternatives(details)
                
                if alternative_details:
                    # Usar la alternativa encontrada
                    self.logger.info(f"✅ Alternativa encontrada: {alternative_details}")
                    response = (
                        f"He encontrado una opción similar en nuestro catálogo:\n\n"
                        f"🚗 **{alternative_details['marca']} {alternative_details['linea']} {alternative_details['modelo']}**\n\n"
                        f"Procedo a generar la cotización con esta alternativa..."
                    )
                    state = self.update_state(state, agent_response=response)
                    state = self.add_message_to_history(state, "assistant", response)
                    
                    # Generar cotización con la alternativa
                    return await self._generate_quotation(state, alternative_details)
                else:
                    # Solo escalar como último recurso
                    response = self._vehicle_not_insurable_response(details)
                    state = self.update_state(state, agent_response=response["content"])
                    state = self.add_message_to_history(state, "assistant", response["content"])
                    
                    # Marcar para escalamiento
                    state.needs_human_intervention = True
                    state.escalation_reason = "Vehículo no asegurable según catálogo"
                    
                    return state
            
            # Generar cotización
            return await self._generate_quotation(state, details)
            
        except Exception as e:
            self.logger.error(f"Error procesando detalles: {str(e)}")
            raise
    
    def _apply_smart_defaults(self, details: Dict[str, Any], vehicle_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica valores por defecto inteligentes basados en la información disponible"""
        
        # Usar análisis de imagen como primera opción
        if not details.get("marca") and vehicle_analysis.get("marca"):
            details["marca"] = vehicle_analysis["marca"]
        
        if not details.get("clase") and vehicle_analysis.get("clase"):
            details["clase"] = vehicle_analysis["clase"]
            
        if not details.get("color") and vehicle_analysis.get("color"):
            details["color"] = vehicle_analysis["color"]
        
        if not details.get("marca"):
            details["marca"] = "CHEVROLET"  # Marca popular en catálogo
            
        if not details.get("clase"):
            marca = details.get("marca", "").lower()
            if any(x in marca for x in ["ford", "chevrolet", "toyota"]):
                details["clase"] = "AUTOMOVIL"
            else:
                details["clase"] = "AUTOMOVIL"
            
        if not details.get("color"):
            details["color"] = "Blanco"
            
        if not details.get("linea"):
            marca = details.get("marca", "").lower()
            clase = details.get("clase", "").upper()
            
            if "MOTOCICLETA" in clase or "MOTO" in clase:
                if "suzuki" in marca:
                    details["linea"] = "GN125"
                elif "yamaha" in marca:
                    details["linea"] = "XTZ125"
                elif "honda" in marca:
                    details["linea"] = "CB125"
                else:
                    details["linea"] = "ESTÁNDAR"
            elif "chevrolet" in marca.lower():
                details["linea"] = "LS - MT 1400CC 4P AA AB"
            elif "hyundai" in marca.lower():
                details["linea"] = "PRIME - MT 1000CC CITY TAXI"
            elif "renault" in marca.lower():
                details["linea"] = "EXPRESSION - MT 1600CC 4X2"
            elif "toyota" in marca.lower():
                details["linea"] = "TX - MT 2700CC 4X4"
            elif "ford" in marca.lower():
                details["marca"] = "CHEVROLET"
                details["linea"] = "LS - MT 1800CC"
                self.logger.info(f"🔄 Mapeando FORD → CHEVROLET (catálogo compatible)")
            else:
                details["linea"] = "LS - MT 1400CC 4P AA AB"
        
        if not details.get("modelo"):
            details["modelo"] = "2015"
            
        self.logger.info(f"Valores aplicados: {details}")
        return details
    
    def _try_vehicle_alternatives(self, original_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Intenta encontrar alternativas del vehículo en el catálogo
        """
        try:
            marca = original_details.get("marca", "")
            modelo = original_details.get("modelo", "")
            linea_original = original_details.get("linea", "")
            clase = original_details.get("clase", "")
            
            # Lista de alternativas REALES basadas en el catálogo actual
            alternatives = {
                "renault": {
                    "sandero": ["EXPRESSION - MT 1600CC AA", "EXPRESSION - MT 1600CC 4X2", "DYNAMIQUE - MT 2000CC 4X4"],
                    "logan": ["EXPRESSION - MT 1600CC AA", "EXPRESSION - MT 1600CC 4X2"],
                    "duster": ["DYNAMIQUE - MT 2000CC 4X4", "EXPRESSION - MT 1600CC 4X2"]
                },
                "hyundai": {
                    "accent": ["PRIME - MT 1000CC CITY TAXI", "CITY TAXI PLUS - MT 1100CC SA TAXI"],
                    "i10": ["PRIME - MT 1000CC CITY TAXI", "CITY TAXI PLUS - MT 1100CC SA TAXI"]
                },
                "chevrolet": {
                    "spark": ["GT [M300] - MT 1200CC 5P FE"],
                    "aveo": ["GT [M300] - MT 1200CC 5P FE"]
                },
                "toyota": {
                    "corolla": ["TX - MT 2700CC 4X4", "XEI - MT 1800CC"],
                    "yaris": ["TX - MT 2700CC 4X4"],
                    "rav4": ["TX - MT 2700CC 4X4"]
                }
            }
            
            marca_lower = marca.lower()
            linea_lower = linea_original.lower()
            
            # Buscar alternativas para la marca/línea
            if marca_lower in alternatives:
                for base_line, variations in alternatives[marca_lower].items():
                    if base_line in linea_lower:
                        for variation in variations:
                            if variation != linea_original:  # No probar la misma línea
                                test_details = original_details.copy()
                                test_details["linea"] = variation
                                
                                # Probar si esta alternativa es asegurable
                                is_insurable = self.quotation_service.validate_vehicle_data(
                                    marca=test_details["marca"],
                                    modelo=test_details["modelo"],
                                    linea=test_details["linea"],
                                    clase=test_details["clase"]
                                )
                                
                                if is_insurable:
                                    self.logger.info(f"✅ Alternativa encontrada: {variation} para {linea_original}")
                                    # APLICAR SMART DEFAULTS COMPLETOS a la alternativa
                                    complete_details = self._apply_smart_defaults(test_details, {})
                                    return complete_details
            
            # Si no encontramos alternativas específicas, intentar con líneas genéricas del catálogo REAL
            generic_lines = [
                "EXPRESSION - MT 1600CC AA",  # Renault más común
                "GT [M300] - MT 1200CC 5P FE",  # Chevrolet común
                "PRIME - MT 1000CC CITY TAXI",  # Hyundai común
                "TX - MT 2700CC 4X4"  # Toyota común
            ]
            for generic_line in generic_lines:
                test_details = original_details.copy()
                test_details["linea"] = generic_line
                
                is_insurable = self.quotation_service.validate_vehicle_data(
                    marca=test_details["marca"],
                    modelo=test_details["modelo"],
                    linea=test_details["linea"],
                    clase=test_details["clase"]
                )
                
                if is_insurable:
                    self.logger.info(f"✅ Alternativa genérica encontrada: {generic_line}")
                    # APLICAR SMART DEFAULTS COMPLETOS a la alternativa genérica
                    complete_details = self._apply_smart_defaults(test_details, {})
                    return complete_details
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error buscando alternativas: {str(e)}")
            return None
    
    async def _generate_quotation(self, state: AgentState, vehicle_details: Dict[str, str]) -> AgentState:
        """Genera cotización para el vehículo CON MANEJO ROBUSTO DE ERRORES"""
        try:
            self.logger.info("Generando cotización", vehicle=vehicle_details)
            
            state.context_data["quotation_state"] = self.STATES["GENERATING_QUOTE"]
            
            # INTENTO 1: Cotización con datos exactos
            try:
                quotation_result = self.quotation_service.generate_quotation(
                    marca=vehicle_details["marca"],
                    modelo=vehicle_details["modelo"],
                    linea=vehicle_details["linea"],
                    clase=vehicle_details["clase"],
                    color=vehicle_details["color"]
                )
                self.logger.info("✅ Cotización exitosa con datos exactos")
                
            except Exception as e:
                self.logger.warning(f"❌ Falló cotización exacta: {str(e)[:100]}")
                
                # INTENTO 2: Usar alternativas inteligentes
                self.logger.info("🔄 Intentando con alternativas...")
                alternative_details = self._try_vehicle_alternatives(vehicle_details)
                
                try:
                    quotation_result = self.quotation_service.generate_quotation(
                        marca=alternative_details["marca"],
                        modelo=alternative_details["modelo"],
                        linea=alternative_details["linea"],
                        clase=alternative_details["clase"],
                        color=alternative_details["color"]
                    )
                    self.logger.info("✅ Cotización exitosa con alternativas")
                    # Actualizar vehicle_details para la respuesta
                    vehicle_details.update(alternative_details)
                    
                except Exception as e2:
                    self.logger.error(f"❌ Falló cotización con alternativas: {str(e2)[:100]}")
                    
                    # INTENTO 3: Análisis LLM antes de escalar
                    return await self._llm_analysis_before_escalation(state, vehicle_details, str(e))
            
            # Guardar cotización en contexto y BD
            state.context_data["current_quotation"] = quotation_result
            state.context_data["quotation_state"] = self.STATES["QUOTE_READY"]
            
            # Persistir cotización en BD
            quotation_id = self.db_manager.save_quotation(
                session_id=state.session_id,
                vehicle_data=vehicle_details,
                quotation_result=quotation_result
            )
            
            state.context_data["quotation_id"] = quotation_id
            
            # Formatear respuesta
            response = self._format_quotation_response(quotation_result)
            
            state = self.update_state(state, agent_response=response["content"])
            state = self.add_message_to_history(
                state, "assistant", response["content"],
                metadata=response.get("metadata", {})
            )
            
            # Guardar estado del agente
            self.save_agent_state(state, {
                "quotation_id": quotation_id,
                "vehicle_details": vehicle_details,
                "quotation_generated": True,
                "plans_quoted": list(quotation_result["quotations"].keys())
            })
            
            self.log_interaction(
                state, vehicle_details, quotation_result,
                quotation_id=quotation_id,
                plans_count=len(quotation_result["quotations"])
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error generando cotización: {str(e)}")
            raise
    
    async def _handle_quote_interaction(self, state: AgentState) -> AgentState:
        """Maneja interacciones con cotización existente"""
        user_input_lower = state.last_user_input.lower()
        
        # Verificar si quiere comprar/expedir
        if any(word in user_input_lower for word in ["comprar", "adquirir", "expedir", "emitir", "sí acepto"]):
            # Transferir a agente de expedición
            response = (
                "Perfecto! Para proceder con la expedición de tu póliza, "
                "necesito algunos datos personales. Un momento mientras "
                "te conecto con el proceso de expedición."
            )
            
            state.context_data["transfer_to"] = "expedition"
            state.context_data["transfer_reason"] = "Usuario desea comprar póliza"
            
        # Verificar si quiere modificar cotización
        elif any(word in user_input_lower for word in ["cambiar", "modificar", "otro plan", "diferente"]):
            response = (
                "Claro, puedo ayudarte a modificar tu cotización. "
                "¿Qué te gustaría cambiar? ¿El plan, algún detalle del vehículo, o necesitas una nueva cotización?"
            )
            
        # Verificar si tiene más preguntas
        elif any(word in user_input_lower for word in ["qué incluye", "cobertura", "detalles", "más información"]):
            response = (
                "Te puedo dar más detalles sobre cualquiera de los planes cotizados. "
                "También puedo conectarte con un asesor especializado que te puede "
                "explicar todas las coberturas en detalle. ¿Qué prefieres?"
            )
            
        else:
            # Respuesta general
            current_quotation = state.context_data.get("current_quotation", {})
            plans = list(current_quotation.get("quotations", {}).keys())
            
            response = (
                f"Tienes una cotización lista con {len(plans)} planes disponibles. "
                "Puedes:\n"
                "• Proceder con la compra de algún plan\n"
                "• Solicitar más información sobre las coberturas\n"
                "• Modificar algún detalle de la cotización\n"
                "• Hablar con un asesor especializado\n\n"
                "¿Qué te gustaría hacer?"
            )
        
        state = self.update_state(state, agent_response=response)
        state = self.add_message_to_history(state, "assistant", response)
        
        return state
    
    async def _request_quotation_info(self, state: AgentState) -> AgentState:
        """Solicita información inicial para cotización CON FLEXIBILIDAD y ORIENTACIÓN"""
        response = (
            "🚗 **¡Excelente! Te ayudo a cotizar tu seguro de autos.**\n\n"
            "Para generar una cotización rápida y personalizada, compárteme la información que tengas:\n\n"
            "🔹 **Marca** (ej: Toyota, Chevrolet, Renault, Ford)\n"
            "🔹 **Modelo/Año** (ej: 2020, 2018, 2022)\n"
            "🔹 **Tipo** (ej: sedán, SUV, hatchback, camioneta)\n"
            "🔹 **Foto del vehículo** (opcional, pero acelera el proceso)\n\n"
            "💡 **¡Tranquilo!** No necesitas información técnica específica. "
            "Con datos básicos como 'Toyota 2020 sedán' puedo generar una cotización.\n\n"
            "🎯 **Ejemplos de respuestas útiles:**\n"
            "• 'Toyota Corolla 2020'\n"
            "• 'Chevrolet Onix 2021 blanco'\n"
            "• 'Renault Sandero 2019'\n\n"
            "**¿Cuéntame sobre tu vehículo?**"
        )
        
        state.context_data["quotation_state"] = self.STATES["AWAITING_DETAILS"]  # Cambio directo a detalles
        state.context_data["flexible_mode"] = True  # Modo flexible activado
        
        state = self.update_state(state, agent_response=response)
        state = self.add_message_to_history(state, "assistant", response)
        
        return state
    
    def _parse_vehicle_details(self, user_input: str, existing_analysis: Dict) -> Dict[str, str]:
        """
        Parsea detalles del vehículo desde entrada del usuario
        
        Args:
            user_input: Entrada del usuario
            existing_analysis: Análisis previo de imagen
            
        Returns:
            Dict con detalles parseados
        """
        details = existing_analysis.copy()
        user_input_upper = user_input.upper()
        user_input_lower = user_input.lower()
        
        # Parsear modelo (año) - buscar números de 4 dígitos
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', user_input)
        if year_match:
            details["modelo"] = year_match.group()
        
        # Parsear marcas comunes
        marcas_comunes = ["toyota", "chevrolet", "ford", "renault", "nissan", "hyundai", "mazda", "kia"]
        for marca in marcas_comunes:
            if marca in user_input_lower and "marca" not in details:
                details["marca"] = marca.title()
                break
        
        # Intentar extracción LLM si faltan datos críticos
        if not details.get("marca") and len(user_input) > 10:
            try:
                llm_extraction = self._extract_vehicle_info_with_llm(user_input)
                details.update(llm_extraction)
            except:
                pass
        
        # Parsear clases de vehículo
        clases_vehiculo = {
            "automóvil": ["automóvil", "automovil", "carro", "sedan", "sedán"], 
            "camioneta": ["camioneta", "pickup", "suv", "4x4"],
            "motocicleta": ["moto", "motocicleta"]
        }
        for clase, keywords in clases_vehiculo.items():
            if any(keyword in user_input_lower for keyword in keywords) and "clase" not in details:
                details["clase"] = clase.title()
                break
        
        # Parsear línea (texto después de marca/modelo)
        lines = user_input.split('\n')
        for line in lines:
            line = line.strip()
            if any(word in line.upper() for word in ["LÍNEA", "LINEA", "REFERENCIA"]):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    details["linea"] = parts[1].strip()
        
        # Si no se encontró línea estructurada, verificar si usuario dice que no la conoce
        if "linea" not in details and len(user_input.strip()) > 0:
            # Detectar si usuario dice que no conoce la línea
            user_input_lower = user_input.lower()
            doesnt_know_line = any(phrase in user_input_lower for phrase in [
                "no sé", "no se", "no conozco", "no tengo idea", "no estoy seguro",
                "no lo sé", "no recuerdo", "desconozco", "no tengo esa información",
                "no la conozco", "no sé la línea", "no conozco la línea"
            ])
            
            if not doesnt_know_line:
                # Remover año si se encontró
                line_candidate = user_input
                if year_match:
                    line_candidate = line_candidate.replace(year_match.group(), "").strip()
                
                # Solo asignar si no es una expresión de desconocimiento
                if line_candidate and not any(phrase in line_candidate.lower() for phrase in ["no sé", "no conozco", "específica"]):
                    # EXTRACCIÓN INTELIGENTE de línea
                    extracted_line = self._extract_smart_line(line_candidate)
                    if extracted_line:
                        details["linea"] = extracted_line
                    else:
                        details["linea"] = line_candidate
        
        return details
    
    def _extract_smart_line(self, user_input: str) -> str:
        """
        Extrae línea de manera inteligente del input del usuario
        
        Ejemplos:
        "Linea TX y modelo 2013" → "TX"
        "es una XEI" → "XEI" 
        "línea expression" → "EXPRESSION"
        """
        user_lower = user_input.lower().strip()
        
        # Patterns para extraer líneas conocidas
        line_patterns = {
            # Toyota
            "tx": "TX - MT 2700CC 4X4",
            "xei": "XEI - MT 1800CC",
            # Renault
            "expression": "EXPRESSION - MT 1600CC AA",
            "dynamique": "DYNAMIQUE - MT 2000CC 4X4",
            # Chevrolet
            "gt": "GT [M300] - MT 1200CC 5P FE",
            "ls": "LS - MT 1400CC 4P AA AB",
            # Hyundai
            "prime": "PRIME - MT 1000CC CITY TAXI",
        }
        
        # Buscar patrones en el texto
        for pattern, full_line in line_patterns.items():
            if pattern in user_lower:
                self.logger.info(f"🎯 Línea inteligente detectada: '{pattern}' → '{full_line}'")
                return full_line
        
        # Si no encuentra patrones específicos, buscar palabras clave comunes
        import re
        # Extraer palabras que podrían ser líneas (evitar palabras comunes)
        words = re.findall(r'\b[A-Za-z]+\b', user_input)
        common_words = ['linea', 'línea', 'modelo', 'year', 'del', 'que', 'es', 'una', 'y', 'el', 'la']
        
        for word in words:
            if word.lower() not in common_words and len(word) >= 2:
                # Buscar si esta palabra coincide parcialmente con alguna línea conocida
                for pattern, full_line in line_patterns.items():
                    if word.lower() in pattern or pattern in word.lower():
                        self.logger.info(f"🎯 Match parcial: '{word}' → '{full_line}'")
                        return full_line
        
        return None
    
    def _request_missing_info(self, analysis_result: Dict) -> Dict[str, Any]:
        """Solicita información faltante del análisis de imagen"""
        detected = {k: v for k, v in analysis_result.items() if v != "NO_DETECTADO"}
        missing = [k for k, v in analysis_result.items() if v == "NO_DETECTADO"]
        
        response_parts = ["He analizado tu imagen y he detectado:"]
        
        if detected:
            for key, value in detected.items():
                response_parts.append(f"• {key.title()}: {value}")
        
        if missing:
            response_parts.append(f"\nNo pude detectar claramente: {', '.join(missing)}")
            response_parts.append("Por favor, compárteme esta información junto con el modelo (año) y línea específica de tu vehículo.")
        
        return self.format_response(
            content="\n".join(response_parts),
            response_type="quotation_request",
            metadata={"analysis_result": analysis_result}
        )
    
    def _request_model_and_line(self, analysis_result: Dict) -> Dict[str, Any]:
        """Solicita modelo y línea después de análisis exitoso"""
        response = (
            f"Excelente! He analizado tu imagen y detecté:\n"
            f"• Marca: {analysis_result.get('marca', 'N/A')}\n"
            f"• Clase: {analysis_result.get('clase', 'N/A')}\n"
            f"• Color: {analysis_result.get('color', 'N/A')}\n\n"
            f"Ahora necesito que me proporciones:\n"
            f"• **Modelo (año)** de tu vehículo\n"
            f"• **Línea específica** (ej: 'Corolla XEI 1.8L', 'Logan Familier')\n\n"
            f"Puedes escribirlo en formato: 'Modelo: 2020, Línea: Corolla XEI 1.8L'"
        )
        
        return self.format_response(
            content=response,
            response_type="quotation_request",
            metadata={"analysis_result": analysis_result}
        )
    
    def _request_specific_details(self, missing_fields: List[str], current_details: Dict, attempt_count: int = 0) -> Dict[str, Any]:
        """Solicita campos específicos faltantes"""
        field_names = {
            "marca": "marca del vehículo",
            "modelo": "modelo (año)",
            "linea": "línea específica",
            "clase": "clase de vehículo",
            "color": "color"
        }
        
        missing_names = [field_names.get(field, field) for field in missing_fields]
        
        current_info = []
        for key, value in current_details.items():
            if value and value != "NO_DETECTADO":
                current_info.append(f"• {field_names.get(key, key).title()}: {value}")
        
        response_parts = []
        
        if current_info:
            response_parts.append("Información que tengo:")
            response_parts.extend(current_info)
            response_parts.append("")
        
        # Mensaje más amigable según el número de intentos
        if attempt_count == 0:
            response_parts.append(f"Necesito que me proporciones: **{', '.join(missing_names)}**")
        elif attempt_count == 1:
            response_parts.append(f"Aún necesito: **{', '.join(missing_names)}**")
            response_parts.append("")
            response_parts.append("💡 *Si no conoces algún dato específico, puedes decirme 'no sé' y procederé con una cotización estimada.*")
        else:
            response_parts.append("🤔 Parece que te falta información específica del vehículo.")
            response_parts.append("")
            response_parts.append("💡 **¿Prefieres que genere una cotización estimada con los datos disponibles?**")
            response_parts.append("Solo responde 'sí' o 'no sé' y procederé con valores aproximados.")
        
        return self.format_response(
            content="\n".join(response_parts),
            response_type="quotation_request"
        )
    
    def _vehicle_not_insurable_response(self, vehicle_details: Dict) -> Dict[str, Any]:
        """Respuesta cuando el vehículo no es asegurable"""
        response = (
            f"Lo siento, pero según nuestro catálogo actual, el vehículo "
            f"{vehicle_details.get('marca', '')} {vehicle_details.get('modelo', '')} "
            f"{vehicle_details.get('linea', '')} no está disponible para asegurar "
            f"en este momento.\n\n"
            f"Te voy a conectar con un asesor especializado que puede:\n"
            f"• Verificar si hay alternativas disponibles\n"
            f"• Revisar si hay actualizaciones en nuestro catálogo\n"
            f"• Ofrecerte opciones para vehículos similares"
        )
        
        return self.format_response(
            content=response,
            response_type="not_insurable",
            metadata={"vehicle_details": vehicle_details}
        )
    
    def _format_quotation_response(self, quotation_result: Dict) -> Dict[str, Any]:
        """Formatea la respuesta de cotización para el usuario"""
        vehicle_info = quotation_result["vehicle_info"]
        quotations = quotation_result["quotations"]
        
        response_parts = [
            f"🚗 **Cotización para tu {vehicle_info['marca']} {vehicle_info['modelo']}**",
            f"Línea: {vehicle_info['linea']}",
            f"Clase: {vehicle_info['clase']} | Color: {vehicle_info['color']}",
            ""
        ]
        
        if quotation_result.get("color_surcharge_applied"):
            response_parts.append("*Se aplicó recargo del 10% por color rojo*")
            response_parts.append("")
        
        response_parts.append("**Planes disponibles:**")
        response_parts.append("")
        
        for plan_name, plan_data in quotations.items():
            prima_anual = f"${plan_data['prima_anual']:,.0f}"
            prima_mensual = f"${plan_data['prima_mensual']:,.0f}"
            
            response_parts.extend([
                f"**{plan_name}**",
                f"• Prima anual: {prima_anual}",
                f"• Prima mensual: {prima_mensual}",
                ""
            ])
        
        response_parts.extend([
            "¿Te interesa alguno de estos planes? Puedo darte más detalles sobre las coberturas o proceder con la expedición de tu póliza.",
            "",
            "También puedes solicitar hablar con un asesor para aclarar cualquier duda."
        ])
        
        return self.format_response(
            content="\n".join(response_parts),
            response_type="quotation_result",
            metadata={
                "quotation_data": quotation_result,
                "plans_count": len(quotations)
            }
        )
    
    def get_quotation_summary(self, state: AgentState) -> Dict[str, Any]:
        """Genera resumen de cotizaciones en la sesión"""
        agent_state = self.load_agent_state(state.session_id) or {}
        current_quotation = state.context_data.get("current_quotation")
        
        return {
            "has_active_quotation": bool(current_quotation),
            "quotation_id": state.context_data.get("quotation_id"),
            "vehicle_details": agent_state.get("vehicle_details"),
            "plans_quoted": agent_state.get("plans_quoted", []),
            "quotation_state": state.context_data.get("quotation_state")
        }
    
    def _extract_vehicle_info_with_llm(self, user_input: str) -> Dict[str, str]:
        """Extrae información del vehículo usando LLM para entender texto libre"""
        try:
            system_prompt = """Eres un experto en extraer información de vehículos. 
Tu tarea es identificar marca, modelo/año, línea, clase y color de la descripción del usuario.

IMPORTANTE:
- Devuelve SOLO los campos que puedas identificar con certeza
- Para marca: Toyota, Chevrolet, Renault, Ford, Nissan, Hyundai, etc.
- Para modelo: solo el año (ej: 2020, 2018, 2019)
- Para clase: Automóvil, Camioneta, Motocicleta
- Para línea: nombre específico del modelo (Corolla, Sandero, Onix, etc.)
- Para color: Blanco, Negro, Gris, Rojo, etc.

Responde en formato JSON simple:
{"marca": "...", "modelo": "...", "linea": "...", "clase": "...", "color": "..."}"""

            user_prompt = f"Extrae información del vehículo de: '{user_input}'"
            
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
            
            # Filtrar campos vacíos o inválidos
            filtered_result = {}
            for key, value in result.items():
                if value and value.strip() and value.lower() not in ["n/a", "no", "ninguno", "desconocido"]:
                    filtered_result[key] = value.strip()
            
            self.logger.info(f"✅ LLM extrajo: {filtered_result} de '{user_input}'")
            return filtered_result
            
        except Exception as e:
            self.logger.warning(f"LLM extraction falló: {e}")
            return {}
