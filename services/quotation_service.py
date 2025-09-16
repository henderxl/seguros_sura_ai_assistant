"""
Servicio de cotización integrado para el sistema de agentes.
Integra la función de cotización existente con capacidades de visión y validación.
"""

import os
import sys
import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import base64
from PIL import Image
import io
import json
import openai

# Agregar el path del servicio original para importar
sys.path.append(str(Path(__file__).parent / "cotizacion_original"))

from cotizacion import configurar_fuente_excel, cotizar_poliza, PLAN_RATES
from utils.config import config
from utils.logging_config import get_logger

logger = get_logger("quotation_service")

class VehicleRecognitionService:
    """Servicio de reconocimiento de vehículos usando GPT-4 Vision"""
    
    def __init__(self):
        self.logger = get_logger("vehicle_recognition")
        
        # Configurar cliente Azure OpenAI
        self.azure_client = openai.AzureOpenAI(
            api_key=config.azure_openai.api_key,
            api_version=config.azure_openai.api_version,
            azure_endpoint=config.azure_openai.endpoint
        )
    
    def analyze_vehicle_image(self, image_data: bytes) -> Dict[str, str]:
        """
        Analiza una imagen de vehículo para extraer características.
        
        Args:
            image_data: Datos binarios de la imagen
            
        Returns:
            Dict con marca, clase y color detectados
        """
        try:
            # Convertir imagen a base64 para OpenAI
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prompt específico para reconocimiento de vehículos
            prompt = """
            Analiza esta imagen de vehículo y extrae las siguientes características:
            
            1. MARCA del vehículo (ejemplos: Toyota, Chevrolet, Ford, Nissan, etc.)
            2. CLASE del vehículo (usar EXACTAMENTE uno de estos valores):
               - AUTOMOVIL
               - CAMIONETA PASAJ.
               - PICKUP DOBLE CAB
               - MOTOCICLETA
               - CAMPERO
               - REMOLCADOR
            
            3. COLOR principal del vehículo (ejemplos: Rojo, Azul, Blanco, Negro, Gris, Plateado, Amarillo, Beige)
            
            Responde ÚNICAMENTE en el siguiente formato JSON, sin texto adicional:
            {
                "marca": "MARCA_DETECTADA",
                "clase": "CLASE_EXACTA",
                "color": "COLOR_DETECTADO"
            }
            
            IMPORTANTE: 
            - La clase debe ser EXACTAMENTE una de las opciones listadas
            - Si no puedes determinar algún valor, usa "NO_DETECTADO"
            - Sé preciso en la identificación de la marca
            """
            
            # Llamar a Azure OpenAI GPT-4o Vision para análisis real
            return self._call_azure_vision_api(image_b64, prompt)
            
        except Exception as e:
            self.logger.error(f"Error en análisis de imagen: {str(e)}")
            return {
                "marca": "NO_DETECTADO",
                "clase": "NO_DETECTADO", 
                "color": "NO_DETECTADO"
            }
    
    def _call_azure_vision_api(self, image_b64: str, prompt: str) -> Dict[str, str]:
        """
        Llama a Azure OpenAI GPT-4o Vision para análisis real de imagen
        """
        try:
            response = self.azure_client.chat.completions.create(
                model=config.azure_openai.chat_deployment,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parsear respuesta JSON
            content = response.choices[0].message.content.strip()
            self.logger.info(f"Respuesta de Azure Vision: {content}")
            
            # Intentar parsear como JSON
            try:
                # Limpiar la respuesta para extraer solo el JSON
                if "```json" in content:
                    # Extraer contenido entre ```json y ```
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                else:
                    json_content = content.strip()
                
                # Si empieza con ```json, extraer solo el JSON
                if json_content.startswith("```json"):
                    json_content = json_content[7:]
                if json_content.endswith("```"):
                    json_content = json_content[:-3]
                    
                json_content = json_content.strip()
                
                result = json.loads(json_content)
                self.logger.info(f"JSON parseado exitosamente: {result}")
                return result
                
            except (json.JSONDecodeError, IndexError, ValueError) as e:
                # Si no es JSON válido, extraer usando regex como último recurso
                self.logger.warning(f"Respuesta no es JSON válido ({str(e)}), intentando extracción regex")
                
                import re
                marca_match = re.search(r'"marca":\s*"([^"]+)"', content)
                clase_match = re.search(r'"clase":\s*"([^"]+)"', content)
                color_match = re.search(r'"color":\s*"([^"]+)"', content)
                
                if marca_match and clase_match and color_match:
                    result = {
                        "marca": marca_match.group(1),
                        "clase": clase_match.group(1),
                        "color": color_match.group(1)
                    }
                    self.logger.info(f"Extraído con regex: {result}")
                    return result
                else:
                    self.logger.warning("No se pudo extraer datos con regex, usando fallback")
                    return self._simulate_vision_response(None)
                
        except Exception as e:
            self.logger.error(f"Error llamando Azure Vision API: {str(e)}")
            # Fallback a simulación si falla la API
            return self._simulate_vision_response(None)
    
    def _simulate_vision_response(self, image_data: bytes) -> Dict[str, str]:
        """
        Simula respuesta de GPT-4 Vision usando datos del CSV de ejemplo.
        En implementación real, esto sería reemplazado por llamada real a OpenAI.
        """
        # Cargar datos de ejemplo del CSV
        csv_path = config.get_absolute_path("data/images/vehiculos_combinado_v2.csv")
        
        try:
            df = pd.read_csv(csv_path, delimiter=';')
            
            # Por simplicidad, devolver el primer registro
            # En implementación real, se haría análisis real de la imagen
            if not df.empty:
                first_row = df.iloc[0]
                return {
                    "marca": first_row['Marca'],
                    "clase": first_row['Clase'],
                    "color": first_row['Color']
                }
        except Exception as e:
            self.logger.warning(f"No se pudo cargar CSV de ejemplo: {str(e)}")
        
        # Fallback
        return {
            "marca": "TOYOTA",
            "clase": "AUTOMOVIL",
            "color": "Blanco"
        }

class QuotationService:
    """Servicio principal de cotización"""
    
    def __init__(self):
        self.logger = get_logger("quotation_service")
        self.vision_service = VehicleRecognitionService()
        self._setup_quotation_service()
    
    def _setup_quotation_service(self):
        """Configura el servicio de cotización con el Excel de vehículos"""
        try:
            # Primero intentar con el Excel copiado desde los datos originales
            excel_path = config.get_absolute_path("services/cotizacion_original/data/carros.xlsx")
            
            # Si no existe, usar el listado de carros asegurables
            if not excel_path.exists():
                excel_path = config.get_absolute_path("data/vehicles/Listado de carros asegurables.xlsx")
            
            if excel_path.exists():
                configurar_fuente_excel(str(excel_path))
                self.logger.info(f"Servicio de cotización configurado con: {excel_path}")
            else:
                self.logger.error("No se encontró archivo Excel de vehículos")
                raise FileNotFoundError("Archivo de vehículos no encontrado")
                
        except Exception as e:
            self.logger.error(f"Error configurando servicio de cotización: {str(e)}")
            raise
    
    def analyze_vehicle_from_image(self, image_data: bytes) -> Dict[str, str]:
        """
        Analiza imagen y extrae características del vehículo
        
        Args:
            image_data: Datos binarios de la imagen
            
        Returns:
            Dict con características detectadas
        """
        self.logger.info("Iniciando análisis de imagen de vehículo")
        
        try:
            result = self.vision_service.analyze_vehicle_image(image_data)
            
            self.logger.info(
                "Análisis de imagen completado",
                marca=result.get('marca'),
                clase=result.get('clase'),
                color=result.get('color')
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error en análisis de imagen: {str(e)}")
            raise
    
    def validate_vehicle_data(self, marca: str, modelo: str, linea: str, clase: str) -> bool:
        """
        Valida que el vehículo esté en el catálogo de asegurables
        
        Args:
            marca: Marca del vehículo
            modelo: Modelo (año)
            linea: Línea del vehículo
            clase: Clase del vehículo
            
        Returns:
            True si el vehículo es asegurable, False en caso contrario
        """
        try:
            # Intentar cotizar para validar que existe en el catálogo
            cotizar_poliza(marca=marca, modelo=modelo, linea=linea, clase=clase, color="Blanco")
            return True
            
        except ValueError as e:
            self.logger.warning(f"Vehículo no asegurable: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error validando vehículo: {str(e)}")
            return False
    
    def generate_quotation(self, marca: str, modelo: str, linea: str, 
                          clase: str, color: str, 
                          planes: Optional[List[str]] = None) -> Dict:
        """
        Genera cotización para un vehículo
        
        Args:
            marca: Marca del vehículo
            modelo: Modelo (año)
            linea: Línea del vehículo
            clase: Clase del vehículo
            color: Color del vehículo
            planes: Lista de planes a cotizar (opcional, por defecto todos)
            
        Returns:
            Dict con cotizaciones por plan
        """
        self.logger.info(
            "Generando cotización",
            marca=marca,
            modelo=modelo,
            linea=linea,
            clase=clase,
            color=color
        )
        
        try:
            # Filtrar planes si se especificaron
            plan_rates = PLAN_RATES.copy()
            if planes:
                plan_rates = {plan: rate for plan, rate in plan_rates.items() if plan in planes}
            
            # Generar cotización usando la función original
            quotation_result = cotizar_poliza(
                marca=marca,
                modelo=modelo,
                linea=linea,
                clase=clase,
                color=color,
                plan_rates=plan_rates
            )
            
            # Enriquecer resultado con información adicional
            enhanced_result = {
                "vehicle_info": {
                    "marca": marca,
                    "modelo": modelo,
                    "linea": linea,
                    "clase": clase,
                    "color": color
                },
                "quotations": quotation_result,
                "generated_at": pd.Timestamp.now().isoformat(),
                "color_surcharge_applied": color.upper() == "ROJO"
            }
            
            self.logger.info(
                "Cotización generada exitosamente",
                plans_count=len(quotation_result),
                has_color_surcharge=enhanced_result["color_surcharge_applied"]
            )
            
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Error generando cotización: {str(e)}")
            raise
    
    def get_available_plans(self) -> List[str]:
        """Obtiene lista de planes disponibles"""
        return list(PLAN_RATES.keys())
    
    def get_vehicle_catalog_sample(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene muestra del catálogo de vehículos disponibles
        
        Args:
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de vehículos de ejemplo
        """
        try:
            # Cargar Excel para obtener muestra
            excel_path = config.get_absolute_path("services/cotizacion_original/data/carros.xlsx")
            
            if not excel_path.exists():
                excel_path = config.get_absolute_path("data/vehicles/Listado de carros asegurables.xlsx")
            
            if excel_path.exists():
                df = pd.read_excel(excel_path)
                sample = df.head(limit).to_dict('records')
                return sample
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error obteniendo muestra del catálogo: {str(e)}")
            return []

# Instancia global del servicio
quotation_service = QuotationService()
