"""
🎨 UI Components - Sistema de Diseño Seguros Sura
Componentes visuales modernos que se integran con Streamlit sin afectar funcionalidad
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime


def apply_sura_theme():
    """Aplica tema corporativo Seguros Sura sin romper funcionalidad"""
    
    sura_css = """
    <style>
    /* ========================================
       SISTEMA DE DISEÑO SEGUROS SURA 2025
       Paleta Oficial + Mejoras UX Modernas
    ======================================== */
    
    /* Variables Corporativas Seguros Sura */
    :root {
        /* Paleta Principal */
        --sura-blue-vivid: #2D6DF6;
        --sura-blue-primary: #0033A0;
        --sura-white: #FFFFFF;
        
        /* Paleta Complementaria */
        --sura-yellow: #E3E829;
        --sura-aqua: #00AEC7;
        --sura-gray: #888B8D;
        
        /* Tonos Neutros Complementarios */
        --sura-blue-light: #8A9CD3;
        --sura-yellow-light: #ECF0A1;
        --sura-aqua-light: #9BE1E9;
        --sura-blue-soft: #81B1FF;
        --sura-gray-light: #B4B4B5;
        
        /* Fondos Digitales */
        --sura-bg-1: #E5E9EA;
        --sura-bg-2: #F9FAE1;
        --sura-bg-3: #D5F6F8;
        --sura-bg-4: #DCEAFF;
        --sura-bg-5: #F8F8F8;
        
        /* Estados */
        --success: #00AEC7;
        --warning: #E3E829;
        --danger: #FF4757;
        --info: #2D6DF6;
    }
    
    /* Mejoras Globales de la App */
    .stApp {
        background: linear-gradient(135deg, var(--sura-bg-5) 0%, var(--sura-bg-4) 100%);
        font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    }
    
    /* Header Mejorado - Compacto */
    .main-header {
        background: linear-gradient(90deg, var(--sura-blue-primary), var(--sura-blue-vivid));
        color: var(--sura-white);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(0, 51, 160, 0.12);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .brand-section h1 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--sura-white);
    }
    
    .brand-section p {
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }
    
    .connection-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.1);
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .pulse-indicator {
        width: 8px;
        height: 8px;
        background: var(--success);
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.1); }
        100% { opacity: 1; transform: scale(1); }
    }
    
    /* Botones Streamlit Mejorados */
    .stButton > button {
        background: linear-gradient(135deg, var(--sura-blue-primary), var(--sura-blue-vivid));
        color: var(--sura-white);
        border: none;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(45, 109, 246, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(45, 109, 246, 0.4);
        background: linear-gradient(135deg, var(--sura-blue-vivid), var(--sura-blue-primary));
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Inputs Mejorados */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border: 2px solid var(--sura-gray-light);
        border-radius: 12px;
        padding: 0.75rem;
        font-family: inherit;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
        background: var(--sura-white);
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--sura-blue-primary);
        box-shadow: 0 0 0 3px rgba(0, 51, 160, 0.1);
        outline: none;
    }
    
    /* Cards Modernas - Compactas */
    .modern-card {
        background: var(--sura-white);
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid var(--sura-bg-1);
        margin-bottom: 0.75rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .modern-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
    }
    
    /* Sidebar Mejorado */
    .css-1d391kg {
        background: var(--sura-white);
        border-radius: 16px;
        margin: 1rem;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Métricas Visuales */
    .metric-container {
        background: linear-gradient(135deg, var(--sura-blue-light), var(--sura-aqua-light));
        border-radius: 10px;
        padding: 0.9rem;
        text-align: center;
        color: var(--sura-blue-primary);
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(138, 156, 211, 0.2);
    }
    
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0.25rem 0 0 0;
        opacity: 0.8;
    }
    
    /* Chat Profesional Corporativo */
    .chat-message-container {
        margin-bottom: 1.5rem;
        animation: fadeInSlide 0.3s ease-out;
    }
    
    .chat-message-container.user {
        display: flex;
        justify-content: flex-end;
        margin-left: 2rem;
    }
    
    .chat-message-container.assistant {
        display: flex;
        justify-content: flex-start;
        margin-right: 2rem;
    }
    
    .message-wrapper {
        background: var(--sura-white);
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        max-width: 75%;
        border: 1px solid var(--sura-bg-1);
        overflow: hidden;
    }
    
    .chat-message-container.user .message-wrapper {
        background: var(--sura-blue-primary);
        color: var(--sura-white);
        border: 1px solid var(--sura-blue-vivid);
    }
    
    .message-header {
        background: var(--sura-bg-1);
        padding: 0.75rem 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .chat-message-container.user .message-header {
        background: rgba(255, 255, 255, 0.1);
        color: var(--sura-white);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .message-icon {
        font-size: 1rem;
    }
    
    .sender-name {
        font-weight: 600;
        color: var(--sura-blue-primary);
    }
    
    .chat-message-container.user .sender-name {
        color: var(--sura-white);
    }
    
    .message-time {
        margin-left: auto;
        font-size: 0.75rem;
        opacity: 0.7;
    }
    
    .message-content-professional {
        padding: 1rem 1.25rem;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    
    .message-content-professional p {
        margin: 0 0 0.5rem 0;
    }
    
    .message-content-professional p:last-child {
        margin-bottom: 0;
    }
    
    @keyframes fadeInSlide {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Estados de Proceso */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-active {
        background: var(--success);
        color: var(--sura-white);
    }
    
    .status-pending {
        background: var(--warning);
        color: var(--sura-blue-primary);
    }
    
    .status-completed {
        background: var(--sura-aqua);
        color: var(--sura-white);
    }
    
    /* Alertas Modernas */
    .modern-alert {
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid;
        font-weight: 500;
    }
    
    .alert-info {
        background: var(--sura-bg-4);
        border-color: var(--info);
        color: var(--sura-blue-primary);
    }
    
    .alert-success {
        background: var(--sura-bg-3);
        border-color: var(--success);
        color: var(--sura-blue-primary);
    }
    
    .alert-warning {
        background: var(--sura-bg-2);
        border-color: var(--warning);
        color: var(--sura-blue-primary);
    }
    
    /* Loading States */
    .loading-spinner {
        width: 32px;
        height: 32px;
        border: 3px solid var(--sura-gray-light);
        border-top: 3px solid var(--sura-blue-primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 1rem auto;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header {
            flex-direction: column;
            text-align: center;
            gap: 1rem;
        }
        
        .chat-message.user,
        .chat-message.assistant {
            margin-left: 0;
            margin-right: 0;
        }
        
        .modern-card {
            padding: 1rem;
        }
    }
    
    /* Efectos de Interacción */
    .interactive:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: all 0.2s ease;
    }
    
    /* Scrollbars Personalizados */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--sura-bg-1);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--sura-blue-light);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--sura-blue-primary);
    }
    
    /* Tablas Profesionales */
    .professional-table-container {
        background: var(--sura-white);
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        overflow: hidden;
        margin: 1rem 0;
        border: 1px solid var(--sura-bg-1);
    }
    
    .table-title {
        color: var(--sura-blue-primary);
        font-weight: 600;
        font-size: 1.1rem;
        margin: 0;
        padding: 1rem 1.25rem 0.5rem 1.25rem;
    }
    
    .professional-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    
    .table-header {
        background: var(--sura-bg-1);
        color: var(--sura-blue-primary);
        font-weight: 600;
        padding: 1rem;
        text-align: left;
        border-bottom: 2px solid var(--sura-blue-light);
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .table-row.even {
        background: var(--sura-white);
    }
    
    .table-row.odd {
        background: var(--sura-bg-5);
    }
    
    .table-row:hover {
        background: var(--sura-bg-4);
        cursor: pointer;
    }
    
    .table-cell {
        padding: 0.875rem 1rem;
        border-bottom: 1px solid var(--sura-bg-1);
        color: var(--sura-blue-primary);
    }
    
    /* Dashboard Metrics Empresariales */
    .dashboard-metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .dashboard-metric-card {
        background: var(--sura-white);
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid var(--sura-bg-1);
        transition: transform 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    
    .dashboard-metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
    }
    
    .dashboard-metric-card.blue::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--sura-blue-primary), var(--sura-blue-vivid));
    }
    
    .dashboard-metric-card.aqua::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--sura-aqua);
    }
    
    .metric-value-large {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--sura-blue-primary);
        margin: 0;
        line-height: 1;
    }
    
    .metric-label-enterprise {
        font-size: 0.8rem;
        color: var(--sura-gray);
        font-weight: 500;
        margin: 0.3rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-trend {
        font-size: 0.875rem;
        font-weight: 600;
        margin-top: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        display: inline-block;
    }
    
    .metric-trend.blue {
        background: var(--sura-bg-4);
        color: var(--sura-blue-primary);
    }
    
    /* Indicadores de Estado Profesionales */
    .status-indicator-professional {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: var(--sura-white);
        border-radius: 8px;
        border: 1px solid var(--sura-bg-1);
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .status-label {
        color: var(--sura-blue-primary);
    }
    
    /* Hide Streamlit Footer */
    .css-h5rgaw {
        display: none;
    }
    
    /* Hide Streamlit Menu */
    #MainMenu {
        display: none;
    }
    
    /* Custom Streamlit Headers */
    .css-10trblm {
        color: var(--sura-blue-primary);
        font-weight: 700;
    }
    
    /* Mejorar selectores y elementos Streamlit */
    .stSelectbox label {
        color: var(--sura-blue-primary);
        font-weight: 600;
    }
    
    .stCheckbox label {
        color: var(--sura-blue-primary);
        font-weight: 500;
    }
    
    /* Optimizar métricas de Streamlit */
    .stMetric {
        background: var(--sura-white);
        border-radius: 8px;
        padding: 0.75rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
        border: 1px solid var(--sura-bg-1);
    }
    
    .stMetric > div {
        padding: 0;
    }
    
    .stMetric [data-testid="metric-container"] {
        background: transparent;
    }
    
    /* Hacer subheaders más compactos */
    .stSubheader {
        color: var(--sura-blue-primary);
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        margin-top: 1.5rem;
    }
    
    /* Tablas más compactas */
    .stDataFrame {
        font-size: 0.9rem;
    }
    
    .stDataFrame table {
        border-collapse: collapse;
    }
    
    .stDataFrame th {
        background: var(--sura-bg-1);
        color: var(--sura-blue-primary);
        font-weight: 600;
        padding: 0.5rem;
        border: 1px solid var(--sura-bg-1);
    }
    
    .stDataFrame td {
        padding: 0.5rem;
        border: 1px solid var(--sura-bg-1);
    }
    
    /* Sidebar mejorado */
    .css-1d391kg {
        background: var(--sura-white);
        border-radius: 16px;
        margin: 1rem;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Barras de progreso con estilo Sura */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--sura-blue-primary), var(--sura-aqua));
    }
    
    .stProgress > div > div {
        background: var(--sura-bg-1);
    }
    
    /* Títulos de sidebar */
    .css-1d391kg h3 {
        color: var(--sura-blue-primary);
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    </style>
    """
    
    st.markdown(sura_css, unsafe_allow_html=True)


def render_sura_header(title: str, subtitle: str, connection_status: bool = True):
    """Renderiza header corporativo Seguros Sura"""
    
    status_text = "Conectado en tiempo real" if connection_status else "Conectando..."
    status_icon = "●" if connection_status else "○"
    
    header_html = f"""
    <div class="main-header">
        <div class="brand-section">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        <div class="connection-status">
            <span class="pulse-indicator"></span>
            {status_icon} {status_text}
        </div>
    </div>
    """
    
    st.markdown(header_html, unsafe_allow_html=True)


def render_metric_card(value: str, label: str, trend: str = None):
    """Renderiza tarjeta de métrica moderna"""
    
    trend_html = f'<div style="font-size: 0.875rem; color: var(--success);">{trend}</div>' if trend else ''
    
    metric_html = f"""
    <div class="metric-container">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {trend_html}
    </div>
    """
    
    st.markdown(metric_html, unsafe_allow_html=True)


def render_status_badge(status: str, text: str):
    """Renderiza badge de estado moderno"""
    
    status_class = f"status-{status}"
    
    badge_html = f"""
    <span class="status-badge {status_class}">
        {text}
    </span>
    """
    
    st.markdown(badge_html, unsafe_allow_html=True)


def render_modern_alert(message: str, alert_type: str = "info"):
    """Renderiza alerta moderna"""
    
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    icon = icons.get(alert_type, "ℹ️")
    
    alert_html = f"""
    <div class="modern-alert alert-{alert_type}">
        {icon} {message}
    </div>
    """
    
    st.markdown(alert_html, unsafe_allow_html=True)


def render_chat_message(content: str, sender: str = "assistant", timestamp: str = None):
    """Renderiza mensaje de chat con diseño corporativo profesional"""
    
    if timestamp is None:
        timestamp = datetime.now().strftime("%H:%M")
    
    # Determinar íconos profesionales (mínimos emojis)
    icon = ""
    if sender == "user":
        icon = '<span class="message-icon user-icon">●</span>'
        sender_label = "Cliente"
    else:
        icon = '<span class="message-icon assistant-icon">■</span>'
        sender_label = "Seguros Sura"
    
    message_html = f"""
    <div class="chat-message-container {sender}">
        <div class="message-wrapper">
            <div class="message-header">
                {icon}
                <span class="sender-name">{sender_label}</span>
                <span class="message-time">{timestamp}</span>
            </div>
            <div class="message-content-professional">
                {content}
            </div>
        </div>
    </div>
    """
    
    st.markdown(message_html, unsafe_allow_html=True)


def render_loading_spinner(text: str = "Procesando..."):
    """Renderiza spinner de carga moderno"""
    
    spinner_html = f"""
    <div style="text-align: center; padding: 2rem;">
        <div class="loading-spinner"></div>
        <p style="color: var(--sura-blue-primary); margin-top: 1rem; font-weight: 500;">{text}</p>
    </div>
    """
    
    st.markdown(spinner_html, unsafe_allow_html=True)


def create_modern_container():
    """Crea contenedor moderno para contenido"""
    return st.container()


def render_section_divider(title: str = None):
    """Renderiza divisor de sección elegante"""
    
    if title:
        divider_html = f"""
        <div style="display: flex; align-items: center; margin: 2rem 0;">
            <div style="flex: 1; height: 2px; background: linear-gradient(90deg, transparent, var(--sura-blue-light), transparent);"></div>
            <div style="padding: 0 1rem; color: var(--sura-blue-primary); font-weight: 600; font-size: 1.1rem;">{title}</div>
            <div style="flex: 1; height: 2px; background: linear-gradient(90deg, transparent, var(--sura-blue-light), transparent);"></div>
        </div>
        """
    else:
        divider_html = """
        <div style="height: 2px; background: linear-gradient(90deg, transparent, var(--sura-blue-light), transparent); margin: 2rem 0;"></div>
        """
    
    st.markdown(divider_html, unsafe_allow_html=True)


def render_professional_table(data: list, headers: list, title: str = None):
    """Renderiza tabla profesional estilo corporativo"""
    
    if title:
        title_html = f'<h3 class="table-title">{title}</h3>'
    else:
        title_html = ""
    
    # Crear filas de la tabla
    rows_html = ""
    for i, row in enumerate(data):
        row_class = "even" if i % 2 == 0 else "odd"
        cells_html = "".join([f'<td class="table-cell">{cell}</td>' for cell in row])
        rows_html += f'<tr class="table-row {row_class}">{cells_html}</tr>'
    
    # Crear headers
    headers_html = "".join([f'<th class="table-header">{header}</th>' for header in headers])
    
    table_html = f"""
    <div class="professional-table-container">
        {title_html}
        <table class="professional-table">
            <thead>
                <tr class="header-row">{headers_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    
    st.markdown(table_html, unsafe_allow_html=True)


def render_dashboard_metrics(metrics_data: list):
    """Renderiza métricas de dashboard estilo empresarial"""
    
    metrics_html = '<div class="dashboard-metrics-grid">'
    
    for metric in metrics_data:
        value = metric.get('value', '0')
        label = metric.get('label', 'Métrica')
        trend = metric.get('trend', None)
        color = metric.get('color', 'blue')
        
        trend_html = ""
        if trend:
            trend_icon = "↗" if trend.startswith('+') else "↘" if trend.startswith('-') else "→"
            trend_html = f'<div class="metric-trend {color}">{trend_icon} {trend}</div>'
        
        metrics_html += f"""
        <div class="dashboard-metric-card {color}">
            <div class="metric-value-large">{value}</div>
            <div class="metric-label-enterprise">{label}</div>
            {trend_html}
        </div>
        """
    
    metrics_html += '</div>'
    
    st.markdown(metrics_html, unsafe_allow_html=True)


def render_status_indicator_professional(status: str, label: str):
    """Renderiza indicador de estado profesional"""
    
    status_colors = {
        "healthy": "#00AEC7",
        "active": "#00AEC7", 
        "warning": "#E3E829",
        "error": "#FF4757",
        "offline": "#888B8D"
    }
    
    color = status_colors.get(status, "#888B8D")
    
    indicator_html = f"""
    <div class="status-indicator-professional">
        <div class="status-dot" style="background-color: {color};"></div>
        <span class="status-label">{label}</span>
    </div>
    """
    
    st.markdown(indicator_html, unsafe_allow_html=True)


def apply_custom_css_to_component(css_class: str, additional_styles: str = ""):
    """Aplica estilos CSS personalizados a componentes específicos"""
    
    custom_css = f"""
    <style>
    .{css_class} {{
        {additional_styles}
    }}
    </style>
    """
    
    st.markdown(custom_css, unsafe_allow_html=True)
