"""
Data models using Pydantic for validation.
"""
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from ..utils.logger import get_logger
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from src.models.metadata_user import MetadataUser
logger = get_logger(__name__)

class DataRecord(BaseModel):
    fecha: datetime = Field(..., description="Fecha y hora de inicio")
    id: str = Field(..., description="ID de la carga")
    phone_number: str = Field(..., max_length=15, description="Teléfono principal")
    phone_number_2: Optional[str] = Field("", max_length=15, description="Teléfono secundario")
    metadata_user: MetadataUser = Field(..., description="Datos del usuario agrupados")

    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Valida que el teléfono principal no esté vacío"""
        if not v or v.strip() == "" or v.strip() == "+56":
            raise ValueError('phone_number es requerido y no puede estar vacío')
        return v.strip()

    @field_validator('phone_number_2')
    @classmethod
    def validate_phone_number_2(cls, v):
        """Valida el teléfono secundario (opcional)"""
        if v is not None and (v.strip() == "" or v.strip() == "+56"):
            return None  # Convertir string vacío a None
        return v.strip() if v else None

    @model_validator(mode='after')
    def validate_at_least_one_phone(self):
        """Valida que al menos phone_number tenga un valor válido"""
        if not self.phone_number or self.phone_number.strip() == "" or self.phone_number.strip() == "+56":
            raise ValueError('Debe tener al menos un número de teléfono válido (phone_number)')
        return self
    
    @classmethod
    def _extract_field(cls, line: str, start: int, end: int, field_name: str, strip: bool = True) -> str:
        """
        Extrae un campo de una línea de texto de ancho fijo con manejo de excepciones.
        
        Args:
            line: Línea de texto de origen
            start: Posición inicial (0-indexed)
            end: Posición final (exclusiva)
            field_name: Nombre del campo para logging de errores
            strip: Si debe remover espacios en blanco
            
        Returns:
            str: Campo extraído
            
        Raises:
            ValueError: Si hay error en la extracción del campo
        """
        try:
            if not line:
                raise ValueError(f"Línea vacía para extraer campo '{field_name}'")
            
            if start < 0 or end < 0:
                raise ValueError(f"Posiciones negativas no permitidas para campo '{field_name}' (start={start}, end={end})")
            
            if start >= end:
                raise ValueError(f"Posición inicial debe ser menor que final para campo '{field_name}' (start={start}, end={end})")
            
            if end > len(line):
                logger.warning(f"Campo '{field_name}': línea más corta que esperado (longitud={len(line)}, end={end})")
                # Ajustar end a la longitud de la línea
                end = len(line)
            
            if start >= len(line):
                logger.warning(f"Campo '{field_name}': posición inicial fuera de rango (start={start}, longitud={len(line)})")
                return ""
            
            extracted = line[start:end]
            result = extracted.strip() if strip else extracted
            
            logger.debug(f"Campo '{field_name}' extraído: posiciones [{start}:{end}] = '{result}'")
            return result
            
        except Exception as e:
            error_msg = f"Error extrayendo campo '{field_name}' en posiciones [{start}:{end}]: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "id": "16092025-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "phone_number": "+56912345678",
                "phone_number_2": "+56987654321",
                "metadata_user": {
                    "queue": "PRA3",
                    "rut": "12345678-9",
                    "name": "Juan Pérez"
                }
            }
        }
    )

