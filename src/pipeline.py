from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from uuid import uuid4
import os


from .config import get_sftp_config
from .services.sftp_service import SFTPService
from .models.data_models import DataRecord
from src.models.log_records import LogRecord
from src.services.firestore_service import FirestoreService 
from .utils.logger import get_logger

logger = get_logger(__name__)

class Pipeline:
    """
    Pipeline principal para procesamiento ETL usando SFTP como fuente.
    """
    def __init__(self):
        self.sftp_service = SFTPService(get_sftp_config())
        self.firestore_service = FirestoreService()
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.file_url = os.getenv("PIPELINE_FILE_URL")

    async def run(self) -> bool:
        self.start_time = datetime.now(timezone.utc)
        fecha = datetime.now().strftime("%d%m%Y")
        fecha_utc = datetime.now(timezone.utc)
        id = f"{fecha}-{uuid4()}"
        start_date: list = []
        file_url = self.file_url
        status = "OK"
        error_list = [] 
        logger.info("Iniciando ejecución del pipeline")

        try:
            # Paso 1: Extract
            logger.info("Iniciando extracción de datos")
            raw_data = self.extract()
            logger.info(f"Extraídos {len(raw_data)} registros")

            if not raw_data:
                logger.warning("No se encontraron datos para procesar")
                status = "NO_DATA"
                error_list.append("No se encontraron datos para procesar")
                return True

            # Paso 2: Transform
            logger.info("Iniciando transformación de datos")
            transformed_data, transform_errors = await self.transform(raw_data, id, fecha_utc)
            error_list.extend(transform_errors)  # Agregar errores específicos de transformación
            logger.info(f"Transformados {len(transformed_data)} registros")

            if not transformed_data and raw_data:
                logger.error("No se pudo transformar ningún registro")
                status = "TRANSFORM_ERROR"
                return False

            # Paso 3: Load
            logger.info("Iniciando carga de datos")
            success, load_errors = await self.load(transformed_data, id)
            error_list.extend(load_errors)  # Agregar errores de carga

            if success:
                logger.info("Pipeline completado exitosamente")
                status = "SUCCESS" if not error_list else "SUCCESS_WITH_ERRORS"
                return True
            else:
                logger.error("Error en la carga de datos")
                status = "LOAD_ERROR"
                return False

        except Exception as e:
            logger.exception(f"Error en el pipeline: {e}")
            status = "ERROR"
            error_list.append(f"Error general del pipeline: {str(e)}")
            return False
        finally:
            self.end_time = datetime.now(timezone.utc)
            duration = (self.end_time - self.start_time).total_seconds()
            logger.info(f"Pipeline finalizado. Duración: {duration:.2f} segundos")

            max_errores = 50
            truncated_errors = error_list[:max_errores]
            if len(error_list) > max_errores:
                truncated_errors.append(f"...y {len(error_list) - max_errores} errores más.")

            # Log summary de errores
            if error_list:
                logger.warning(f"Pipeline completado con {len(error_list)} errores:")
                for i, error in enumerate(error_list, 1):
                    logger.warning(f"  {i}. {error}")

            # Guardar log en Firestore
            try: 
                log = LogRecord(
                    id=id,
                    start_date=self.start_time,
                    end_date=self.end_time,
                    file_url=self.file_url,
                    errors=truncated_errors, 
                    status=status
                )
                self.firestore_service.connect()
                self.firestore_service.save_log_record(log)
            except Exception as e:
                logger.exception(f"Error guardando log en Firestore: {e}")
                try:
                    minimal_log = LogRecord(
                        id= id,
                        start_date=self.start_time,
                        end_date=self.end_time,
                        file_url=self.file_url or "N/A",
                        errors=[f"Pipeline completado con {len(error_list)} errores (log truncado por tamaño)"],
                        status=status
                    )
                    self.firestore_service.save_log_record(minimal_log)
                except Exception as e2:
                    logger.exception(f"Error guardando log en Firestore: {e2}")

    def extract(self) -> List[Dict[str, Any]]:
        """
        Extrae datos desde el archivo TXT en SFTP.
        """
        try:
            remote_path = self.file_url
            data = self.sftp_service.extract(remote_path)
            return data
        except Exception as e:
            logger.error(f"Error en la extracción SFTP: {e}")
            return []

    async def transform(self, raw_data: List[Dict[str, Any]], id: str, fecha_utc) -> Tuple[List[DataRecord], List[str]]:
        """
        Transforma los datos raw en objetos DataRecord.

        Returns:
            Tuple[List[DataRecord], List[str]]: (datos_transformados, lista_de_errores)
        """
        transformed_data = []
        error_messages = []

        for i, row in enumerate(raw_data):
            try:
                record = DataRecord.from_dict(row, id, fecha_utc)
                transformed_data.append(record)
            except Exception as e:
                error_msg = f"Registro {i+1}: {str(e)} - Datos: {row}"
                error_messages.append(error_msg)
                logger.warning(f"Error transformando registro {i+1}: {e}")

        # Log resumen de transformación
        if error_messages:
            logger.warning(f"Transformación completada con {len(error_messages)} errores de {len(raw_data)} registros")
            
            # Si todos los registros fallaron
            if len(error_messages) == len(raw_data) and len(raw_data) > 0:
                logger.error("Todos los registros fallaron en la transformación")
        else:
            logger.info("Transformación completada sin errores")
        
        return transformed_data, error_messages

    async def load(self, data: List[DataRecord], id: str = None) -> Tuple[bool, List[str]]:
        """
        Carga los datos transformados en Firestore.
        
        Returns:
            Tuple[bool, List[str]]: (success, lista_de_errores)
        """
        error_messages = []
        
        try:
            if not data:
                error_msg = "No hay datos para cargar"
                error_messages.append(error_msg)
                logger.warning(error_msg)
                return False, error_messages

            if not id:
                id = str(uuid4())
            
            # Convierte DataRecord a dict antes de guardar
            records_dicts = [record.model_dump(mode='json') for record in data]
            self.firestore_service.connect()
            self.firestore_service.save_transformed_records(records_dicts, id)
            logger.info(f"Todos los {len(records_dicts)} registros guardados en Firestore exitosamente")
            return True, error_messages
            
        except Exception as e:
            error_msg = f"Error en la carga a Firestore: {str(e)}"
            error_messages.append(error_msg)
            logger.exception(error_msg)
            return False, error_messages

    async def validate_data_quality(self, data: List[DataRecord]) -> Tuple[bool, List[str]]:
        """
        Valida la calidad de los datos.
        
        Returns:
            Tuple[bool, List[str]]: (es_valido, lista_de_errores)
        """
        error_messages = []
        
        if not data:
            error_msg = "No hay datos para validar"
            error_messages.append(error_msg)
            logger.warning(error_msg)
            return False, error_messages

        invalid_records = []
        for i, record in enumerate(data):
            if not record.is_valid():
                invalid_records.append(i + 1)

        null_percentage = (len(invalid_records) / len(data)) * 100

        if null_percentage > 5:
            error_msg = f"Calidad de datos insuficiente: {null_percentage:.2f}% registros inválidos. Registros inválidos: {invalid_records[:10]}{'...' if len(invalid_records) > 10 else ''}"
            error_messages.append(error_msg)
            logger.error(error_msg)
            return False, error_messages

        logger.info(f"Validación de calidad pasada. Registros inválidos: {null_percentage:.2f}%")
        return True, error_messages