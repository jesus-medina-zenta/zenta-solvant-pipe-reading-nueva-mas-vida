"""
Data models using Pydantic for validation.
"""
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from src.models.metadata_user import MetadataUser



class DataRecord(BaseModel):
    fecha: datetime = Field(..., description="Fecha y hora de inicio")
    id: str = Field(..., description="ID de la carga")
    phone_number: str = Field(..., max_length=15, description="Teléfono principal")
    phone_number_2: str = Field(..., max_length=15, description="Teléfono secundario")
    metadata_user: MetadataUser = Field(..., description="Datos del usuario agrupados")

    @classmethod
    def from_line(cls, line: str, carga_id: str) -> "DataRecord":
        """Crea un DataRecord desde una línea del archivo TXT"""
        metadata = MetadataUser(
            queue=line[0:4].strip(),
            queue_id_cyber=line[0:4].strip(),
            rut=line[4:12].strip() + line[12:13].strip(),
            name=line[48:128].strip(),
            paternal_surname=line[128:208].strip(),
            maternal_surname=line[208:212].strip(),
            days_overdue=line[473:478].strip(),
            monthly_payment=line[478:493].strip(),
            down_payment_option1=line[508:523].strip(),
            process_date=line[572:582].strip(),
            overdue_date1=line[586:596].strip(),
            overdue_amount1=line[596:611].strip(),
            email=line[822:882].strip(),
            card=line[902:908].strip(),
            expiration_date=line[1008:1018].strip(),
        )
        return cls(
            id=carga_id,
            phone_number=f"+56{line[377:392].strip()}",
            phone_number_2=f"+56{line[397:412].strip()}",
            metadata_user=metadata
        )
    
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
    def from_dict(cls, data: Dict[str, Any], carga_id: str, fecha_utc) -> "DataRecord":
        """Crea un DataRecord desde un diccionario de datos"""
        metadata = MetadataUser(
            queue=data.get('queue', '').strip(),
            queue_id_cyber=data.get('queue_id_cyber', '').strip(),
            rut=data.get('rut', '').strip(),
            name=data.get('name', '').strip(),
            paternal_surname=data.get('paternal_surname', '').strip(),
            maternal_surname=data.get('maternal_surname', '').strip(),
            days_overdue=data.get('days_overdue', '').strip(),
            monthly_payment=data.get('monthly_payment', '').strip(),
            down_payment_option1=data.get('down_payment_option1', '').strip(),
            process_date=data.get('process_date', '').strip(),
            overdue_date1=data.get('overdue_date1', '').strip(),
            overdue_amount1=data.get('overdue_amount1', '').strip(),
            email=data.get('email', '').strip(),
            card=data.get('card', '').strip(),
            expiration_date=data.get('expiration_date', '').strip(),
        )

        # Extraer fecha e ID de carga (format: "16092025-uuid")
        if '-' in carga_id:
            id_parte = carga_id.split('-', 1)[1]  # Todo después del primer guión
        else:
            id_parte = carga_id
        # Extraer y limpiar números de teléfono
        personal_phone = data.get('personal_phone', '').strip()
        cell_phone = data.get('cell_phone', '').strip()
        
        # Formatear teléfonos
        phone_1 = f"+56{personal_phone}" if personal_phone else ""
        phone_2 = f"+56{cell_phone}" if cell_phone else ""

        #validar phone's
        if not phone_1 or phone_1 == "+56":
            raise ValueError("El teléfono principal es obligatorio y no puede ser solo el código de país.")
        
        return cls(
            fecha=fecha_utc,
            id=id_parte,
            phone_number=phone_1[:15],  # Truncar a 15 caracteres
            phone_number_2=phone_2[:15],  # Truncar a 15 caracteres
            metadata_user=metadata
        )

    def is_valid(self) -> bool:
        """Validates that critical fields are present, including phone_number."""
        return bool(
            self.phone_number and self.phone_number.strip() and self.phone_number != "+56" and
            self.metadata_user.queue and self.metadata_user.queue.strip() and
            self.metadata_user.rut and self.metadata_user.rut.strip() and
            self.metadata_user.name and self.metadata_user.name.strip()
        )
    
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
    
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Example record",
                "value": 100.50,
                "category": "example",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "metadata": {"source": "api", "version": "1.0"}
            }
        }
    )


class ProcessingStats(BaseModel):
    """
    Model for pipeline processing statistics.
    """
    
    total_records: int = Field(0, description="Total records processed")
    successful_records: int = Field(0, description="Successfully processed records")
    failed_records: int = Field(0, description="Failed records")
    processing_time_seconds: float = Field(0.0, description="Total processing time in seconds")
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Start time")
    end_time: Optional[datetime] = Field(None, description="End time")
    
    @property
    def success_rate(self) -> float:
        """Calculates the processing success rate."""
        if self.total_records == 0:
            return 0.0
        return (self.successful_records / self.total_records) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculates the processing failure rate."""
        return 100.0 - self.success_rate
    
    def add_success(self) -> None:
        """Increments the successful records counter."""
        self.successful_records += 1
        self.total_records += 1
    
    def add_failure(self) -> None:
        """Increments the failed records counter."""
        self.failed_records += 1
        self.total_records += 1
    
    def finish(self) -> None:
        """Marks processing as finished."""
        self.end_time = datetime.now(datetime.timezone.utc)
        if self.start_time:
            self.processing_time_seconds = (self.end_time - self.start_time).total_seconds()


class ErrorRecord(BaseModel):
    """
    Model for recording errors during processing.
    """
    
    record_id: Optional[str] = Field(None, description="ID of the record that caused the error")
    error_type: str = Field(..., description="Error type")
    error_message: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")
    stage: str = Field(..., description="Pipeline stage where the error occurred")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw data that caused the error")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "record_id": "123",
                "error_type": "ValidationError",
                "error_message": "Field 'name' is required",
                "timestamp": "2023-01-01T12:00:00Z",
                "stage": "transform",
                "raw_data": {"id": 123, "value": 100}
            }
        }
    )


class PipelineConfig(BaseModel):
    """
    Model for pipeline-specific configuration.
    """
    
    source_query: Optional[str] = Field(None, description="SQL query to extract data")
    batch_size: int = Field(1000, gt=0, description="Batch size for processing")
    max_retries: int = Field(3, ge=0, description="Maximum number of retries")
    enable_validation: bool = Field(True, description="Enable data validation")
    output_format: str = Field("json", description="Output format")
    custom_filters: Optional[Dict[str, Any]] = Field(None, description="Custom filters")
    
    @field_validator('output_format')
    @classmethod
    def validate_output_format(cls, v):
        """Validates that the output format is supported."""
        supported_formats = ['json', 'csv', 'parquet']
        if v not in supported_formats:
            raise ValueError(f'Unsupported format. Use one of: {supported_formats}')
        return v