from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LogRecord(BaseModel):
    carga_id: str = Field(..., description="ID único de la carga")
    fecha_inicio: datetime = Field(..., description="Fecha y hora de inicio")
    fecha_fin: datetime = Field(..., description="Fecha y hora de fin")
    archivo_url: str = Field(..., description="URL o ruta del archivo procesado")
    errores: Optional[List[str]] = Field(default_factory=list, description="Lista de errores encontrados")
    estado: str = Field(..., description="Estado final del proceso (OK/ERROR)")