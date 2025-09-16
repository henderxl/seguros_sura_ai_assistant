"""
Configuración de logging estructurado para el sistema de agentes.
Proporciona logging consistente y detallado para monitoreo y debugging.
"""

import logging
import structlog
import sys
from pathlib import Path
from typing import Any, Dict

from utils.config import config

def configure_logging():
    """Configura el sistema de logging estructurado"""
    
    # Configurar logging básico de Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if not config.debug else logging.DEBUG,
    )
    
    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if config.debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if config.debug else logging.INFO
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Obtiene un logger estructurado para un componente específico"""
    return structlog.get_logger(name)

class AgentLogger:
    """Logger especializado para agentes con contexto automático"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_logger(f"agent.{agent_name}")
    
    def info(self, message: str, **kwargs):
        """Log nivel info con contexto del agente"""
        self.logger.info(message, agent=self.agent_name, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log nivel error con contexto del agente"""
        self.logger.error(message, agent=self.agent_name, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log nivel warning con contexto del agente"""
        self.logger.warning(message, agent=self.agent_name, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log nivel debug con contexto del agente"""
        self.logger.debug(message, agent=self.agent_name, **kwargs)
    
    def log_interaction(self, session_id: str, input_data: Any, output_data: Any, **kwargs):
        """Log específico para interacciones de agentes"""
        self.logger.info(
            "agent_interaction",
            agent=self.agent_name,
            session_id=session_id,
            input_size=len(str(input_data)) if input_data else 0,
            output_size=len(str(output_data)) if output_data else 0,
            **kwargs
        )
    
    def log_error_with_context(self, error: Exception, session_id: str, context: Dict[str, Any]):
        """Log detallado para errores con contexto completo"""
        self.logger.error(
            "agent_error",
            agent=self.agent_name,
            session_id=session_id,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context
        )

class ConversationLogger:
    """Logger especializado para conversaciones"""
    
    def __init__(self):
        self.logger = get_logger("conversation")
    
    def log_message(self, session_id: str, agent_type: str, content: str, metadata: Dict[str, Any]):
        """Log de mensaje en conversación"""
        self.logger.info(
            "conversation_message",
            session_id=session_id,
            agent_type=agent_type,
            content_length=len(content),
            metadata=metadata
        )
    
    def log_session_start(self, session_id: str, user_type: str):
        """Log de inicio de sesión"""
        self.logger.info(
            "session_start",
            session_id=session_id,
            user_type=user_type
        )
    
    def log_session_transfer(self, session_id: str, from_agent: str, to_agent: str, reason: str):
        """Log de transferencia entre agentes"""
        self.logger.info(
            "session_transfer",
            session_id=session_id,
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason
        )
    
    def log_session_end(self, session_id: str, status: str, duration_seconds: float):
        """Log de fin de sesión"""
        self.logger.info(
            "session_end",
            session_id=session_id,
            status=status,
            duration_seconds=duration_seconds
        )

class PerformanceLogger:
    """Logger especializado para métricas de performance"""
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_operation_time(self, operation: str, duration_seconds: float, **kwargs):
        """Log de tiempo de operación"""
        self.logger.info(
            "operation_performance",
            operation=operation,
            duration_seconds=duration_seconds,
            **kwargs
        )
    
    def log_llm_call(self, model: str, tokens_input: int, tokens_output: int, 
                     duration_seconds: float, cost_estimate: float = None):
        """Log específico para llamadas a LLM"""
        log_data = {
            "llm_call": True,
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "duration_seconds": duration_seconds
        }
        
        if cost_estimate:
            log_data["cost_estimate"] = cost_estimate
            
        self.logger.info("llm_performance", **log_data)
    
    def log_vector_search(self, query: str, results_count: int, duration_seconds: float):
        """Log específico para búsquedas vectoriales"""
        self.logger.info(
            "vector_search_performance",
            query_length=len(query),
            results_count=results_count,
            duration_seconds=duration_seconds
        )

# Configurar logging al importar el módulo
configure_logging()

# Instancias globales de loggers especializados
conversation_logger = ConversationLogger()
performance_logger = PerformanceLogger()
