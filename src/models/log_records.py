from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LogRecord(BaseModel):
    id: str = Field(..., description="ID único de la carga")
    start_date: datetime = Field(..., description="Fecha y hora de inicio")
    end_date: datetime = Field(..., description="Fecha y hora de fin")
    file_url: str = Field(..., description="URL o ruta del archivo procesado")
    errors: Optional[List[str]] = Field(default_factory=list, description="Lista de errores encontrados")
    status: str = Field(..., description="Estado final del proceso (OK/ERROR)")