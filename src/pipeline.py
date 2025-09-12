from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

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

    async def run(self) -> bool:
        self.start_time = datetime.now(timezone.utc)
        carga_id = str(uuid4())
        errores: list = []
        archivo_url = "/upload/Cyber/preventivaZENTA.txt"
        estado = "OK"
        logger.info("Iniciando ejecución del pipeline")

        try:
            # Paso 1: Extract
            logger.info("Iniciando extracción de datos")
            raw_data = self.extract()
            logger.info(f"Extraídos {len(raw_data)} registros")

            if not raw_data:
                logger.warning("No se encontraron datos para procesar")
                return True

            # Paso 2: Transform
            logger.info("Iniciando transformación de datos")
            transformed_data = await self.transform(raw_data)
            logger.info(f"Transformados {len(transformed_data)} registros")

            # Paso 3: Load
            logger.info("Iniciando carga de datos")
            success = await self.load(transformed_data, carga_id)

            if success:
                logger.info("Pipeline completado exitosamente")
                return True
            else:
                logger.error("Error en la carga de datos")
                return False

        except Exception as e:
            logger.exception(f"Error en el pipeline: {e}")
            return False
        finally:
            self.end_time = datetime.now(timezone.utc)
            duration = (self.end_time - self.start_time).total_seconds()
            logger.info(f"Pipeline finalizado. Duración: {duration:.2f} segundos")

            # Guardar log en Firestore
            log = LogRecord(
                carga_id=carga_id,
                fecha_inicio=self.start_time,
                fecha_fin=self.end_time,
                archivo_url=archivo_url,
                errores=errores,
                estado=estado
            )
            self.firestore_service.connect()
            self.firestore_service.save_log_record(log)

    def extract(self) -> List[Dict[str, Any]]:
        """
        Extrae datos desde el archivo TXT en SFTP.
        """
        try:
            remote_path = "/upload/Cyber/preventivaZENTA.txt"
            data = self.sftp_service.extract(remote_path)
           # print("Datos extraídos:", data)  # Depuración
            return data
        except Exception as e:
            logger.error(f"Error en la extracción SFTP: {e}")
            return []

#CAMBIAR RETURN TYPE A List[DataRecord]
    async def transform(self, raw_data: List[Dict[str, Any]]) -> List[DataRecord]:
        transformed_data = []
        errors = 0

        for row in raw_data:
            try:
                record = DataRecord(**row)
                transformed_data.append(record)
            except Exception as e:
                errors += 1
                logger.warning(f"Error transformando registro: {e}")
                if errors == len(raw_data) and len(raw_data) > 0:
                    logger.error(f"Todos los registros son inválidos ({errors} errores)")
                    return []

        if errors > 0:
            logger.warning(f"Se encontraron {errors} errores en la transformación")

        print(transformed_data[0].model_dump(mode='json'))  # Depuración: muestra el segundo registro transformado
        return transformed_data

    async def load(self, data: List[DataRecord], carga_id: str = None) -> bool:
        """
        Carga los datos transformados en Firestore.
        """
        try:
            if not carga_id:
                carga_id = str(uuid4())
            # Convierte DataRecord a dict antes de guardar
            records_dicts = [record.model_dump(mode='json') for record in data]
            self.firestore_service.connect()
            self.firestore_service.save_transformed_records(records_dicts, carga_id)
            logger.info("Todos los registros guardados en Firestore exitosamente")
            return True
        except Exception as e:
            logger.exception(f"Error en la carga a Firestore: {e}")
            return False

    async def validate_data_quality(self, data: List[DataRecord]) -> bool:
        if not data:
            logger.warning("No hay datos para validar")
            return False

        null_count = sum(1 for record in data if not record.is_valid())
        null_percentage = (null_count / len(data)) * 100

        if null_percentage > 5:
            logger.error(f"Demasiados registros inválidos: {null_percentage:.2f}%")
            return False

        logger.info(f"Validación de calidad pasada. Registros inválidos: {null_percentage:.2f}%")
        return True