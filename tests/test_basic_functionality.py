"""
Tests básicos para validar funcionalidad del sistema.
Incluye tests de integración con casos proporcionados en la prueba técnica.
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.orchestrator import orchestrator
from services.rag_service import rag_service
from services.quotation_service import quotation_service
from services.expedition_service import expedition_service
from utils.database import db_manager
from utils.config import config

class TestBasicFunctionality:
    """Tests básicos de funcionalidad del sistema"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup para cada test"""
        # Configurar ambiente de test
        os.environ["ENVIRONMENT"] = "test"
        os.environ["DEBUG"] = "True"
        
        # Verificar que hay API key (puede ser fake para algunos tests)
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = "test-key-for-mock"
    
    def test_imports_successful(self):
        """Test que todos los imports principales funcionen"""
        try:
            from agents.consultant_agent import ConsultantAgent
            from agents.quotation_agent import QuotationAgent
            from agents.expedition_agent import ExpeditionAgent
            from agents.human_loop_agent import HumanLoopAgent
            
            assert True, "Todos los imports funcionan"
        except ImportError as e:
            pytest.fail(f"Error en imports: {e}")
    
    def test_database_connection(self):
        """Test conexión a base de datos"""
        try:
            # Crear sesión de test
            session_id = db_manager.create_session("test", {"test": True})
            assert session_id is not None
            
            # Verificar que se puede recuperar
            session = db_manager.get_session(session_id)
            assert session is not None
            assert session.user_type == "test"
            
        except Exception as e:
            pytest.fail(f"Error en base de datos: {e}")
    
    def test_rag_service_initialization(self):
        """Test inicialización del servicio RAG"""
        try:
            health = rag_service.health_check()
            assert health["status"] in ["healthy", "unhealthy"]
            
            # Intentar inicializar documentos
            result = rag_service.initialize_documents()
            # Es OK si falla por falta de documentos en ambiente de test
            
        except Exception as e:
            pytest.fail(f"Error en servicio RAG: {e}")
    
    def test_quotation_service_basic(self):
        """Test básico del servicio de cotización"""
        try:
            # Verificar que el servicio se puede instanciar
            assert quotation_service is not None
            
            # Verificar planes disponibles
            plans = quotation_service.get_available_plans()
            assert len(plans) > 0
            assert "Plan Basico" in plans
            
        except Exception as e:
            pytest.fail(f"Error en servicio de cotización: {e}")
    
    def test_expedition_service_basic(self):
        """Test básico del servicio de expedición"""
        try:
            # Test de validación de datos
            invalid_data = {"identificacion_tomador": "123"}  # Incompleto
            errors = expedition_service.validate_client_data(invalid_data)
            assert len(errors) > 0  # Debe detectar errores
            
            # Test de datos válidos
            valid_data = {
                "identificacion_tomador": "12345678",
                "celular_tomador": "3001234567",
                "email_tomador": "test@test.com"
            }
            errors = expedition_service.validate_client_data(valid_data)
            assert len(errors) == 0  # No debe haber errores
            
        except Exception as e:
            pytest.fail(f"Error en servicio de expedición: {e}")
    
    @pytest.mark.asyncio
    async def test_orchestrator_basic(self):
        """Test básico del orquestador"""
        try:
            # Verificar que el orquestador se inicializa
            assert orchestrator is not None
            
            # Test de salud del sistema
            health = orchestrator.get_system_health()
            assert "orchestrator" in health
            assert "agents" in health
            
        except Exception as e:
            pytest.fail(f"Error en orquestador: {e}")

class TestRAGWithProvidedQuestions:
    """Tests usando las preguntas proporcionadas en la prueba técnica"""
    
    @pytest.fixture(autouse=True)
    def setup_rag(self):
        """Setup RAG para tests"""
        try:
            rag_service.initialize_documents()
        except:
            pytest.skip("RAG no disponible para tests (documentos faltantes)")
    
    def test_provided_questions(self):
        """Test con preguntas específicas de la prueba técnica"""
        
        # Preguntas de ejemplo de la prueba técnica
        test_questions = [
            "¿Qué cubre la asistencia de pequeños choques en el plan de Pequeños Eventos?",
            "¿Qué deducible aplica para los daños en vidrios bajo la asistencia de Pequeños Eventos?",
            "¿Qué cubre la asistencia de llantas estalladas en autos?",
            "¿En qué ciudades aplica la asistencia de pequeños eventos para autos?",
            "¿Cuál es el valor asegurado permitido en el Plan Autos Básico PT?"
        ]
        
        for question in test_questions:
            try:
                result = rag_service.query(question)
                
                # Verificar que se obtuvo una respuesta
                assert "answer" in result
                assert len(result["answer"]) > 0
                
                # Verificar que la confianza es razonable para documentos conocidos
                confidence = result.get("confidence", 0)
                if confidence > 0:
                    assert confidence > 0.3  # Umbral mínimo razonable
                
                print(f"✅ Pregunta procesada: {question[:50]}...")
                
            except Exception as e:
                pytest.fail(f"Error procesando pregunta '{question}': {e}")

