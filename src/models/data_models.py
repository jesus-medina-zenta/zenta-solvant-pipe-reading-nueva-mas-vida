"""
Data models using Pydantic for validation.
"""
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class DataRecord(BaseModel):
    queue: str = Field(..., min_length=1, max_length=4, description="Queue code")
    queue_id_cyber: str = Field(..., min_length=1, max_length=4, description="Cyber queue ID")
    rut: str = Field(..., min_length=1, max_length=9, description="RUT with verification digit")
    name: str = Field(..., min_length=1, max_length=80, description="Name")
    paternal_surname: str = Field(..., min_length=1, max_length=80, description="Paternal surname")
    maternal_surname: str = Field(..., min_length=1, max_length=4, description="Maternal surname")
    personal_area_code: str = Field(..., max_length=5, description="Personal phone area code")
    personal_phone: str = Field(..., max_length=15, description="Personal phone")
    personal_cell_area_code: str = Field(..., max_length=5, description="Personal cell phone area code")
    personal_cell_phone: str = Field(..., max_length=15, description="Personal cell phone")
    cell_area_code: str = Field(..., max_length=5, description="Cell phone area code")
    cell_phone: str = Field(..., max_length=15, description="Cell phone")
    reference_area_code: str = Field(..., max_length=5, description="Reference phone area code")
    reference_phone: str = Field(..., max_length=15, description="Reference phone")
    days_overdue: str = Field(..., max_length=5, description="Days overdue")
    monthly_payment: str = Field(..., max_length=15, description="Monthly payment amount")
    down_payment_option1: str = Field(..., description="Down payment option 1")
    process_date: str = Field(..., description="Process date")
    overdue_date1: str = Field(..., description="Overdue date 1")
    overdue_amount1: str = Field(..., description="Overdue amount 1")
    email: str = Field(..., description="Email address")
    card: str = Field(..., description="Card number")
    expiration_date: str = Field(..., description="Expiration date")

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        """Validates that the name is not empty."""
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
    
   # @field_validator('value')
   # @classmethod
   # def value_must_be_positive_if_present(cls, v):
    #    """Validates that the value is positive if present."""
    #    if v is not None and v < 0:
    #        raise ValueError('Value must be positive')
    #   return v
    
    #@model_validator(mode='after')
    #def validate_updated_at_after_created_at(self):
    #    """Validates that updated_at is after created_at."""
    #    if self.updated_at and self.created_at and self.updated_at < self.created_at:
    #        raise ValueError('Update date must be after creation date')
    #    return self
    
    def is_valid(self) -> bool:
        """Validates that critical fields are present."""
        return bool(
            self.queue and self.queue.strip() and
            self.rut and self.rut.strip() and
            self.name and self.name.strip()
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