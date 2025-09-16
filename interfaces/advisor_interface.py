"""
Interfaz Asesor - Aplicación Streamlit para asesores humanos.
Permite gestionar casos escalados, ver conversaciones y continuar interacciones.
"""

import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

from agents.orchestrator import AgentOrchestrator
from utils.database import db_manager
from utils.config import config
from utils.logging_config import get_logger
from utils.ui_components import (
    apply_sura_theme, 
    render_sura_header, 
    render_modern_alert
)

logger = get_logger("advisor_interface")

class AdvisorInterface:
    """Interfaz principal para asesores humanos"""
    
    def __init__(self):
        self.logger = get_logger("advisor_interface")
        self.orchestrator = AgentOrchestrator()
        
        st.set_page_config(
            page_title="Seguros Sura - Panel Asesor",
            page_icon="👨‍💼",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        apply_sura_theme()
        
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Inicializa estado de la sesión Streamlit"""
        if "advisor_id" not in st.session_state:
            st.session_state.advisor_id = None
        
        if "selected_session" not in st.session_state:
            st.session_state.selected_session = None
        
        if "refresh_trigger" not in st.session_state:
            st.session_state.refresh_trigger = 0
        
        if "auto_refresh" not in st.session_state:
            st.session_state.auto_refresh = True
    
    def run(self):
        """Ejecuta la interfaz principal"""
        
        # Auto-refresh SIMPLIFICADO para detectar transferencias - 10 segundos
        if st.session_state.auto_refresh:
            import time
            
            # Verificar transferencias cada 10 segundos (más frecuente)
            if not hasattr(st.session_state, 'last_transfer_check'):
                st.session_state.last_transfer_check = time.time()
                st.session_state.notified_transfers = set()  # Set de IDs ya notificados
            
            if time.time() - st.session_state.last_transfer_check > 10:  # Cada 10 segundos
                st.session_state.last_transfer_check = time.time()
                
                try:
                    current_sessions = asyncio.run(self.orchestrator.get_active_sessions())
                    transferred_sessions = [s for s in current_sessions if s.get("status") == "transferred"]
                    
                    # Verificar si hay transferencias nuevas (por ID, no por conteo)
                    new_transfers = []
                    for session in transferred_sessions:
                        session_id = session.get("session_id")
                        if session_id not in st.session_state.notified_transfers:
                            new_transfers.append(session)
                            st.session_state.notified_transfers.add(session_id)
                    
                    # Si hay NUEVAS transferencias (no notificadas antes)
                    if new_transfers:
                        # Notificación MÚLTIPLE para asegurar que se vea
                        for i, session in enumerate(new_transfers):
                            st.toast(f"🚨 CASO TRANSFERIDO: {session.get('session_id', 'N/A')[:8]}...", icon="🚨")
                            
                        # Recargar interfaz
                        st.rerun()
                    
                    # TAMBIÉN verificar mensajes nuevos del cliente actual
                    if st.session_state.selected_session:
                        new_client_messages = self._check_for_client_messages(st.session_state.selected_session)
                        if new_client_messages:
                            st.rerun()
                
                except Exception as e:
                    self.logger.debug(f"Error verificando transferencias: {e}")
        
        # Header
        self._render_header()
        
        # Autenticación simple
        if not st.session_state.advisor_id:
            self._render_login()
            return
        
        # Layout principal
        self._render_main_layout()
    
    def _render_header(self):
        """Renderiza header corporativo para asesores"""
        advisor_name = st.session_state.advisor_id if st.session_state.advisor_id else "Asesor"
        render_sura_header(
            title=f"Panel de Asesor - {advisor_name}",
            subtitle="Gestión Profesional de Casos y Atención al Cliente",
            connection_status=True
        )
        
        # Mensaje de bienvenida integrado en el título - sin alerts que interfieran
    
    def _render_login(self):
        """Renderiza pantalla de login simple"""
        st.subheader("🔐 Acceso de Asesor")
        
        with st.form("login_form"):
            advisor_id = st.text_input("ID de Asesor:", placeholder="Ej: asesor001")
            password = st.text_input("Contraseña:", type="password", placeholder="password")
            
            if st.form_submit_button("Ingresar"):
                # Autenticación simple para demo
                if advisor_id and password == "admin123":
                    st.session_state.advisor_id = advisor_id
                    # NO mostrar success antes de rerun - causa problemas de timing
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Usa cualquier ID con contraseña 'admin123'")
    
    def _render_main_layout(self):
        """Renderiza layout principal del asesor"""
        
        with st.sidebar:
            st.markdown("### 🎛️ Panel de Control")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                auto_refresh = st.checkbox("Auto-actualización", value=st.session_state.auto_refresh)
            with col2:
                if st.button("🔄", help="Actualizar ahora"):
                    st.session_state.refresh_trigger += 1
                    st.rerun()
            
            if auto_refresh != st.session_state.auto_refresh:
                st.session_state.auto_refresh = auto_refresh
                if auto_refresh:
                    st.success("✅ Activado (15s)")
            else:
                    st.info("⏸️ Desactivado")
            
            try:
                active_sessions = asyncio.run(self.orchestrator.get_active_sessions())
                urgent_cases = len([s for s in active_sessions if s.get("status") == "transferred"])
                
                st.markdown("---")
                st.markdown("### 📊 Resumen Rápido")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total", len(active_sessions), help="Casos totales")
                with col2:
                    st.metric("Urgente", urgent_cases, delta="Requeridos" if urgent_cases > 0 else "Sin urgentes")
                
            except Exception as e:
                st.error(f"Error en resumen: {str(e)}")
            
            st.markdown("---")
            self._render_cases_sidebar()
        
        if st.session_state.selected_session:
            self._render_case_details()
        else:
            self._render_dashboard()
    
    def _render_cases_sidebar(self):
        """Renderiza sidebar con lista de casos"""
        st.subheader("Casos Activos")
        
        # Botón de refresh manual
        if st.button("Actualizar", use_container_width=True, type="primary"):
            st.session_state.refresh_trigger += 1
            st.rerun()
        
        # Obtener sesiones activas
        active_sessions = asyncio.run(self.orchestrator.get_active_sessions())
        
        if not active_sessions:
            st.info("No hay casos activos")
            return
        
        # NOTIFICACIONES DE TRANSFERENCIAS NUEVAS - MEJORADO
        transferred_sessions = [s for s in active_sessions if s.get("status") == "transferred"]
        human_active_sessions = [s for s in active_sessions if s.get("status") == "human_active"]
        
        if transferred_sessions:
            st.error(f"🚨 {len(transferred_sessions)} CASO(S) TRANSFERIDO(S) - ATENCIÓN INMEDIATA REQUERIDA")
            
            # Mostrar casos transferidos primero con estilo destacado
            for session in transferred_sessions:
                self._render_priority_case_card(session, priority="URGENT")
        
        if human_active_sessions:
            st.success(f"👨‍💼 {len(human_active_sessions)} caso(s) bajo tu atención")
            
            # Mostrar casos que ya estás atendiendo
            for session in human_active_sessions:
                self._render_priority_case_card(session, priority="ACTIVE")
        
        # Filtros
        st.subheader("🔍 Filtros")
        
        filter_type = st.selectbox(
            "Tipo de usuario:",
            ["Todos", "client", "advisor"]
        )
        
        # Filtrar sesiones PERO SIEMPRE mostrar transferencias
        if filter_type != "Todos":
            # Filtrar normalmente PERO incluir TODAS las transferencias
            filtered_sessions = [s for s in active_sessions if (
                s["user_type"] == filter_type or 
                s.get("status") in ["transferred", "human_active"]
            )]
        else:
            filtered_sessions = active_sessions
        
        # Mostrar casos
        st.subheader(f"📊 Casos ({len(filtered_sessions)})")
        
        for session in filtered_sessions:
            self._render_case_card(session)
    
    def _render_case_card(self, session: Dict[str, Any]):
        """Renderiza tarjeta de caso individual"""
        session_id = session["session_id"]
        
        # Obtener información adicional
        try:
            session_status = asyncio.run(self.orchestrator.get_session_status(session_id))
        except:
            session_status = {"exists": False}
        
        # Determinar prioridad visual
        if session_status.get("exists"):
            agent_states = session_status.get("agent_states", {})
            has_escalation = any("escalation" in str(state) for state in agent_states.values())
            priority_color = "🔴" if has_escalation else "🟡"
        else:
            priority_color = "⚪"
        
        # Información del caso
        updated_time = self._format_datetime(session["updated_at"])
        
        with st.container():
            st.markdown(f"""
            **{priority_color} Caso: {session_id[:8]}...**  
            Tipo: {session["user_type"]}  
            Actualizado: {updated_time}  
            Estado: {session.get("status", "active")}
            """)
            
            if st.button(f"Ver Caso", key=f"select_{session_id}"):
                st.session_state.selected_session = session_id
                st.rerun()
            
            st.markdown("---")
    
    def _render_priority_case_card(self, session: Dict[str, Any], priority: str = "HIGH"):
        """Renderiza tarjeta de caso con información completa"""
        session_id = session["session_id"]
        
        # Color y estilo según prioridad
        if priority == "URGENT":
            border_color = "#dc3545"  # Rojo urgente
            bg_color = "#f8d7da"
            icon = "🚨"
            button_text = "🔥 ATENDER URGENTE"
        elif priority == "ACTIVE":
            border_color = "#198754"  # Verde activo
            bg_color = "#d1e7dd"
            icon = "👨‍💼"
            button_text = "📋 Continuar Caso"
        else:
            border_color = "#ffc107"  # Amarillo
            bg_color = "#fff3cd"
            icon = "⚠️"
            button_text = "📝 Ver Caso"
        
        # Obtener información adicional del caso
        try:
            case_info = asyncio.run(self.orchestrator.get_session_status(session_id))
            agent_states = case_info.get("agent_states", {})
            
            # Detectar tipo de proceso
            if "quotation" in agent_states:
                process_type = "🚗 Cotización en proceso"
            elif "expedition" in agent_states:
                process_type = "📋 Expedición en proceso"
            else:
                process_type = "💬 Consulta general"
        except:
            process_type = "💬 Consulta"
        
        # Información del caso
        updated_time = self._format_datetime(session["updated_at"])
        
        # Contenedor con información completa
        st.markdown(f"""
        <div style='border-left: 6px solid {border_color}; padding: 15px; margin: 10px 0; background-color: {bg_color}; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <strong>{icon} {session_id[:8]}...</strong><br>
        <strong>Proceso:</strong> {process_type}<br>
        <strong>Tipo:</strong> {session["user_type"]}<br>
        <strong>Actualizado:</strong> {updated_time}<br>
        <strong>Estado:</strong> <span style='color: {border_color}; font-weight: bold;'>{session.get("status", "active").upper()}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón para atender caso
        if st.button(button_text, key=f"priority_{session_id}_{priority}", use_container_width=True):
            st.session_state.selected_session = session_id
            st.rerun()
    
    def _render_dashboard(self):
        """Renderiza dashboard profesional"""
        st.title("Dashboard de Asesor")
        
        # Métricas generales empresariales
        
        try:
            active_sessions = asyncio.run(self.orchestrator.get_active_sessions())
            system_health = self.orchestrator.get_system_health()
            
            # Preparar métricas empresariales
            total_cases = len(active_sessions)
            escalated_count = len([s for s in active_sessions if s.get("status") == "transferred"])
            client_sessions = len([s for s in active_sessions if s["user_type"] == "client"])
            system_healthy = system_health.get("orchestrator") == "healthy"
            
            # Métricas con Streamlit nativo (más confiable)
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Casos Activos",
                    value=str(total_cases),
                    delta=f"+{len([s for s in active_sessions[-5:]])} recientes" if total_cases > 0 else "Sin casos"
                )
            
            with col2:
                st.metric(
                    label="Casos Escalados", 
                    value=str(escalated_count),
                    delta="Requiere atención" if escalated_count > 0 else "Sin escalados"
                )
            
            with col3:
                st.metric(
                    label="Clientes Activos",
                    value=str(client_sessions), 
                    delta="En sesión" if client_sessions > 0 else "Sin clientes"
                )
            
            with col4:
                st.metric(
                    label="Estado Sistema",
                    value="Operativo" if system_healthy else "Error",
                    delta="100% disponible" if system_healthy else "Revisar servicios"
                )
        
        except Exception as e:
            st.error(f"Error cargando métricas: {str(e)}")
        
        # Estado del sistema
        st.subheader("Estado del Sistema")
        
        try:
            health = self.orchestrator.get_system_health()
            self._render_system_health(health)
        except Exception as e:
            st.error(f"Error obteniendo estado del sistema: {str(e)}")
        
        # Sección con estadísticas y actividad
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 Estadísticas de Uso")
            self._render_usage_statistics()
        
        with col2:
            st.subheader("📋 Actividad Reciente")
            self._render_recent_activity_table()
    
    def _render_system_health(self, health: Dict[str, Any]):
        """Renderiza estado de salud del sistema organizado"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🎯 Núcleo**")
            # Orquestador
            orchestrator_status = health.get("orchestrator", "unknown")
            color = "🟢" if orchestrator_status == "healthy" else "🔴"
            st.write(f"{color} Orquestador: {orchestrator_status}")
            
            # Base de datos
            db_status = health.get("database", "unknown")
            color = "🟢" if db_status == "healthy" else "🔴"
            st.write(f"{color} Base de Datos: {db_status}")
        
        with col2:
            st.markdown("**🤖 Agentes**")
            agents = health.get("agents", {})
            if agents:
                for agent, status in agents.items():
                    color = "🟢" if status == "healthy" else "🔴"
                    st.write(f"{color} {agent.title()}")
            else:
                st.write("🟡 Sin datos")
        
        with col3:
            st.markdown("**⚙️ Servicios**")
            services = health.get("services", {})
            if services:
                for service, status in services.items():
                    color = "🟢" if status == "healthy" else "🔴"
                    st.write(f"{color} {service.upper()}")
            else:
                st.write("🟡 Sin datos")
    
    def _render_usage_statistics(self):
        """Renderiza estadísticas de uso con gráficos"""
        try:
            active_sessions = asyncio.run(self.orchestrator.get_active_sessions())
            
            # Estadísticas por tipo de proceso
            process_counts = {}
            status_counts = {}
            
            for session in active_sessions:
                # Contar por tipo de proceso (si existe)
                process = session.get("current_process", "Consulta general")
                process_counts[process] = process_counts.get(process, 0) + 1
                
                # Contar por estado
                status = session.get("status", "active")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Gráfico de barras de procesos
            if process_counts:
                st.markdown("**Tipos de Proceso:**")
                for process, count in process_counts.items():
                    percentage = (count / len(active_sessions)) * 100
                    st.progress(percentage / 100, text=f"{process}: {count} ({percentage:.1f}%)")
            
            # Métricas adicionales
            st.markdown("**Resumen:**")
            total_transferred = len([s for s in active_sessions if s.get("status") == "transferred"])
            resolution_rate = ((len(active_sessions) - total_transferred) / len(active_sessions) * 100) if active_sessions else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tasa Resolución", f"{resolution_rate:.1f}%")
            with col2:
                st.metric("Promedio/Hora", f"{len(active_sessions)//24 if active_sessions else 0}")
                
        except Exception as e:
            st.error(f"Error en estadísticas: {str(e)}")
    
    def _render_recent_activity_table(self):
        """Renderiza tabla de actividad reciente compacta"""
        try:
            recent_sessions = asyncio.run(self.orchestrator.get_active_sessions())
            
            if recent_sessions:
                # Mostrar solo los últimos 8 para que quepa bien
                df_data = []
                for session in recent_sessions[-8:]:
                    df_data.append({
                        "ID": session["session_id"][:6] + "...",
                        "Tipo": session["user_type"],
                        "Estado": session["status"],
                        "Hora": self._format_datetime(session["updated_at"])[:5]  # Solo HH:MM
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, height=280)
            else:
                st.info("Sin actividad reciente")
        
        except Exception as e:
            st.error(f"Error en actividad: {str(e)}")
    
    def _render_case_details(self):
        """Renderiza detalles de caso seleccionado"""
        session_id = st.session_state.selected_session
        
        # Header del caso
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(f"📁 Caso: {session_id}")
        
        with col2:
            if st.button("⬅️ Volver", use_container_width=True):
                st.session_state.selected_session = None
                st.rerun()
        
        # Obtener información del caso
        try:
            session_status = asyncio.run(self.orchestrator.get_session_status(session_id))
            
            if not session_status.get("exists"):
                st.error("Caso no encontrado")
                return
            
            # Tabs del caso
            tab1, tab2, tab3, tab4 = st.tabs(["💬 Conversación", "📊 Resumen", "🔧 Acciones", "📋 Estado"])
            
            with tab1:
                self._render_conversation_tab(session_id, session_status)
            
            with tab2:
                self._render_summary_tab(session_status)
            
            with tab3:
                self._render_actions_tab(session_id, session_status)
            
            with tab4:
                self._render_status_tab(session_status)
        
        except Exception as e:
            st.error(f"Error cargando caso: {str(e)}")
    
    def _render_conversation_tab(self, session_id: str, session_status: Dict[str, Any]):
        """Renderiza tab de conversación"""
        
        # Obtener historial completo
        try:
            history = db_manager.get_conversation_history(session_id)
            
            if not history:
                st.info("No hay historial de conversación")
                return
            
            # Mostrar conversación
            st.subheader("💬 Historial de Conversación")
            
            for message in history:
                self._render_message_for_advisor(message)
            
            # INFORMACIÓN DE COTIZACIÓN/EXPEDICIÓN SI APLICA
            self._render_process_info(session_id)
            
            # Área para responder como asesor
            st.subheader("✏️ Responder como Asesor")
            
            with st.form("advisor_response_form"):
                advisor_response = st.text_area(
                    "Tu respuesta:",
                    placeholder="Escribe tu respuesta al cliente...",
                    height=100
                )
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.form_submit_button("📤 Enviar Respuesta"):
                        if advisor_response.strip():
                            self._send_advisor_response(session_id, advisor_response.strip())
                
                with col2:
                    if st.form_submit_button("🤖 Devolver a IA"):
                        self._return_to_ai(session_id)
                
                with col3:
                    if st.form_submit_button("✅ Cerrar Caso"):
                        self._close_case(session_id)
        
        except Exception as e:
            st.error(f"Error cargando conversación: {str(e)}")
    
    def _render_message_for_advisor(self, message):
        """Renderiza mensaje para vista de asesor"""
        role_icon = "👤" if message.agent_type == "user" else "🤖"
        
        if message.agent_type == "user":
            st.markdown(f"""
            <div style='background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                <strong>{role_icon} Cliente ({message.timestamp.strftime('%H:%M')})</strong><br>
                {message.content}
            </div>
            """, unsafe_allow_html=True)
        elif message.agent_type == "human_advisor":
            st.markdown(f"""
            <div style='background-color: #fff3e0; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                <strong>👨‍💼 Asesor ({message.timestamp.strftime('%H:%M')})</strong><br>
                {message.content}
            </div>
            """, unsafe_allow_html=True)
        else:
            agent_name = message.agent_type.replace("_", " ").title()
            st.markdown(f"""
            <div style='background-color: #f1f8e9; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                <strong>{role_icon} {agent_name} ({message.timestamp.strftime('%H:%M')})</strong><br>
                {message.content}
            </div>
            """, unsafe_allow_html=True)
    
    def _render_summary_tab(self, session_status: Dict[str, Any]):
        """Renderiza tab de resumen"""
        st.subheader("📊 Resumen del Caso")
        
        # Información básica
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Información General:**")
            st.write(f"• **ID:** {session_status['session_id']}")
            st.write(f"• **Tipo:** {session_status['user_type']}")
            st.write(f"• **Estado:** {session_status['status']}")
            st.write(f"• **Mensajes:** {session_status['message_count']}")
        
        with col2:
            st.write("**Tiempos:**")
            st.write(f"• **Creado:** {self._format_datetime(session_status['created_at'])}")
            st.write(f"• **Actualizado:** {self._format_datetime(session_status['updated_at'])}")
        
        # Estados de agentes
        agent_states = session_status.get("agent_states", {})
        
        if agent_states:
            st.subheader("🤖 Estados de Agentes")
            
            for agent, state in agent_states.items():
                with st.expander(f"Agente: {agent.replace('_', ' ').title()}"):
                    st.json(state)
        
        # Últimos mensajes
        last_messages = session_status.get("last_messages", [])
        
        if last_messages:
            st.subheader("💬 Últimos Mensajes")
            
            for msg in last_messages:
                st.write(f"**{msg['agent']}** ({self._format_datetime(msg['timestamp'])}): {msg['content']}")
    
    def _render_actions_tab(self, session_id: str, session_status: Dict[str, Any]):
        """Renderiza tab de acciones"""
        st.subheader("🔧 Acciones Disponibles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Gestión de Caso:**")
            
            if st.button("🔄 Reactivar Conversación"):
                self._reactivate_session(session_id)
            
            if st.button("📧 Enviar Email de Seguimiento"):
                st.info("Funcionalidad de email pendiente de implementación")
            
            if st.button("📞 Programar Llamada"):
                st.info("Funcionalidad de programación pendiente de implementación")
        
        with col2:
            st.write("**Estado de Sesión:**")
            
            new_status = st.selectbox(
                "Cambiar estado:",
                ["active", "transferred", "completed", "cancelled"]
            )
            
            if st.button("💾 Actualizar Estado"):
                self._update_session_status(session_id, new_status)
        
        # Notas del asesor
        st.subheader("📝 Notas del Asesor")
        
        with st.form("advisor_notes_form"):
            notes = st.text_area(
                "Agregar nota:",
                placeholder="Notas internas sobre el caso...",
                height=100
            )
            
            if st.form_submit_button("💾 Guardar Nota"):
                if notes.strip():
                    self._save_advisor_note(session_id, notes.strip())
    
    def _render_status_tab(self, session_status: Dict[str, Any]):
        """Renderiza tab de estado técnico"""
        st.subheader("📋 Estado Técnico")
        
        # Mostrar JSON completo del estado
        st.json(session_status)
    
    def _send_advisor_response(self, session_id: str, response: str):
        """Envía respuesta del asesor al cliente CON CONTROL PROFESIONAL"""
        try:
            # Marcar sesión como atendida por humano
            db_manager.update_session_status(session_id, "human_active")
            
            # Agregar mensaje a la base de datos como respuesta de asesor humano
            db_manager.add_message(
                session_id=session_id,
                agent_type="human_advisor",
                content=response,
                metadata={
                    "advisor_id": st.session_state.advisor_id,
                    "response_type": "human_advisor",
                    "source": "advisor_panel",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Actualizar metadata de sesión (método disponible)
            try:
                current_metadata = db_manager.get_session_status(session_id)
                if current_metadata:
                    metadata = current_metadata.get("metadata", {})
                    metadata.update({
                        "advisor_active": True,
                        "last_advisor_response": datetime.now().isoformat(),
                        "client_waiting": False
                    })
            except Exception as meta_error:
                self.logger.warning(f"No se pudo actualizar metadata: {meta_error}")
            
            st.success("✅ Respuesta enviada al cliente exitosamente")
            st.info("🔄 **Sesión ahora bajo control humano** - El asistente AI está pausado")
            st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error enviando respuesta: {str(e)}")
    
    def _close_case(self, session_id: str):
        """Cierra un caso y devuelve control al asistente PROFESIONALMENTE"""
        try:
            # Devolver control al asistente AI
            db_manager.update_session_status(session_id, "active")
            
            # Limpiar metadata de control humano (método simplificado)
            try:
                # Solo marcar como cerrado en los metadatos del mensaje
                pass  # La metadata se maneja en el mensaje automático
            except Exception as meta_error:
                self.logger.warning(f"No se pudo limpiar metadata: {meta_error}")
            
            # Enviar mensaje automático al cliente
            db_manager.add_message(
                session_id=session_id,
                agent_type="human_advisor",
                content="Gracias por contactarnos. Tu caso ha sido resuelto. El asistente inteligente puede continuar ayudándote con otras consultas.",
                metadata={
                    "advisor_id": st.session_state.advisor_id,
                    "response_type": "case_closure",
                    "automated": True
                }
            )
            
            st.success("✅ Caso cerrado exitosamente")
            st.info("🤖 **Control devuelto al asistente AI** - El cliente puede continuar normalmente")
            st.session_state.selected_session = None
            st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error cerrando caso: {str(e)}")
    
    def _reactivate_session(self, session_id: str):
        """Reactiva una sesión para que pueda seguir con el agente"""
        try:
            db_manager.update_session_status(session_id, "active")
            st.success("Sesión reactivada - el cliente puede continuar con el asistente")
        
        except Exception as e:
            st.error(f"Error reactivando sesión: {str(e)}")
    
    def _update_session_status(self, session_id: str, new_status: str):
        """Actualiza estado de sesión"""
        try:
            db_manager.update_session_status(session_id, new_status)
            st.success(f"Estado actualizado a: {new_status}")
            st.rerun()
        
        except Exception as e:
            st.error(f"Error actualizando estado: {str(e)}")
    
    def _save_advisor_note(self, session_id: str, note: str):
        """Guarda nota del asesor"""
        try:
            db_manager.add_message(
                session_id=session_id,
                agent_type="advisor_note",
                content=note,
                metadata={
                    "advisor_id": st.session_state.advisor_id,
                    "note_type": "internal",
                    "source": "advisor_panel"
                }
            )
            
            st.success("Nota guardada")
            st.rerun()
        
        except Exception as e:
            st.error(f"Error guardando nota: {str(e)}")
    
    def _render_process_info(self, session_id: str):
        """Renderiza información de procesos activos (cotización/expedición)"""
        try:
            # Obtener estados de agentes
            quotation_state = db_manager.get_agent_state(session_id, "quotation")
            expedition_state = db_manager.get_agent_state(session_id, "expedition")
            
            if quotation_state:
                st.subheader("🚗 Información de Cotización")
                
                with st.expander("Ver detalles de cotización", expanded=True):
                    if quotation_state.get("vehicle_details"):
                        vehicle = quotation_state["vehicle_details"]
                        st.write(f"**Vehículo:** {vehicle.get('marca', 'N/A')} {vehicle.get('modelo', 'N/A')} {vehicle.get('linea', 'N/A')}")
                        st.write(f"**Clase:** {vehicle.get('clase', 'N/A')} | **Color:** {vehicle.get('color', 'N/A')}")
                    
                    if quotation_state.get("plans_quoted"):
                        st.write(f"**Planes cotizados:** {', '.join(quotation_state['plans_quoted'])}")
                    
                    quotation_state_value = quotation_state.get("quotation_state", "N/A")
                    st.write(f"**Estado:** {quotation_state_value}")
                    
                    # Botón para continuar cotización
                    if st.button("🔄 Continuar Cotización como IA"):
                        self._continue_quotation_as_ai(session_id)
            
            if expedition_state:
                st.subheader("📋 Información de Expedición")
                
                with st.expander("Ver detalles de expedición", expanded=True):
                    st.write(f"**Estado:** {expedition_state.get('expedition_state', 'N/A')}")
                    
                    if expedition_state.get("selected_plan"):
                        st.write(f"**Plan seleccionado:** {expedition_state['selected_plan']}")
                    
                    if expedition_state.get("client_data"):
                        st.write("**Datos del cliente:** Disponibles")
                        client_data = expedition_state["client_data"]
                        for key, value in client_data.items():
                            st.write(f"• **{key}:** {value}")
                    else:
                        st.write("**Datos del cliente:** Pendientes")
                    
                    # Botones de acción para expedición
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🚀 Continuar Expedición como IA", key=f"continue_expedition_{session_id}"):
                            self._continue_expedition_as_ai(session_id)
                    with col2:
                        if st.button("✅ Confirmar Expedición Manual", key=f"manual_expedition_{session_id}"):
                            self._confirm_manual_expedition(session_id)
        
        except Exception as e:
            st.warning(f"No se pudo cargar información de procesos: {str(e)}")
    
    def _return_to_ai(self, session_id: str):
        """Devuelve el control al asistente IA"""
        try:
            db_manager.update_session_status(session_id, "active")
            
            # Mensaje automático al cliente
            db_manager.add_message(
                session_id=session_id,
                agent_type="human_advisor",
                content="Perfecto, he resuelto tu consulta. El asistente inteligente puede continuar ayudándote con otras preguntas.",
                metadata={
                    "advisor_id": st.session_state.advisor_id,
                    "response_type": "handoff_to_ai",
                    "automated": True
                }
            )
            
            st.success("✅ Control devuelto al asistente IA")
            st.rerun()
        
        except Exception as e:
            st.error(f"Error devolviendo control: {str(e)}")
    
    def _continue_quotation_as_ai(self, session_id: str):
        """Permite al asesor activar que la IA continúe con la cotización"""
        try:
            # Marcar sesión para que IA continúe cotización
            db_manager.add_message(
                session_id=session_id,
                agent_type="human_advisor",
                content="He revisado tu solicitud de cotización. Te ayudo a completar el proceso ahora.",
                metadata={
                    "advisor_id": st.session_state.advisor_id,
                    "action": "continue_quotation",
                    "trigger_ai": True
                }
            )
            
            # Devolver control a IA específicamente para cotización
            db_manager.update_session_status(session_id, "active")
            
            st.success("✅ IA continuará con la cotización")
            st.rerun()
        
        except Exception as e:
            st.error(f"Error activando cotización: {str(e)}")
    
    def _continue_expedition_as_ai(self, session_id: str):
        """Permite al asesor activar que la IA continúe con la expedición"""
        try:
            # Marcar sesión para que IA continúe expedición
            db_manager.add_message(
                session_id=session_id,
                agent_type="human_advisor",
                content="He revisado tus datos. Procedo a completar la expedición de tu póliza.",
                metadata={
                    "advisor_id": st.session_state.advisor_id,
                    "action": "continue_expedition",
                    "trigger_ai": True
                }
            )
            
            # Cambiar estado a activo para que IA tome control
            db_manager.update_session_status(session_id, "active")
            
            st.success("✅ IA continuará con la expedición")
            st.rerun()
        
        except Exception as e:
            st.error(f"Error activando expedición: {str(e)}")
    
    def _confirm_manual_expedition(self, session_id: str):
        """Permite al asesor confirmar expedición manualmente"""
        try:
            # Recuperar información de expedición
            expedition_state = db_manager.get_agent_state(session_id, "expedition")
            quotation_state = db_manager.get_agent_state(session_id, "quotation")
            
            if not expedition_state or not quotation_state:
                st.error("❌ No se encontró información completa para expedición")
                return
            
            # Simulación de expedición manual
            policy_number = f"POL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Mensaje de confirmación al cliente
            db_manager.add_message(
                session_id=session_id,
                agent_type="human_advisor",
                content=f"🎉 ¡Felicitaciones! Tu póliza ha sido expedida exitosamente.\n\n**Número de póliza:** {policy_number}\n\nRecibirás los documentos en tu correo electrónico en los próximos minutos.",
                metadata={
                    "advisor_id": st.session_state.advisor_id,
                    "action": "manual_expedition",
                    "policy_number": policy_number
                }
            )
            
            # Cerrar la sesión como completada
            db_manager.update_session_status(session_id, "completed")
            
            st.success(f"✅ Póliza expedida manualmente: {policy_number}")
            st.balloons()
            st.rerun()
        
        except Exception as e:
            st.error(f"Error en expedición manual: {str(e)}")
    
    def _check_for_client_messages(self, session_id: str) -> bool:
        """
        Verificación ESPECÍFICA para mensajes nuevos del cliente
        Para sincronización asesor ← cliente
        """
        try:
            # Obtener historial completo de la sesión
            db_history = db_manager.get_conversation_history(session_id)
            
            # Filtrar SOLO mensajes del cliente (user)
            client_messages_db = [
                msg for msg in db_history 
                if msg.agent_type == "user"
            ]
            
            # Obtener mensajes del cliente en el contexto actual
            if not hasattr(st.session_state, f'client_messages_{session_id}'):
                st.session_state.__dict__[f'client_messages_{session_id}'] = []
            
            current_client_messages = st.session_state.__dict__[f'client_messages_{session_id}']
            
            # Si hay más mensajes del cliente en BD que en el contexto
            if len(client_messages_db) > len(current_client_messages):
                # Actualizar el contador
                st.session_state.__dict__[f'client_messages_{session_id}'] = client_messages_db
                
                # Mostrar notificación discreta
                new_count = len(client_messages_db) - len(current_client_messages)
                st.toast(f"💬 {new_count} nuevo(s) mensaje(s) del cliente", icon="💬")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando mensajes del cliente: {str(e)}")
            return False
    
    def _format_datetime(self, datetime_str: str) -> str:
        """Formatea datetime para display"""
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y %H:%M")
        except:
            return datetime_str

def main():
    """Función principal"""
    try:
        interface = AdvisorInterface()
        interface.run()
    except Exception as e:
        logger.error(f"Error en interfaz asesor: {str(e)}")
        st.error("Error iniciando la aplicación. Por favor recarga la página.")

if __name__ == "__main__":
    main()