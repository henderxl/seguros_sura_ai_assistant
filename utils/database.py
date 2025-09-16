"""
Gestión de base de datos para el sistema de agentes de IA.
Maneja persistencia de conversaciones, sesiones y estado del sistema.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from contextlib import contextmanager

from utils.config import config

@dataclass
class ConversationSession:
    """Modelo de sesión de conversación"""
    session_id: str
    user_type: str  # 'client' or 'advisor'
    created_at: datetime
    updated_at: datetime
    status: str  # 'active', 'transferred', 'completed'
    metadata: Dict[str, Any]

@dataclass
class Message:
    """Modelo de mensaje en conversación"""
    message_id: str
    session_id: str
    agent_type: str  # 'user', 'consultant', 'quotation', 'expedition', 'human_loop'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]

class DatabaseManager:
    """Gestor de base de datos SQLite para el sistema"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database.sqlite_path
        self._ensure_db_path()
        self._init_tables()
    
    def _ensure_db_path(self):
        """Asegura que el directorio de la BD exista"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones a la BD"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_tables(self):
        """Inicializa las tablas de la base de datos"""
        with self.get_connection() as conn:
            # Tabla de sesiones
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_type TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Tabla de mensajes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
                )
            """)
            
            # Tabla de estado de agentes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_state (
                    session_id TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (session_id, agent_type),
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
                )
            """)
            
            # Tabla de cotizaciones
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotations (
                    quotation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    vehicle_data TEXT NOT NULL,
                    quotation_result TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
                )
            """)
            
            # Tabla de pólizas expedidas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    policy_number TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    quotation_id TEXT,
                    client_data TEXT NOT NULL,
                    policy_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id),
                    FOREIGN KEY (quotation_id) REFERENCES quotations (quotation_id)
                )
            """)
            
            conn.commit()
    
    def create_session(self, user_type: str, metadata: Optional[Dict] = None, session_id: Optional[str] = None) -> str:
        """Crea una nueva sesión de conversación"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        now = datetime.now()
        metadata = metadata or {}
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO conversation_sessions 
                (session_id, user_type, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, user_type, now, now, json.dumps(metadata)))
            conn.commit()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Obtiene información de una sesión"""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM conversation_sessions WHERE session_id = ?
            """, (session_id,)).fetchone()
            
            if row:
                return ConversationSession(
                    session_id=row['session_id'],
                    user_type=row['user_type'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    status=row['status'],
                    metadata=json.loads(row['metadata'])
                )
        return None
    
    def update_session_status(self, session_id: str, status: str):
        """Actualiza el estado de una sesión"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE conversation_sessions 
                SET status = ?, updated_at = ?
                WHERE session_id = ?
            """, (status, datetime.now(), session_id))
            conn.commit()
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Obtiene el estado actual de una sesión"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT status, metadata FROM conversation_sessions
                WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "status": row[0],
                    "metadata": json.loads(row[1]) if row[1] else {}
                }
            return None
    
    def get_messages_after_timestamp(self, session_id: str, timestamp: str) -> List[Any]:
        """Obtiene mensajes después de un timestamp específico para sincronización"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, session_id, agent_type, content, timestamp, metadata
                FROM conversation_history 
                WHERE session_id = ? AND timestamp > ?
                ORDER BY timestamp ASC
            """, (session_id, timestamp))
            
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                message = type('Message', (), {
                    'id': row[0],
                    'session_id': row[1],
                    'agent_type': row[2],
                    'content': row[3],
                    'timestamp': datetime.fromisoformat(row[4]),
                    'metadata': json.loads(row[5]) if row[5] else {}
                })()
                messages.append(message)
            
            return messages
    
    def update_session_metadata(self, session_id: str, metadata_update: Dict[str, Any]):
        """Actualiza metadatos de sesión de forma incremental"""
        with self.get_connection() as conn:
            # Obtener metadata actual
            cursor = conn.execute("""
                SELECT metadata FROM conversation_sessions WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            
            current_metadata = json.loads(row[0]) if row and row[0] else {}
            current_metadata.update(metadata_update)
            
            # Actualizar metadata
            conn.execute("""
                UPDATE conversation_sessions 
                SET metadata = ?, updated_at = ?
                WHERE session_id = ?
            """, (json.dumps(current_metadata), datetime.now().isoformat(), session_id))
    
    def add_message(self, session_id: str, agent_type: str, content: str, 
                   metadata: Optional[Dict] = None) -> str:
        """Agrega un mensaje a la conversación"""
        message_id = str(uuid.uuid4())
        now = datetime.now()
        metadata = metadata or {}
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO messages 
                (message_id, session_id, agent_type, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, session_id, agent_type, content, now, json.dumps(metadata)))
            
            # Actualizar timestamp de sesión
            conn.execute("""
                UPDATE conversation_sessions 
                SET updated_at = ? WHERE session_id = ?
            """, (now, session_id))
            
            conn.commit()
        
        return message_id
    
    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Obtiene el historial de conversación"""
        query = """
            SELECT * FROM messages 
            WHERE session_id = ? 
            ORDER BY timestamp ASC
        """
        params = [session_id]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
            return [Message(
                message_id=row['message_id'],
                session_id=row['session_id'],
                agent_type=row['agent_type'],
                content=row['content'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                metadata=json.loads(row['metadata'])
            ) for row in rows]
    
    def save_agent_state(self, session_id: str, agent_type: str, state_data: Dict):
        """Guarda el estado de un agente"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_state
                (session_id, agent_type, state_data, updated_at)
                VALUES (?, ?, ?, ?)
            """, (session_id, agent_type, json.dumps(state_data), datetime.now()))
            conn.commit()
    
    def get_agent_state(self, session_id: str, agent_type: str) -> Optional[Dict]:
        """Obtiene el estado de un agente"""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT state_data FROM agent_state
                WHERE session_id = ? AND agent_type = ?
            """, (session_id, agent_type)).fetchone()
            
            if row:
                return json.loads(row['state_data'])
        return None
    
    def save_quotation(self, session_id: str, vehicle_data: Dict, 
                      quotation_result: Dict) -> str:
        """Guarda una cotización"""
        quotation_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO quotations
                (quotation_id, session_id, vehicle_data, quotation_result, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (quotation_id, session_id, json.dumps(vehicle_data), 
                 json.dumps(quotation_result), datetime.now()))
            conn.commit()
        
        return quotation_id
    
    def save_policy(self, policy_number: str, session_id: str, 
                   quotation_id: Optional[str], client_data: Dict, 
                   policy_data: Dict):
        """Guarda una póliza expedida"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO policies
                (policy_number, session_id, quotation_id, client_data, 
                 policy_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (policy_number, session_id, quotation_id, 
                 json.dumps(client_data), json.dumps(policy_data), datetime.now()))
            conn.commit()
    
    def get_active_sessions(self, user_type: Optional[str] = None) -> List[ConversationSession]:
        """Obtiene sesiones activas Y transferidas (para visibilidad del asesor)"""
        # INCLUIR sesiones 'active', 'transferred' y 'human_active' para que el asesor las vea
        query = "SELECT * FROM conversation_sessions WHERE status IN ('active', 'transferred', 'human_active')"
        params = []
        
        if user_type:
            query += " AND user_type = ?"
            params.append(user_type)
        
        query += " ORDER BY updated_at DESC"
        
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
            return [ConversationSession(
                session_id=row['session_id'],
                user_type=row['user_type'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                status=row['status'],
                metadata=json.loads(row['metadata'])
            ) for row in rows]

# Instancia global del gestor de BD
db_manager = DatabaseManager()