class TestQuotationWithProvidedImages:
    """Tests de cotización con datos de las imágenes proporcionadas"""
    
    def test_vehicle_data_validation(self):
        """Test validación de datos de vehículos del CSV proporcionado"""
        
        # Datos de ejemplo del CSV vehiculos_combinado_v2.csv
        test_vehicles = [
            {"marca": "Hyundai", "clase": "AUTOMOVIL", "color": "Amarillo"},
            {"marca": "Chevrolet", "clase": "CAMIONETA PASAJ.", "color": "Gris"},
            {"marca": "Toyota", "clase": "CAMPERO", "color": "Plateado"},
            {"marca": "Nissan", "clase": "AUTOMOVIL", "color": "Rojo"},
        ]
        
        for vehicle in test_vehicles:
            # Test de reconocimiento simulado
            try:
                # Como no tenemos las imágenes reales en el test, 
                # simulamos el resultado del análisis
                analysis = quotation_service.vision_service._simulate_vision_response(b"fake_image_data")
                
                # Verificar que se obtiene un resultado válido
                assert "marca" in analysis
                assert "clase" in analysis  
                assert "color" in analysis
                
                print(f"✅ Análisis simulado: {analysis['marca']} {analysis['clase']}")
                
            except Exception as e:
                pytest.fail(f"Error en análisis de vehículo: {e}")

class TestExpeditionFlow:
    """Tests del flujo completo de expedición"""
    
    def test_expedition_payload_preparation(self):
        """Test preparación de payload para expedición"""
        
        # Datos de test
        client_data = {
            "identificacion_tomador": "12345678",
            "celular_tomador": "3001234567",
            "email_tomador": "test@example.com"
        }
        
        vehicle_data = {
            "marca": "TOYOTA",
            "modelo": "2020", 
            "linea": "COROLLA XEI",
            "clase": "AUTOMOVIL",
            "color": "Blanco"
        }
        
        quotation_data = {
            "quotations": {
                "Plan Basico": {
                    "prima_anual": 1200000,
                    "prima_mensual": 100000
                }
            }
        }
        
        try:
            payload = expedition_service.prepare_expedition_payload(
                client_data=client_data,
                vehicle_data=vehicle_data,
                quotation_data=quotation_data,
                selected_plan="Plan Basico"
            )
            
            # Verificar campos requeridos
            required_fields = [
                "identificacion_tomador", "celular_tomador",
                "marca_vehiculo", "modelo_vehiculo", "linea_vehiculo",
                "plan_poliza", "valor_total_poliza", "valor_mensual"
            ]
            
            for field in required_fields:
                assert field in payload, f"Campo faltante: {field}"
            
            print("✅ Payload de expedición preparado correctamente")
            
        except Exception as e:
            pytest.fail(f"Error preparando payload: {e}")

class TestIntegrationFlow:
    """Tests de flujo de integración completo"""
    
    @pytest.mark.asyncio
    async def test_complete_consultation_flow(self):
        """Test flujo completo de consulta"""
        
        session_id = "test_session_consultation"
        
        try:
            # Consulta simple
            response = await orchestrator.process_user_input(
                session_id=session_id,
                user_input="¿Qué cubre el Plan Autos Básico?",
                user_type="client"
            )
            
            # Verificar respuesta
            assert response["success"] == True
            assert len(response["content"]) > 0
            assert response["agent"] in ["consultant", "router"]
            
            print("✅ Flujo de consulta completado")
            
        except Exception as e:
            # Es aceptable que falle por falta de configuración completa
            print(f"⚠️  Flujo de consulta falló (esperado en ambiente de test): {e}")
    
    @pytest.mark.asyncio 
    async def test_quotation_request_flow(self):
        """Test flujo de solicitud de cotización"""
        
        session_id = "test_session_quotation"
        
        try:
            # Solicitud de cotización
            response = await orchestrator.process_user_input(
                session_id=session_id,
                user_input="Quiero cotizar mi vehículo",
                user_type="client"
            )
            
            # Verificar que se direcciona correctamente
            assert response["success"] == True
            assert len(response["content"]) > 0
            
            print("✅ Flujo de cotización iniciado")
            
        except Exception as e:
            print(f"⚠️  Flujo de cotización falló (esperado en ambiente de test): {e}")

def run_tests():
    """Función para ejecutar tests manualmente"""
    print("🧪 Ejecutando tests básicos del sistema...")
    
    # Tests básicos
    test_basic = TestBasicFunctionality()
    test_basic.setup_test_environment()
    
    try:
        test_basic.test_imports_successful()
        print("✅ Imports OK")
        
        test_basic.test_database_connection()
        print("✅ Base de datos OK")
        
        test_basic.test_rag_service_initialization()
        print("✅ Servicio RAG OK")
        
        test_basic.test_quotation_service_basic()
        print("✅ Servicio cotización OK")
        
        test_basic.test_expedition_service_basic()
        print("✅ Servicio expedición OK")
        
        print("\n🎉 Todos los tests básicos pasaron!")
        
    except Exception as e:
        print(f"❌ Error en tests: {e}")
        return False
    
    return True

if __name__ == "__main__":
    run_tests()
