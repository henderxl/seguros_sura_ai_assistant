"""
Servicio de expedición de pólizas integrado.
Cliente para la API de expedición existente con validaciones y logging.
"""

import requests
import json
from typing import Dict, Optional
from datetime import datetime

from utils.config import config
from utils.logging_config import get_logger

logger = get_logger("expedition_service")

class ExpeditionService:
    """Servicio para expedición de pólizas usando la API Flask existente"""
    
    def __init__(self, api_base_url: Optional[str] = None):
        self.api_base_url = api_base_url or "http://localhost:8000"
        self.logger = get_logger("expedition_service")
    
    def validate_client_data(self, client_data: Dict) -> Dict[str, str]:
        """
        Valida datos del cliente antes de expedición
        
        Args:
            client_data: Datos del cliente a validar
            
        Returns:
            Dict con errores de validación (vacío si todo está correcto)
        """
        errors = {}
        
        # Campos requeridos según la API
        required_fields = [
            "identificacion_tomador",
            "celular_tomador",
            "email_tomador"  # Agregamos email como requerido
        ]
        
        for field in required_fields:
            if field not in client_data or not client_data[field]:
                errors[field] = f"Campo {field} es requerido"
        
        # Validaciones específicas
        if "identificacion_tomador" in client_data:
            cedula = str(client_data["identificacion_tomador"]).strip()
            if not cedula.isdigit() or len(cedula) < 6 or len(cedula) > 12:
                errors["identificacion_tomador"] = "Cédula debe tener entre 6 y 12 dígitos"
        
        if "celular_tomador" in client_data:
            celular = str(client_data["celular_tomador"]).strip()
            if not celular.isdigit() or len(celular) != 10:
                errors["celular_tomador"] = "Celular debe tener exactamente 10 dígitos"
        
        if "email_tomador" in client_data:
            email = client_data["email_tomador"].strip()
            if "@" not in email or "." not in email:
                errors["email_tomador"] = "Email debe tener formato válido"
        
        return errors
    
    def prepare_expedition_payload(self, client_data: Dict, vehicle_data: Dict, 
                                 quotation_data: Dict, selected_plan: str) -> Dict:
        """
        Prepara payload para expedición según formato requerido por la API
        
        Args:
            client_data: Datos del cliente
            vehicle_data: Datos del vehículo
            quotation_data: Datos de la cotización
            selected_plan: Plan seleccionado
            
        Returns:
            Dict con payload formateado para la API
        """
        try:
            # Obtener datos de la cotización para el plan seleccionado
            plan_quote = quotation_data["quotations"][selected_plan]
            
            payload = {
                # Datos del tomador
                "identificacion_tomador": str(client_data["identificacion_tomador"]),
                "celular_tomador": str(client_data["celular_tomador"]),
                
                # Datos del vehículo
                "marca_vehiculo": vehicle_data["marca"],
                "modelo_vehiculo": vehicle_data["modelo"],
                "linea_vehiculo": vehicle_data["linea"],
                "clase_vehiculo": vehicle_data["clase"],
                "color_vehiculo": vehicle_data["color"],
                
                # Datos de la póliza
                "plan_poliza": selected_plan,
                "valor_total_poliza": str(int(plan_quote["prima_anual"])),
                "valor_mensual": str(int(plan_quote["prima_mensual"]))
            }
            
            self.logger.info(
                "Payload preparado para expedición",
                cedula=payload["identificacion_tomador"],
                plan=selected_plan,
                valor_anual=payload["valor_total_poliza"]
            )
            
            return payload
            
        except Exception as e:
            self.logger.error(f"Error preparando payload: {str(e)}")
            raise ValueError(f"Error preparando datos para expedición: {str(e)}")
    
    def expedite_policy(self, expedition_payload: Dict) -> Dict:
        """
        Expide una póliza usando la API Flask
        
        Args:
            expedition_payload: Datos formateados para expedición
            
        Returns:
            Dict con resultado de la expedición
        """
        self.logger.info(
            "Iniciando expedición de póliza",
            cedula=expedition_payload.get("identificacion_tomador"),
            plan=expedition_payload.get("plan_poliza")
        )
        
        try:
            # Llamada a la API de expedición
            response = requests.post(
                f"{self.api_base_url}/expedir-poliza",
                json=expedition_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                
                self.logger.info(
                    "Póliza expedida exitosamente",
                    numero_poliza=result.get("numero_poliza"),
                    cedula=expedition_payload.get("identificacion_tomador")
                )
                
                return {
                    "success": True,
                    "numero_poliza": result["numero_poliza"],
                    "mensaje": result["mensaje"],
                    "archivo_poliza": result.get("archivo"),
                    "fecha_expedicion": datetime.now().isoformat()
                }
            
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", f"Error HTTP {response.status_code}")
                
                self.logger.error(
                    "Error en expedición de póliza",
                    status_code=response.status_code,
                    error=error_msg,
                    cedula=expedition_payload.get("identificacion_tomador")
                )
                
                return {
                    "success": False,
                    "error": error_msg,
                    "details": error_data
                }
        
        except requests.RequestException as e:
            self.logger.error(f"Error de conexión con API de expedición: {str(e)}")
            return {
                "success": False,
                "error": "Error de conexión con el sistema de expedición",
                "details": str(e)
            }
        
        except Exception as e:
            self.logger.error(f"Error inesperado en expedición: {str(e)}")
            return {
                "success": False,
                "error": "Error interno durante la expedición",
                "details": str(e)
            }
    
    def get_policy_status(self, numero_poliza: str) -> Dict:
        """
        Consulta el estado de una póliza (funcionalidad extendida)
        
        Args:
            numero_poliza: Número de la póliza a consultar
            
        Returns:
            Dict con información de la póliza
        """
        try:
            # En la implementación actual, verificar si existe el archivo
            import os
            policy_file = f"services/expedition_api/polizas/{numero_poliza}.json"
            
            if os.path.exists(policy_file):
                with open(policy_file, 'r', encoding='utf-8') as f:
                    policy_data = json.load(f)
                
                return {
                    "exists": True,
                    "numero_poliza": numero_poliza,
                    "data": policy_data
                }
            else:
                return {
                    "exists": False,
                    "numero_poliza": numero_poliza,
                    "message": "Póliza no encontrada"
                }
        
        except Exception as e:
            self.logger.error(f"Error consultando póliza {numero_poliza}: {str(e)}")
            return {
                "exists": False,
                "error": str(e)
            }
    
    def health_check(self) -> bool:
        """
        Verifica si la API de expedición está disponible
        
        Returns:
            True si la API responde, False en caso contrario
        """
        try:
            # Intentar hacer una petición simple (podría ser un endpoint de health)
            response = requests.get(
                f"{self.api_base_url}/",
                timeout=5
            )
            return response.status_code < 500
            
        except Exception:
            return False

# Instancia global del servicio
expedition_service = ExpeditionService()
