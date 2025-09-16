"""
Intent Classifier - LLM Inteligente para clasificación de intenciones del usuario
Reemplaza el routing primitivo por comprensión semántica avanzada
"""

from typing import Dict, Any, List, Optional
from langchain_openai import AzureChatOpenAI
from utils.config import config
import json
import logging

logger = logging.getLogger(__name__)

class IntentClassifier:
    """
    Clasificador de intenciones usando LLM para routing inteligente
    """
    
    def __init__(self):
        self.llm = AzureChatOpenAI(
            api_key=config.azure_openai.api_key,
            azure_endpoint=config.azure_openai.endpoint,
            api_version=config.azure_openai.api_version,
            azure_deployment=config.azure_openai.chat_deployment,
            temperature=0.1  # Baja temperatura para consistencia
        )
        
        # Definir intenciones claras y sus características
        self.intents = {
            "greeting": {
                "description": "Saludos, cortesías, presentaciones iniciales",
                "examples": ["hola", "buenos días", "qué tal", "me puedes ayudar"],
                "agent": "consultant",
                "priority": 1
            },
            "consultation": {
                "description": "Preguntas sobre seguros, planes, coberturas, deducibles, condiciones",
                "examples": ["qué cubre el plan básico", "cuál es el deducible", "diferencias entre planes"],
                "agent": "consultant", 
                "priority": 2
            },
            "quotation_request": {
                "description": "Solicitud explícita de cotización con/sin imagen",
                "examples": ["quiero cotizar", "necesito cotización", "cuánto me cuesta", "imagen del vehículo"],
                "agent": "quotation",
                "priority": 3
            },
            "quotation_details": {
                "description": "Proporcionar detalles del vehículo para cotización en curso",
                "examples": ["Toyota 2020", "es un sedán rojo", "modelo 2019 línea sport"],
                "agent": "quotation",
                "priority": 4
            },
            "purchase_intent": {
                "description": "Intención de comprar póliza cotizada",
                "examples": ["quiero comprar", "acepto la cotización", "proceder con la compra"],
                "agent": "expedition",
                "priority": 5
            },
            "client_data": {
                "description": "Proporcionar datos personales para expedición",
                "examples": ["mi cédula es", "teléfono", "correo electrónico"],
                "agent": "expedition",
                "priority": 6
            },
            "human_request": {
                "description": "Solicitud explícita de hablar con humano",
                "examples": ["quiero hablar con un asesor", "no entiendo", "esto es confuso"],
                "agent": "human_loop",
                "priority": 7
            },
            "complaint": {
                "description": "Quejas, problemas, insatisfacción",
                "examples": ["esto no funciona", "muy caro", "no me gusta"],
                "agent": "human_loop",
                "priority": 8
            }
        }

    def classify_intent(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clasifica la intención del usuario usando LLM
        
        Args:
            user_input: Texto del usuario
            context: Contexto de la conversación
            
        Returns:
            Dict con intención detectada, agente recomendado, confianza
        """
        try:
            # Preparar prompt de clasificación
            classification_prompt = self._build_classification_prompt(user_input, context)
            
            # Ejecutar clasificación con LLM
            response = self.llm.invoke(classification_prompt)
            
            # Procesar respuesta
            return self._process_classification_response(response.content, user_input, context)
            
        except Exception as e:
            logger.error(f"Error en clasificación de intención: {str(e)}")
            return {
                "intent": "consultation",
                "agent": "consultant", 
                "confidence": 0.5,
                "reasoning": "Error en clasificación, usando fallback"
            }

    def _build_classification_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Construye prompt de clasificación inteligente"""
        
        # Extraer contexto relevante
        current_state = context.get("quotation_state", "")
        expedition_state = context.get("expedition_state", "")
        has_image = context.get("has_image", False)
        current_quotation = context.get("current_quotation", {})
        conversation_length = len(context.get("conversation_history", []))
        
        prompt = f"""
Eres un clasificador de intenciones EXPERTO para seguros de autos Sura Colombia.

MENSAJE DEL USUARIO: "{user_input}"

CONTEXTO ACTUAL:
- Estado cotización: {current_state}
- Estado expedición: {expedition_state}
- Tiene imagen: {has_image}
- Cotización activa: {'Sí' if current_quotation else 'No'}
- Longitud conversación: {conversation_length}

INTENCIONES DISPONIBLES:
{self._format_intents_for_prompt()}

INSTRUCCIONES:
1. Analiza el mensaje considerando el CONTEXTO COMPLETO
2. Si hay cotización/expedición en curso, prioriza esa continuidad
3. Considera el flujo natural: consulta → cotización → expedición
4. Responde SOLO en formato JSON válido:

{{
    "intent": "nombre_intencion",
    "agent": "agente_recomendado", 
    "confidence": 0.0-1.0,
    "reasoning": "explicación_breve",
    "context_factors": ["factor1", "factor2"]
}}

EJEMPLOS DE CLASIFICACIÓN:
- "qué cubre el plan básico" → consultation/consultant
- "quiero cotizar mi vehículo" → quotation_request/quotation
- "Toyota 2020 sedán" (en cotización) → quotation_details/quotation
- "acepto, quiero comprar" → purchase_intent/expedition
- "mi cédula es 123456" (en expedición) → client_data/expedition

CLASIFICA AHORA:
"""
        return prompt

    def _format_intents_for_prompt(self) -> str:
        """Formatea intenciones para el prompt"""
        formatted = ""
        for intent_name, intent_data in self.intents.items():
            formatted += f"- {intent_name}: {intent_data['description']} → {intent_data['agent']}\n"
        return formatted

    def _process_classification_response(self, response: str, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa respuesta del LLM y aplica lógica de validación"""
        try:
            # Limpiar respuesta y extraer JSON
            clean_response = response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0]
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0]
            
            # Parsear JSON
            classification = json.loads(clean_response)
            
            # Validar campos requeridos
            required_fields = ["intent", "agent", "confidence"]
            for field in required_fields:
                if field not in classification:
                    raise ValueError(f"Campo requerido {field} no encontrado")
            
            # Aplicar validaciones contextuales
            classification = self._apply_contextual_validations(classification, user_input, context)
            
            return classification
            
        except Exception as e:
            logger.warning(f"Error procesando clasificación: {str(e)}")
            # Fallback inteligente
            return self._fallback_classification(user_input, context)

    def _apply_contextual_validations(self, classification: Dict[str, Any], user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica validaciones contextuales a la clasificación"""
        
        # Si hay cotización en curso y usuario proporciona detalles
        if context.get("quotation_state") == "awaiting_details":
            if any(keyword in user_input.lower() for keyword in ["toyota", "ford", "chevrolet", "2020", "2019", "sedán", "suv"]):
                classification["intent"] = "quotation_details"
                classification["agent"] = "quotation"
                classification["confidence"] = min(0.9, classification["confidence"] + 0.2)
        
        # Si hay cotización lista y usuario expresa interés de compra
        if context.get("quotation_state") == "quote_ready":
            if any(keyword in user_input.lower() for keyword in ["acepto", "comprar", "quiero", "proceder", "sí"]):
                classification["intent"] = "purchase_intent"
                classification["agent"] = "expedition"
                classification["confidence"] = min(0.9, classification["confidence"] + 0.2)
        
        # Si hay expedición en curso y usuario proporciona datos
        if context.get("expedition_state") == "requesting_client_data":
            if any(keyword in user_input for keyword in ["@", "cédula", "teléfono", "nombre"]):
                classification["intent"] = "client_data"
                classification["agent"] = "expedition"
                classification["confidence"] = min(0.9, classification["confidence"] + 0.2)
        
        return classification

    def _fallback_classification(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Clasificación de fallback cuando falla el LLM"""
        
        user_lower = user_input.lower()
        
        # Patrones de fallback simples pero efectivos
        if any(word in user_lower for word in ["cotizar", "cotización", "cuánto cuesta"]):
            return {"intent": "quotation_request", "agent": "quotation", "confidence": 0.7, "reasoning": "Fallback: palabras clave cotización"}
        
        if any(word in user_lower for word in ["comprar", "acepto", "proceder"]):
            return {"intent": "purchase_intent", "agent": "expedition", "confidence": 0.7, "reasoning": "Fallback: palabras clave compra"}
        
        if any(word in user_lower for word in ["asesor", "humano", "persona"]):
            return {"intent": "human_request", "agent": "human_loop", "confidence": 0.8, "reasoning": "Fallback: solicitud humano"}
        
        # Default: consulta
        return {"intent": "consultation", "agent": "consultant", "confidence": 0.6, "reasoning": "Fallback: consulta general"}

# Instancia global
intent_classifier = IntentClassifier()
