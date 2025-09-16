"""
Interfaz Cliente - Aplicación Streamlit para interacción con clientes.
Proporciona chat interactivo, carga de imágenes y visualización de cotizaciones.
"""

import streamlit as st
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import base64
from PIL import Image
import io

from agents.orchestrator import AgentOrchestrator
from services.rag_service import rag_service
from utils.config import config
from utils.logging_config import get_logger
from utils.database import db_manager
from utils.ui_components import (
    apply_sura_theme, 
    render_sura_header, 
    render_metric_card,
    render_status_badge, 
    render_modern_alert,
    render_chat_message,
    render_section_divider,
    render_status_indicator_professional
)

logger = get_logger("client_interface")

class ClientInterface:
    """Interfaz principal para clientes"""
    
    def __init__(self):
        self.logger = get_logger("client_interface")
        self.orchestrator = AgentOrchestrator()
        
        st.set_page_config(
            page_title="Seguros Sura - Asistente IA",
            page_icon="🛡️",
            layout="wide",
            initial_sidebar_state="auto"
        )
        
        apply_sura_theme()
        
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Inicializa estado de la sesión Streamlit"""
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "current_quotation" not in st.session_state:
            st.session_state.current_quotation = None
        
        if "user_context" not in st.session_state:
            st.session_state.user_context = {}
        
        if "system_initialized" not in st.session_state:
            st.session_state.system_initialized = False
        
        if "auto_refresh" not in st.session_state:
            st.session_state.auto_refresh = True
    
    def run(self):
        """Ejecuta la interfaz principal"""
        
        # SINCRONIZACIÓN AUTOMÁTICA - MEJORADA
        if st.session_state.auto_refresh:
            import time
            if not hasattr(st.session_state, 'last_auto_check'):
                st.session_state.last_auto_check = time.time()
            
            # Auto-check cada 3 segundos para mejor responsividad
            if time.time() - st.session_state.last_auto_check > 3:
                st.session_state.last_auto_check = time.time()
                # Verificación para mensajes del asesor
                new_advisor_messages = self._check_for_advisor_messages_only()
                if new_advisor_messages:
                    st.rerun()
                    
        # Auto-refresh independiente del checkbox (cada 10 segundos como fallback)
        import time
        if not hasattr(st.session_state, 'last_fallback_check'):
            st.session_state.last_fallback_check = time.time()
        
        if time.time() - st.session_state.last_fallback_check > 10:
            st.session_state.last_fallback_check = time.time()
            # Check menos frecuente como respaldo
            new_messages = self._check_for_advisor_messages_only()
            if new_messages:
                st.rerun()
            
        # AUTO-RERUN si es necesario (técnica profesional para forms)
        if st.session_state.get('should_rerun', False):
            st.session_state.should_rerun = False
            st.rerun()
        
        # Header
        self._render_header()
        
        # Inicializar sistema si es necesario
        if not st.session_state.system_initialized:
            self._initialize_system()
        
        # Layout principal
        col1, col2 = st.columns([3, 1])
        
        with col1:
            self._render_chat_interface()
        
        with col2:
            self._render_sidebar()
        
        # Footer
        self._render_footer()
    
    def _render_header(self):
        """Renderiza header corporativo moderno"""
        render_sura_header(
            title="Seguros Sura Colombia",
            subtitle="Asistente Corporativo para Seguros Vehiculares - Consultas, Cotizaciones y Expedición de Pólizas",
            connection_status=st.session_state.get('system_initialized', False)
        )
    
    def _initialize_system(self):
        """Inicializa sistemas necesarios"""
        with st.spinner("Inicializando sistema..."):
            try:
                # Inicializar RAG si es necesario
                rag_health = rag_service.health_check()
                
                if rag_health["vector_store_docs"] == 0:
                    st.info("Cargando base de conocimientos...")
                    rag_service.initialize_documents()
                
                # Verificar salud del sistema
                system_health = self.orchestrator.get_system_health()
                
                if system_health.get("orchestrator") == "healthy":
                    st.session_state.system_initialized = True
                    
                    # Crear sesión en la base de datos si no existe
                    try:
                        from utils.database import db_manager
                        session = db_manager.get_session(st.session_state.session_id)
                        if not session:
                            db_manager.create_session(
                                session_id=st.session_state.session_id,
                                user_type="client",
                                metadata={"initialized_at": datetime.now().isoformat()}
                            )
                    except Exception as e:
                        logger.error(f"Error creando sesión en BD: {str(e)}")
                    
                    # Mensaje de bienvenida
                    welcome_message = {
                        "role": "assistant",
                        "content": "¡Hola! Soy tu asistente de Seguros Sura. Puedo ayudarte con:\n\n• **Consultas** sobre planes y coberturas\n• **Cotizaciones** de seguros (puedes subir una foto de tu vehículo)\n• **Expedición** de pólizas\n\n¿En qué puedo ayudarte hoy?",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    st.session_state.messages.append(welcome_message)
                else:
                    st.error("Error inicializando sistema. Por favor recarga la página.")
                
            except Exception as e:
                self.logger.error(f"Error inicializando sistema: {str(e)}")
                st.error("Error inicializando sistema. Por favor verifica la configuración.")
    
    def _render_chat_interface(self):
        """Renderiza interfaz de chat principal"""
        st.subheader("💬 Conversación")
        
        # Contenedor de mensajes
        messages_container = st.container()
        
        with messages_container:
            for message in st.session_state.messages:
                self._render_message(message)
        
        # Input del usuario
        self._render_user_input()
    
    def _render_message(self, message: Dict[str, Any]):
        """Renderiza un mensaje individual con diseño profesional"""
        role = message["role"]
        content = message["content"]
        timestamp = message.get("timestamp", "")
        
        # Usar componente profesional de chat
        if timestamp:
            timestamp_str = self._format_timestamp(timestamp)
        else:
            timestamp_str = None
            
        render_chat_message(content, role, timestamp_str)
                
                # Mostrar información adicional si es cotización
        if role == "assistant" and self._is_quotation_message(message):
                    self._render_quotation_details(message)
    
    def _render_user_input(self):
        """Renderiza área de input del usuario"""
        
        # Opciones de entrada
        input_method = st.radio(
            "Método de entrada:",
            ["Texto", "Imagen + Texto"],
            horizontal=True
        )
        
        if input_method == "Texto":
            self._render_text_input()
        else:
            self._render_image_input()
    
    def _render_text_input(self):
        """Renderiza input de solo texto"""
        
        # Controles fuera del form para que funcionen
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            auto_sync = st.checkbox("Sync", value=st.session_state.auto_refresh, help="Sincronización automática")
            if auto_sync != st.session_state.auto_refresh:
                st.session_state.auto_refresh = auto_sync
                if auto_sync:
                    st.success("🔄 Sync activado")
                else:
                    st.info("⏸️ Sync desactivado")
                st.rerun()
        
        with col2:
            if st.button("Reiniciar", help="Nueva sesión"):
                self._start_new_session()
                
        with col3:
            if st.button("🔄", help="Sincronizar ahora"):
                new_messages = self._check_for_advisor_messages_only()
                if new_messages:
                    st.success("✅ Mensajes sincronizados")
                else:
                    st.info("📡 Sin mensajes nuevos")
                st.rerun()
        
        # Form solo para el input y envío
        with st.form("text_input_form", clear_on_submit=True):
            user_input = st.text_area(
                "Escribe tu mensaje:",
                placeholder="Ejemplo: ¿Qué cubre el Plan Autos Básico?",
                height=80
            )
            
            submit_button = st.form_submit_button("Enviar", type="primary", use_container_width=True)
            
            if submit_button and user_input.strip():
                self._process_user_input(user_input.strip())
    
    def _render_image_input(self):
        """Renderiza input con imagen y texto"""
        
        # Controles fuera del form para que funcionen (igual que texto)
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            auto_sync = st.checkbox("Sync", value=st.session_state.auto_refresh, help="Sincronización automática")
            if auto_sync != st.session_state.auto_refresh:
                st.session_state.auto_refresh = auto_sync
                if auto_sync:
                    st.success("🔄 Sync activado")
                else:
                    st.info("⏸️ Sync desactivado")
                st.rerun()
        
        with col2:
            if st.button("Reiniciar", help="Nueva sesión"):
                self._start_new_session()
                
        with col3:
            if st.button("🔄", help="Sincronizar ahora"):
                new_messages = self._check_for_advisor_messages_only()
                if new_messages:
                    st.success("✅ Mensajes sincronizados")
                else:
                    st.info("📡 Sin mensajes nuevos")
                st.rerun()
        
        # Form para imagen y texto
        with st.form("image_input_form", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "Sube una imagen de tu vehículo:",
                type=["jpg", "jpeg", "png"],
                help="Acepto imágenes JPG, JPEG y PNG"
            )
            
            user_input = st.text_area(
                "Información adicional (opcional):",
                placeholder="Ejemplo: Toyota Corolla 2020, línea XEI",
                height=80
            )
            
            submit_button = st.form_submit_button("Enviar", type="primary", use_container_width=True)
            
            if submit_button:
                if uploaded_file is not None:
                    self._process_image_input(uploaded_file, user_input.strip())
                    # AUTO-CAMBIAR a modo texto después de enviar imagen (fuera del form)
                    st.session_state.input_method = "Texto"
                    st.session_state.should_rerun = True
                else:
                    st.warning("Por favor sube una imagen para usar este método.")
    
    def _process_user_input(self, user_input: str, image_data: Optional[bytes] = None):
        """Procesa entrada del usuario"""
        try:
            from utils.database import db_manager
            
            # Agregar mensaje del usuario al chat
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            }

            if image_data:
                user_message["has_image"] = True

            st.session_state.messages.append(user_message)
            
            # NO guardar mensaje aquí - el orquestador lo hará
            # Evita duplicación en la BD

            # VERIFICAR estado de sesión COMPLETO
            session_data = db_manager.get_session_status(st.session_state.session_id)
            is_human_active = session_data and session_data.get("status") == "human_active"

            # Si hay asesor humano activo, NO procesar con asistente
            if is_human_active:
                # SOLO en este caso, guardar mensaje para que asesor lo vea
                db_manager.add_message(
                    session_id=st.session_state.session_id,
                    agent_type="user",
                    content=user_input,
                    metadata={"from_client": True, "has_image": bool(image_data), "human_session": True}
                )
                
                st.info("🧑‍💼 **Tu asesor humano está atendiendo tu consulta**")
                st.markdown("💬 *Tu mensaje ha sido enviado al asesor. Recibirás respuesta pronto.*")
                st.rerun()
                return
            
            # Preparar contexto
            context_data = st.session_state.user_context.copy()
            
            if image_data:
                context_data["has_image"] = True
                context_data["image_data"] = image_data
            
            # Procesar con orquestador
            with st.spinner("Procesando..."):
                response = asyncio.run(
                    self.orchestrator.process_user_input(
                        session_id=st.session_state.session_id,
                        user_input=user_input,
                        user_type="client",
                        context_data=context_data
                    )
                )
            
            # Procesar respuesta
            if response["success"]:
                assistant_message = {
                    "role": "assistant",
                    "content": response["content"],
                    "timestamp": response["timestamp"],
                    "agent": response["agent"],
                    "metadata": response.get("metadata", {})
                }
                
                st.session_state.messages.append(assistant_message)
                
                # Actualizar contexto si es necesario
                if "context" in response:
                    st.session_state.user_context.update(response["context"])
                
                # Manejar cotización si se generó
                if response.get("metadata", {}).get("quotation"):
                    st.session_state.current_quotation = response["metadata"]["quotation"]
                
                # Manejar escalamiento humano
                if response["metadata"].get("human_intervention_needed"):
                    self._handle_human_escalation(response)
            
            else:
                st.error(f"Error: {response.get('error', 'Error desconocido')}")
            
            # Rerun para actualizar interfaz
            st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error procesando entrada: {str(e)}")
            st.error("😅 **¡Ups!** Hubo un problema momentáneo. Reformula tu consulta o escribe 'hablar con asesor' para ayuda inmediata.")
    
    def _process_image_input(self, uploaded_file, user_input: str):
        """Procesa entrada con imagen SIN duplicación"""
        try:
            # Leer imagen
            image_bytes = uploaded_file.read()
            
            # Validar tamaño
            if len(image_bytes) > 10 * 1024 * 1024:  # 10MB
                st.warning("La imagen es muy grande. Por favor sube una imagen menor a 10MB.")
                return
            
            # Mostrar preview SOLO si no está ya en mensajes
            existing_images = [msg for msg in st.session_state.messages if msg.get("has_image")]
            if len(existing_images) == 0 or not any("[Imagen de vehículo subida]" in msg.get("content", "") for msg in existing_images[-2:]):
                image = Image.open(io.BytesIO(image_bytes))
                st.image(image, caption="Imagen subida", width=200)
                
                # Procesar SOLO una vez
                combined_input = f"[Imagen de vehículo subida] {user_input}" if user_input else "[Imagen de vehículo subida]"
                self._process_user_input(combined_input, image_bytes)
            
        except Exception as e:
            self.logger.error(f"Error procesando imagen: {str(e)}")
            st.error("Error procesando la imagen. Por favor intenta con otra imagen.")
    
    def _render_sidebar(self):
        """Renderiza sidebar compacta con información adicional"""
        render_section_divider("Información de Sesión")
        
        # Información de sesión compacta
        st.markdown(f"**ID:** `{st.session_state.session_id[:8]}...`")
        st.markdown(f"**Mensajes:** `{len(st.session_state.messages)}`")
        
        # Solo mostrar estado si auto-refresh está activado
        if st.session_state.auto_refresh:
            import time
            last_check = getattr(st.session_state, 'last_auto_check', time.time())
            seconds_ago = int(time.time() - last_check)
            render_modern_alert(f"🔄 Sync activo (último: {seconds_ago}s)", "success")
        
        # Cotización actual
        if st.session_state.current_quotation:
            self._render_quotation_summary()
        
        # Ejemplos de preguntas
        self._render_example_questions()
        
        # Contacto de emergencia
        self._render_emergency_contact()
    
    def _render_quotation_summary(self):
        """Renderiza resumen de cotización actual"""
        quotation = st.session_state.current_quotation
            
        if quotation and quotation.get("has_active_quotation") and quotation.get("vehicle_details"):
            with st.expander("🚗 Cotización Activa", expanded=True):
                st.success("Tienes una cotización activa")
                
                vehicle = quotation["vehicle_details"]
                st.write(f"**Vehículo:** {vehicle.get('marca', 'N/A')} {vehicle.get('modelo', 'N/A')}")
                
                if quotation.get("plans_quoted"):
                    st.write(f"**Planes:** {len(quotation['plans_quoted'])}")
                
                if st.button("Ver Detalles de Cotización"):
                    self._show_quotation_details()
    
    def _render_example_questions(self):
        """Renderiza preguntas de ejemplo"""
        with st.expander("❓ Preguntas Frecuentes", expanded=False):
            examples = [
                "¿Qué cubre el Plan Autos Básico?",
                "¿Cuál es el deducible para daños por hurto?",
                "¿Qué incluye la asistencia de pequeños eventos?",
                "Quiero cotizar mi vehículo",
                "¿En qué ciudades aplica la asistencia?"
            ]
            
            for example in examples:
                if st.button(f"💬 {example}", key=f"example_{hash(example)}"):
                    self._process_user_input(example)
    
    def _render_emergency_contact(self):
        """Renderiza información de contacto de emergencia"""
        with st.expander("🆘 Contacto Directo", expanded=False):
            st.markdown("""
            **Si necesitas ayuda inmediata:**
            
            📞 **Línea de Atención:**  
            018000 518000
            
            💬 **Chat Web:**  
            www.segurossura.com.co
            
            📧 **Email:**  
            atencion.cliente@sura.com.co
            
            🕐 **Horarios:**  
            Lunes a Viernes: 7:00 AM - 7:00 PM  
            Sábados: 8:00 AM - 4:00 PM
            """)
    
    def _is_quotation_message(self, message: Dict[str, Any]) -> bool:
        """Verifica si un mensaje contiene información de cotización"""
        content = message.get("content", "").lower()
        metadata = message.get("metadata", {})
        
        return (
            "cotización" in content or 
            "prima anual" in content or 
            "prima mensual" in content or
            metadata.get("quotation")
        )
    
    def _render_quotation_details(self, message: Dict[str, Any]):
        """Renderiza detalles de cotización en un mensaje"""
        if "plan" in message.get("content", "").lower():
            st.info("💡 **Tip:** Puedes proceder con la compra diciendo 'Quiero comprar el Plan X' o solicitar más información sobre las coberturas.")
    
    def _handle_human_escalation(self, response: Dict[str, Any]):
        """Maneja escalamiento a asesor humano"""
        st.warning("🔄 **Transferencia a Asesor Humano**")
        st.info("Tu conversación ha sido transferida a un asesor humano que se comunicará contigo pronto.")
        
        # Deshabilitar input temporalmente
        st.session_state.user_context["human_intervention_active"] = True
    
    def _start_new_session(self):
        """Inicia una nueva sesión"""
        # Limpiar estado
        for key in list(st.session_state.keys()):
            if key not in ["system_initialized"]:
                del st.session_state[key]
        
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.current_quotation = None
        st.session_state.user_context = {}
        st.session_state.auto_refresh = True
        
        st.rerun()
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """Formatea timestamp para display"""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
        except:
            return timestamp_str
    
    def _show_quotation_details(self):
        """Muestra detalles completos de cotización en modal"""
        st.info("Los detalles de cotización están disponibles en la conversación arriba.")
    
    def _check_for_new_messages(self) -> bool:
        """Verifica si hay mensajes nuevos del sistema (asesor humano Y agentes). Retorna True si hay nuevos mensajes"""
        try:
            from utils.database import db_manager
            
            # Obtener historial completo desde BD
            db_history = db_manager.get_conversation_history(st.session_state.session_id)
            
            # Contar mensajes actuales en Streamlit (excluyendo mensajes del usuario)
            current_system_messages = [
                msg for msg in st.session_state.messages 
                if msg.get("role") == "assistant"
            ]
            
            # Filtrar mensajes del sistema desde BD (NO incluir mensajes de usuario)
            db_system_messages = [
                msg for msg in db_history 
                if msg.agent_type != "user"  # Incluir ALL system messages: consultant, quotation, human_advisor, etc.
            ]
            
            # Verificar si hay mensajes nuevos (comparación más robusta)
            last_timestamp = None
            if current_system_messages:
                # Obtener timestamp del último mensaje del sistema en interfaz
                last_msg = current_system_messages[-1]
                last_timestamp = last_msg.get("timestamp") if hasattr(last_msg, 'get') else None
            
            # Filtrar mensajes más recientes que el último timestamp
            if last_timestamp:
                new_messages_db = [
                    msg for msg in db_system_messages 
                    if msg.timestamp.isoformat() > last_timestamp
                ]
            else:
                # Si no hay timestamp, usar diferencia de conteo
                if len(db_system_messages) > len(current_system_messages):
                    missing_count = len(db_system_messages) - len(current_system_messages)
                    new_messages_db = db_system_messages[-missing_count:]
                else:
                    new_messages_db = []
                
            # Si hay nuevos mensajes, procesarlos SIN DUPLICADOS
            if new_messages_db:
                for msg in new_messages_db:
                    # VERIFICAR si el mensaje ya existe en la interfaz (MEJORADO para todos los tipos)
                    msg_timestamp = msg.timestamp.isoformat()
                    msg_content = msg.content
                    
                    # Verificar duplicados por timestamp Y contenido (para TODOS los agentes)
                    msg_already_exists = any(
                        existing_msg.get("timestamp") == msg_timestamp and (
                            # Para mensajes de asesor humano
                            existing_msg.get("content", "").replace("👨‍💼 **Asesor:** ", "") == msg_content or
                            # Para mensajes de sistema/agentes
                            existing_msg.get("content", "") == msg_content
                        )
                        for existing_msg in st.session_state.messages
                    )
                    
                    if msg_already_exists:
                        continue  # Saltar mensaje duplicado
                    
                    # Formatear según el tipo de agente
                    if msg.agent_type == "human_advisor":
                        system_message = {
                            "role": "assistant",
                            "content": f"👨‍💼 **Asesor:** {msg.content}",
                            "timestamp": msg_timestamp,
                            "agent": "human_advisor",
                            "metadata": msg.metadata,
                            "from_advisor": True
                        }
                    else:
                        # Mensajes de agentes (consultant, quotation, etc.)
                        system_message = {
                            "role": "assistant",
                            "content": msg.content,
                            "timestamp": msg_timestamp,
                            "agent": msg.agent_type,
                            "metadata": msg.metadata,
                            "from_system": True
                        }
                    
                    st.session_state.messages.append(system_message)
                
                # Notificación visual profesional (solo para mensajes de asesor humano)
                advisor_count = len([msg for msg in new_messages_db if msg.agent_type == "human_advisor"])
                if advisor_count > 0:
                    st.success(f"💬 {advisor_count} nuevo(s) mensaje(s) de tu asesor")
                
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error en sincronización: {str(e)}")
            return False
    
    def _check_for_advisor_messages_only(self) -> bool:
        """
        Verificación ESPECÍFICA solo para mensajes del asesor humano
        NO incluye mensajes del orquestador (evita duplicados)
        """
        try:
            # Obtener SOLO mensajes del asesor humano desde la BD
            db_history = db_manager.get_conversation_history(st.session_state.session_id)
            
            # Filtrar ÚNICAMENTE mensajes del asesor humano
            advisor_messages_db = [
                msg for msg in db_history 
                if msg.agent_type == "human_advisor"
            ]
            
            # Obtener mensajes del asesor en la interfaz actual
            current_advisor_messages = [
                msg for msg in st.session_state.messages 
                if msg.get("agent") == "human_advisor" or msg.get("from_advisor", False)
            ]
            
            # Si hay más mensajes del asesor en BD
            if len(advisor_messages_db) > len(current_advisor_messages):
                missing_count = len(advisor_messages_db) - len(current_advisor_messages)
                new_advisor_messages = advisor_messages_db[-missing_count:]
                
                for msg in new_advisor_messages:
                    # Verificar que no esté duplicado
                    msg_timestamp = msg.timestamp.isoformat()
                    msg_already_exists = any(
                        existing_msg.get("timestamp") == msg_timestamp
                        for existing_msg in st.session_state.messages
                    )
                    
                    if not msg_already_exists:
                        # Agregar SOLO mensaje del asesor
                        advisor_message = {
                            "role": "assistant",
                            "content": f"👨‍💼 **Asesor:** {msg.content}",
                            "timestamp": msg_timestamp,
                            "agent": "human_advisor",
                            "metadata": msg.metadata,
                            "from_advisor": True
                        }
                        st.session_state.messages.append(advisor_message)
                
                if new_advisor_messages:
                    st.success(f"💬 {len(new_advisor_messages)} nuevo(s) mensaje(s) de tu asesor")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando mensajes del asesor: {str(e)}")
            return False
    
    def _render_footer(self):
        """Renderiza footer de la aplicación"""
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.8em;'>
            Seguros Sura Colombia - Asistente IA | Versión 1.0<br>
            Para soporte técnico: soporte.ia@sura.com.co
        </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal"""
    try:
        interface = ClientInterface()
        interface.run()
    except Exception as e:
        logger.error(f"Error en interfaz cliente: {str(e)}")
        st.error("Error iniciando la aplicación. Por favor recarga la página.")

if __name__ == "__main__":
    main()