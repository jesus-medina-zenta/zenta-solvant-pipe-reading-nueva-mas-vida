from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from uuid import uuid4
import os
import csv
import requests

from src.services.execute_job import CloudRunService
from src.services.gcs_service import CloudStorageService


from src.config import get_sftp_config
from src.services.sftp_service import SFTPService
from src.services.firestore_service import FirestoreService
from src.models.log_records import LogRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Pipeline:
    """
    Pipeline principal para procesamiento ETL usando SFTP como fuente.
    """
    def __init__(self):

        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.file_url = os.getenv("PIPELINE_FILE_URL")
        # Services
        self.sftp_service = SFTPService(get_sftp_config())
        self.firestore_service = FirestoreService()
        self.gcs_service = CloudStorageService()
        
        self.cloud_run_service = CloudRunService()
        self.errors = []

    async def run(self) -> bool:
        self.start_time = datetime.now(timezone.utc)
        fecha = datetime.now().strftime("%d%m%Y")
        fecha_utc = datetime.now(timezone.utc)
        id = f"{fecha}-{uuid4()}"
        file_url = self.file_url
        status = "OK"
        gcs_url = None
        csv_file_path = None
        logger.info("Iniciando ejecución del pipeline")

        try:
            # Paso 1: Extract
            logger.info("Iniciando extracción de datos")
            raw_data = self.extract()
            logger.info(f"Extraídos {len(raw_data)} registros")

            if not raw_data:
                logger.warning("No se encontraron datos para procesar")
                status = "NO_DATA"
                self.errors.append("No se encontraron datos para procesar")
                if self.sftp_service.last_error:
                    sftp_error_msg = f"Fallo de conexión/extracción SFTP: {self.sftp_service.last_error}"
                    logger.error(sftp_error_msg)
                    self.errors.append(sftp_error_msg)
                    status = "ERROR"
                await self._save_extraction_log(id, status, 0, 0, self.errors, fecha_utc, None)
                return status != "ERROR"

            # Paso 2: Convert to CSV
            logger.info("Iniciando transformación de datos")
            csv_file_path = await self._convert_to_csv(raw_data, id)
            logger.info(f"CSV generado en: {csv_file_path}")

            # Paso 3: Upload CSV to GCS
            logger.info("Subiendo CSV a Google Cloud Storage")
            gcs_url = await self._upload_to_gcs(csv_file_path, id)
            if gcs_url:
                logger.info(f"Archivo subido a GCS: {gcs_url}")
                status = "PENDIENTE"
            else:
                logger.error("Error subiendo archivo a GCS")
                self.errors.append("Error subiendo archivo a GCS")
                status = "ERROR"
            # Paso 4: Load
            logger.info("Save Logs")
            csv_location = gcs_url if gcs_url else csv_file_path
            await self._save_extraction_log(
                id, 
                status, 
                extracted_count= len(raw_data), 
                processed_count=0, 
                errors=self.errors, 
                fecha_utc=fecha_utc, 
                csv_location=csv_location
            )

            if gcs_url:
                logger.info("Activando pipeline de transformación")
                await self._trigger_transformation_pipeline(gcs_url, id)
            else:
                logger.warning("No se activará pipeline de transformación - CSV no está en GCS")
                self.errors.append("Pipeline de transformación no activado - CSV no disponible en GCS")

            logger.info("Pipeline completado exitosamente")
            return True
        
        except Exception as e:
            logger.exception(f"Error en pipeline de extracción: {e}")
            
            self.errors.append(str(e))

            csv_location = gcs_url if gcs_url else csv_file_path
            extracted_count = len(raw_data) if 'raw_data' in locals() and raw_data else 0

            await self._save_extraction_log(
                id, 
                "ERROR", 
                extracted_count, 
                0, 
                self.errors, 
                fecha_utc, 
                csv_location
            )
            return False
        finally:
            self.sftp_service.disconnect()
            self.firestore_service.disconnect()
            await self.gcs_service.disconnect()
            self.cloud_run_service.disconnect()
            
            if self.start_time:
                duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                logger.info(f"Pipeline de extracción finalizado. Duración: {duration:.2f} segundos")

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

    async def _convert_to_csv(self, raw_data: List[Dict[str, Any]], extraction_id: str) -> str:
        """
        Convierte los datos extraídos a formato CSV con SOLO los campos necesarios.
        
        Args:
            raw_data: Datos extraídos del SFTP (líneas parseadas)
            extraction_id: ID de la extracción
            
        Returns:
            str: Ruta del archivo CSV generado
        """
        # Crear directorio de salida si no existe
        output_dir = "output/csv"
        os.makedirs(output_dir, exist_ok=True)
        
        # Nombre del archivo CSV
        csv_filename = f"{extraction_id}.csv"
        csv_file_path = os.path.join(output_dir, csv_filename)
        
        if not raw_data:
            logger.warning("No hay datos para convertir a CSV")
            return csv_file_path
        
        try:
            fieldnames = [
                # Metadata de extracción
                'extraction_id',
                'record_index',
                
                # Campos principales de field_mappings
                'queue',
                'queue_id_cyber',
                'rut_number',
                'rut_digit', 
                'rut',  # rut_number + rut_digit combinado
                'name',
                'paternal_surname',
                'maternal_surname',
                
                # Teléfonos (extraídos aparte)
                'personal_phone',
                'cell_phone',
                
                # Campos financieros/comerciales
                'days_overdue',
                'monthly_payment',
                'down_payment_option1',
                'process_date',
                'overdue_date1',
                'overdue_amount1',
                'email',
                'card',
                'expiration_date',
                'gender',
                
                # URL de pago
                'url_link'
            ]
            
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Escribir headers
                writer.writeheader()
                
                # Escribir datos - SOLO campos especificados
                for idx, raw_record in enumerate(raw_data, 1):
                    try:
                        processed_record = self._extract_specific_fields(raw_record, extraction_id, idx)
                        writer.writerow(processed_record)
                        
                    except Exception as e:
                        logger.error(f"Error procesando registro {idx}: {e}")
                        # Escribir registro con errores marcados
                        error_record = {
                            'extraction_id': extraction_id,
                            'record_index': idx,
                            'queue': 'ERROR',
                            'queue_id_cyber': '',
                            'rut_number': '',
                            'rut_digit': '',
                            'rut': '',
                            'name': f'ERROR_PROCESSING: {str(e)[:50]}',
                            'paternal_surname': '',
                            'maternal_surname': '',
                            'personal_phone': '',
                            'cell_phone': '',
                            'days_overdue': '',
                            'monthly_payment': '',
                            'down_payment_option1': '',
                            'process_date': '',
                            'overdue_date1': '',
                            'overdue_amount1': '',
                            'email': '',
                            'card': '',
                            'expiration_date': '',
                            'gender': '',
                            'url_link': ''
                        }
                        writer.writerow(error_record)
            
            logger.info(f"CSV generado exitosamente: {csv_file_path} ({len(raw_data)} registros)")
            return csv_file_path
            
        except Exception as e:
            logger.error(f"Error generando CSV: {e}")
            raise
    def _extract_specific_fields(self, raw_record: Dict[str, Any], extraction_id: str, record_index: int) -> Dict[str, Any]:
        """
        Extrae solo los campos específicos de un registro raw.
        
        Args:
            raw_record: Registro raw (puede ser línea de texto o dict)
            extraction_id: ID de la extracción
            record_index: Índice del registro
            
        Returns:
            Dict con solo los campos necesarios
        """
        try:
            if isinstance(raw_record, str):
                line = raw_record
                
                field_mappings = [
                    ('queue', 0, 4),
                    ('queue_id_cyber', 0, 4), 
                    ('rut_number', 4, 12),
                    ('rut_digit', 12, 13),
                    ('name', 48, 128),
                    ('paternal_surname', 128, 208),
                    ('maternal_surname', 208, 212), 
                    ('personal_phone', 377, 392),    # Teléfono personal
                    ('cell_phone', 397, 412),        # Teléfono celular
                    ('days_overdue', 473, 478),
                    ('monthly_payment', 478, 493),
                    ('down_payment_option1', 508, 523),
                    ('process_date', 572, 582),
                    ('overdue_date1', 586, 596),
                    ('overdue_amount1', 596, 611),
                    ('email', 822, 882),
                    ('card', 902, 908),
                    ('expiration_date', 1008, 1018),
                    ('gender', 1028, 1029)
                ]
                
                extracted_data = {}
                rut_number = ""
                rut_digit = ""
                
                for field_name, start, end in field_mappings:
                    try:
                        field_value = self._extract_field_safe(line, start, end, field_name)
                        
                        if field_name == 'rut_number':
                            rut_number = field_value
                            extracted_data['rut_number'] = field_value
                        elif field_name == 'rut_digit':
                            rut_digit = field_value
                            extracted_data['rut_digit'] = field_value
                            # Combinar RUT
                            extracted_data['rut'] = f"{rut_number}{rut_digit}" if rut_number and rut_digit else ""
                        else:
                            extracted_data[field_name] = field_value
                            
                    except Exception as e:
                        logger.warning(f"Error extrayendo campo {field_name}: {e}")
                        extracted_data[field_name] = ""
                
                # url_link no se extrae de formato de texto fijo (SFTP), será vacío
                extracted_data['url_link'] = ""
                
            elif isinstance(raw_record, dict):
                # Resuelve campos aceptando nombres de columnas CSV (rut_deudor, fono_contacto, etc.)
                # y nombres de RegistroTxtFull (rut, name, personal_phone, etc.)
                def _val(*keys: str) -> str:
                    for k in keys:
                        v = str(raw_record.get(k, '') or '').strip()
                        if v:
                            return v
                    return ''

                rut_full = _val('rut', 'rut_deudor', 'rut_completo')
                rut_number = _val('rut_number', 'rut_numero')
                rut_digit  = _val('rut_digit', 'rut_digito', 'dv')

                # Si no vienen separados, derivarlos del RUT completo
                if not rut_number and rut_full:
                    clean = rut_full.replace('.', '').replace(' ', '')
                    if '-' in clean:
                        parts = clean.rsplit('-', 1)
                        rut_number = parts[0]
                        rut_digit  = parts[1] if len(parts) > 1 else ''
                    elif len(clean) > 1:
                        rut_number = clean[:-1]
                        rut_digit  = clean[-1]

                extracted_data = {
                    'queue':             _val('queue', 'tipo_deudor', 'queue_id_cyber'),
                    'queue_id_cyber':    _val('queue_id_cyber', 'queue', 'tipo_deudor'),
                    'rut_number':        rut_number,
                    'rut_digit':         rut_digit,
                    'rut':               rut_full or (f"{rut_number}-{rut_digit}" if rut_number else ''),
                    'name':              _val('name', 'nombre_deudor', 'nombre', 'nombres'),
                    'paternal_surname':  _val('paternal_surname', 'apellido_paterno', 'apellido'),
                    'maternal_surname':  _val('maternal_surname', 'apellido_materno'),
                    'personal_phone':    _val('personal_phone', 'fono_contacto', 'telefono', 'celular'),
                    'cell_phone':        _val('cell_phone', 'fono_contacto', 'celular', 'personal_phone'),
                    'days_overdue':      _val('days_overdue', 'dias_mora', 'dias_vencido'),
                    'monthly_payment':   _val('monthly_payment', 'deuda_cotizaciones', 'monto_cotizaciones', 'monto_mensual'),
                    'down_payment_option1': _val('down_payment_option1', 'monto_cupon', 'monto_con_descuento'),
                    'process_date':      _val('process_date', 'fecha_compromiso', 'fecha_proceso'),
                    'overdue_date1':     _val('overdue_date1', 'fecha_mora', 'menor_per_deuda', 'fecha_vencimiento'),
                    'overdue_amount1':   _val('overdue_amount1', 'deuda_cotizaciones', 'monto_cotizaciones', 'monto_vencido'),
                    'email':             _val('email', 'email_destinatario', 'correo'),
                    'card':              _val('card', 'tarjeta'),
                    'expiration_date':   _val('expiration_date', 'fecha_expiracion', 'vencimiento_tarjeta'),
                    'gender':            _val('gender', 'genero', 'sexo'),
                    'url_link':          _val('url_link', 'link_pago', 'payment_link', 'url_pago', 'link'),
                }
            else:
                raise ValueError(f"Tipo de registro no soportado: {type(raw_record)}")
            
            # Agregar metadata de extracción
            csv_record = {
                'extraction_id': extraction_id,
                'record_index': record_index,
                **extracted_data
            }
            
            return csv_record
        
        except Exception as e:
            logger.error(f"Error procesando registro {record_index}: {e}")
            raise
    def _extract_field_safe(self, line: str, start: int, end: int, field_name: str) -> str:
        """
        Versión segura de _extract_field para uso en pipeline.
        """
        try:
            if not line or start < 0 or end < 0 or start >= end:
                return ""
            
            if start >= len(line):
                return ""
            
            # Ajustar end si es mayor que la longitud
            if end > len(line):
                end = len(line)
            
            extracted = line[start:end].strip()
            return extracted
            
        except Exception as e:
            logger.warning(f"Error extrayendo campo '{field_name}': {e}")
            return ""

    async def _save_extraction_log(self, id: str, status: str, extracted_count: int, 
                                    processed_count: int, errors: List[str], fecha_utc: str,
                                    csv_location: str = None): 
            """
            Guarda log específico de extracción (sin transformación).
            """
            try:
                if not self.firestore_service.is_connected:
                    connected = self.firestore_service.connect()
                    if not connected:
                        logger.error("No se pudo conectar a Firestore para guardar log")
                        return

                duration = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0

                # Log específico para extracción
                log_record = LogRecord(
                    id=id,
                    fecha_inicio=self.start_time,
                    fecha_fin=datetime.now(timezone.utc),
                    duracion_segundos=int(duration),
                    status=status,
                    registros_extraidos=extracted_count,
                    registros_transformados=0,
                    registros_cargados=0,
                    errores=errors,
                    archivo_sftp=self.file_url,
                    csv_generado=csv_location, 
                    pipeline_type="EXTRACTION"
                )
 
                self.firestore_service.save_log_record(log_record)
                logger.info(f"Log de extracción guardado con ID: {id}")

            except Exception as e:
                logger.error(f"Error guardando log de extracción: {e}")
    async def _upload_to_gcs(self, csv_file_path: str, extraction_id: str) -> Optional[str]:
        """
        Sube el archivo CSV a Google Cloud Storage.
        """
        try:
            if not self.gcs_service.is_connected:
                connected = await self.gcs_service.connect() 
                if not connected:
                    logger.error("No se pudo conectar a Google Cloud Storage")
                    return None
            
            gcs_url = await self.gcs_service.upload_csv_file(csv_file_path, extraction_id) 
            
            if gcs_url:
                logger.info(f"Archivo CSV subido exitosamente a GCS: {gcs_url}")
                return gcs_url
            else:
                logger.error("Error subiendo archivo CSV a GCS")
                return None
                
        except Exception as e:
            logger.error(f"Error en upload a GCS: {e}")
            self.errors.append(f"Error en upload a GCS: {e}")
            return None

    async def _trigger_transformation_pipeline(self, gcs_url: str, extraction_id: str):
        """
        Activa el pipeline de transformación mediante Cloud Run Job.
        
        Args:
            gcs_url: URL de GCS del archivo CSV
            extraction_id: ID de la extracción
        """
        try:
            logger.info("🚀 Activando pipeline de transformación via Cloud Run Job")
            
            execution_name = await self.cloud_run_service.execute_transformation_job(
                extraction_id=extraction_id,
                gcs_csv_url=gcs_url
            )
            
            if execution_name:
                logger.info(f"✅ Pipeline de transformación activado exitosamente")
                logger.info(f"🔄 Execution: {execution_name}")
                
            else:
                logger.warning("⚠️ No se pudo activar pipeline de transformación")
                self.errors.append("No se pudo ejecutar job de transformación")
                
        except Exception as e:
            logger.error(f"❌ Error activando pipeline de transformación: {e}")
            self.errors.append(f"Error ejecutando job de transformación: {e}")
            
        logger.info(f"📋 Datos disponibles para transformación - ID: {extraction_id}, Status: PENDIENTE")