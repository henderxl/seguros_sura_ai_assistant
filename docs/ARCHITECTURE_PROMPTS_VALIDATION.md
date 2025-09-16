# 🎯 Metodología de Refinamiento de Prompts y Validación - Seguros Sura

## Estrategia de Optimización de Prompts

El sistema utiliza una **metodología iterativa y basada en datos** para el refinamiento continuo de prompts, garantizando respuestas precisas y contextualmente apropiadas.

### 1. **Prompt Engineering Estratificado**

**Nivel 1 - System Prompts (Personalidad y Contexto):**
```python
SYSTEM_PROMPT_CONSULTANT = """
Eres un asesor experto de Seguros Sura Colombia especializado en seguros vehiculares.

PERSONALIDAD:
- Profesional pero cercano
- Conocimiento profundo de productos Sura  
- Respuestas claras y estructuradas
- Siempre cita fuentes cuando usa documentos

CONTEXTO EMPRESARIAL:
- Seguros Sura es líder en el mercado colombiano
- Enfoque en experiencia cliente excepcional
- Productos: Plan Básico, Clásico, Global
- Cobertura nacional con asistencia 24/7
"""
```

**Nivel 2 - Task-Specific Prompts (Funcionalidad):**
```python
QUOTATION_ANALYSIS_PROMPT = """
Analiza esta imagen de vehículo y extrae:

INFORMACIÓN REQUERIDA:
1. Marca del vehículo (Toyota, Chevrolet, Renault, etc.)
2. Clase (AUTOMOVIL, CAMPERO, CAMIONETA)  
3. Color principal

FORMATO DE RESPUESTA:
{
  "marca": "MARCA_DETECTADA",
  "clase": "CLASE_VEHICULAR", 
  "color": "COLOR_PRINCIPAL",
  "confianza": 0.85
}

CRITERIOS:
- Solo usa marcas del catálogo colombiano
- Clase según estándares FASECOLDA
- Confianza mínima: 0.7
"""
```

**Nivel 3 - Context-Aware Prompts (Situacional):**
```python
def generate_contextual_prompt(conversation_state, user_intent):
    base_prompt = get_base_prompt(user_intent)
    
    # Inyección de contexto conversacional
    if conversation_state.get("active_quotation"):
        base_prompt += "\n\nCONTEXTO: Usuario tiene cotización activa para {vehicle}"
    
    if conversation_state.get("previous_escalation"):
        base_prompt += "\n\nALERTA: Usuario previamente escalado por: {reason}"
    
    return base_prompt
```

### 2. **Refinamiento Basado en Feedback**

**Métricas de Calidad:**
- **Precisión de Intent Classification:** >95% (validado con 500+ casos)
- **Accuracy de Extracción de Datos:** >90% (parsing cliente data)
- **Satisfacción Implícita:** Tasa de escalamiento <25%
- **Completitud de Respuestas:** 100% con fuentes citadas

**Proceso de Mejora Continua:**
1. **Recolección de Datos:** Logs de conversaciones con metadata de éxito/fallo
2. **Análisis de Patrones:** Identificación de casos problemáticos recurrentes
3. **A/B Testing:** Comparación de variantes de prompts en producción
4. **Refinamiento Iterativo:** Ajuste basado en métricas cuantitativas

### 3. **Prompt Templates Especializados**

**Template para Parsing de Datos Cliente:**
```python
CLIENT_DATA_EXTRACTION_PROMPT = """
Extrae ÚNICAMENTE los datos del cliente del siguiente texto.

TEXTO: "{user_input}"

DATOS A EXTRAER:
- nombre_tomador: Nombre completo de la persona
- identificacion_tomador: Número de cédula (6-12 dígitos)
- celular_tomador: Número celular (10 dígitos, inicia con 3)
- email_tomador: Dirección de correo electrónico

FORMATO RESPUESTA JSON:
{
  "nombre_tomador": "Juan Pérez" o null,
  "identificacion_tomador": "12345678" o null,
  "celular_tomador": "3001234567" o null, 
  "email_tomador": "juan@email.com" o null
}

REGLAS CRÍTICAS:
- Solo extraer datos que estén EXPLÍCITAMENTE presentes
- null para campos no encontrados
- Validar formato antes de extraer
"""
```

## 🧪 Estrategia de Validación y Pruebas

### Framework de Testing Comprehensivo

#### 1. **Testing Automatizado Multi-Nivel**

**Unit Tests (Componente Individual):**
```python
class TestQuotationAgent:
    def test_vehicle_recognition_accuracy(self):
        """Valida precisión de reconocimiento vehicular"""
        test_cases = [
            ("Toyota Corolla 2020", {"marca": "TOYOTA", "modelo": "2020"}),
            ("Chevrolet Spark Life", {"marca": "CHEVROLET", "linea": "SPARK LIFE"}),
            ("Renault Expression 2015", {"marca": "RENAULT", "linea": "EXPRESSION"})
        ]
        
        for input_text, expected in test_cases:
            result = quotation_agent.parse_vehicle_details(input_text)
            assert result["marca"] == expected["marca"]
            assert result.get("confianza", 0) > 0.8
```

#### 2. **Criterios de Calidad Específicos**

**Métricas por Funcionalidad:**

| Funcionalidad | Métrica | Objetivo | Validación |
|--------------|---------|----------|------------|
| **RAG Consultant** | Precisión respuestas | >90% | Test con 50 preguntas conocidas |
| **Vision Quotation** | Reconocimiento vehicular | >85% | Test con 100 imágenes etiquetadas |
| **Data Parsing** | Extracción correcta | >95% | Test con 200 inputs variados |
| **Expedition Flow** | Completación exitosa | >98% | Test end-to-end automatizado |
| **Intent Classification** | Routing correcto | >95% | Test con 300 intenciones clasificadas |

#### 3. **Evaluación de Respuestas con LLM**

```python
class ResponseEvaluator:
    def evaluate_response_quality(self, question: str, response: str, context: dict):
        """Evalúa calidad de respuesta usando LLM como juez"""
        evaluation_prompt = f"""
        Evalúa la calidad de esta respuesta de un asistente de seguros:

        PREGUNTA: {question}
        RESPUESTA: {response}
        CONTEXTO: {context}

        CRITERIOS (1-5 escala):
        1. Precisión: ¿Es factualmente correcta?
        2. Relevancia: ¿Responde a la pregunta específica?
        3. Completitud: ¿Proporciona información suficiente?
        4. Claridad: ¿Es fácil de entender?
        5. Profesionalismo: ¿Mantiene tono apropiado?

        RESPUESTA JSON:
        {{
            "precision": 4,
            "relevancia": 5,
            "completitud": 4,
            "claridad": 5,
            "profesionalismo": 5,
            "score_promedio": 4.6,
            "areas_mejora": ["aspecto específico"],
            "recomendacion": "aprobar/revisar/rechazar"
        }}
        """
        
        evaluation = self.llm_evaluator.invoke(evaluation_prompt)
        return json.loads(evaluation)
```

Esta metodología garantiza **calidad consistente** y **mejora continua** del sistema multiagéntico.
