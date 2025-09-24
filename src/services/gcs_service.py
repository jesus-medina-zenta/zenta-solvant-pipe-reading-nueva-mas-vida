import asyncio
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from google.cloud import storage
from google.cloud.exceptions import NotFound, Forbidden
from google.cloud.storage import Bucket, Blob

from ..utils.logger import get_logger

logger = get_logger(__name__)

class CloudStorageService:
    """
    Servicio para manejar exiones y operaciones con Google Cloud Storage.
    """
    
    def __init__(self, project_id: Optional[str] = None, bucket_name: Optional[str] = None):
        """
        Inicializa el servicio de Cloud Storage.
        
        Args:
            project_id: ID del proyecto de Google Cloud
            bucket_name: Nombre del bucket
        """
        self.is_connected = False
        self.client: Optional[storage.Client] = None
        self.project_id = project_id or os.getenv('FIRESTORE_PROJECT_ID', 'znt-solvant-dev')
        self.bucket_name = bucket_name or os.getenv('GCS_BUCKET_NAME', f'{self.project_id}-csv-files')
        self.bucket: Optional[Bucket] = None
        
    async def connect(self) -> bool:
        """
        Establece conexión con Cloud Storage.
        
        Returns:
            bool: True si la conexión fue exitosa
        """
        if self.is_connected and self.client and self.bucket:
            return True
            
        try:
            logger.info("Conectando a Cloud Storage...")
            logger.info(f"Project ID: {self.project_id}")
            logger.info(f"Bucket: {self.bucket_name}")
            
            # ✅ Verificar credenciales
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and not os.path.exists(credentials_path):
                logger.error(f"❌ Archivo de credenciales no existe: {credentials_path}")
                return False
            
            # Crear cliente de Cloud Storage
            if self.project_id:
                self.client = storage.Client(project=self.project_id)
            else:
                self.client = storage.Client()
            
            # ✅ Configurar bucket de forma segura
            if self.bucket_name:
                self.bucket = self.client.bucket(self.bucket_name)
                
                # ✅ Verificar/crear bucket de forma segura
                try:
                    # Intentar una operación simple para verificar permisos
                    self.bucket.exists()  
                    logger.info(f"📂 Bucket verificado: {self.bucket_name}")
                    
                except NotFound:
                    logger.info(f"Bucket '{self.bucket_name}' no existe, creándolo...")
                    try:
                        self.bucket = self._create_bucket()
                    except Exception as create_error:
                        logger.error(f"❌ No se pudo crear bucket: {create_error}")
                        
                        logger.warning("⚠️ Continuando sin verificar bucket...")
                        
                except Forbidden as e:
                    logger.warning(f"⚠️ Sin permisos para verificar bucket: {e}")
                    logger.warning("⚠️ Continuando asumiendo que el bucket existe...")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error verificando bucket: {e}")
                    logger.warning("⚠️ Continuando sin verificación...")
            
            self.is_connected = True
            logger.info("✅ Conexión a Cloud Storage establecida exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Cloud Storage: {e}")
            logger.error(f"❌ Project ID: {self.project_id}")
            logger.error(f"❌ Bucket Name: {self.bucket_name}")
            logger.error(f"❌ Credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'NO CONFIGURADO')}")
            self.is_connected = False
            return False
    
    def _create_bucket(self) -> Bucket:
        """Crea un nuevo bucket en GCS."""
        try:
            bucket = self.client.bucket(self.bucket_name)
            bucket = self.client.create_bucket(bucket, location="US-CENTRAL1")
            
            # Configurar políticas del bucket
            bucket.versioning_enabled = True
            bucket.patch()
            
            logger.info(f"✅ Bucket '{self.bucket_name}' creado exitosamente")
            return bucket
            
        except Exception as e:
            logger.error(f"❌ Error creando bucket: {e}")
            raise

    async def upload_csv_file(self, local_file_path: str, extraction_id: str) -> Optional[str]:
        """
        Sube archivo CSV a Google Cloud Storage.
        
        Args:
            local_file_path: Ruta local del archivo CSV
            extraction_id: ID de la extracción para organizar archivos
            
        Returns:
            str: URL gs:// del archivo en GCS o None si hay error
        """
        if not self.is_connected:
            if not await self.connect(): 
                logger.error("No se pudo conectar a GCS")
                return None
        
        try:
            if not os.path.exists(local_file_path):
                logger.error(f"Archivo local no encontrado: {local_file_path}")
                return None
            
            # Generar nombre del archivo en GCS con estructura organizada
            file_name = os.path.basename(local_file_path)
            fecha = extraction_id.split('-')[0] if '-' in extraction_id else 'unknown'
            gcs_blob_name = f"extractions/{fecha}/{extraction_id}/{file_name}"
            
            logger.info(f"📤 Subiendo archivo a GCS: {gcs_blob_name}")
            
            # Crear blob y subir archivo
            blob: Blob = self.bucket.blob(gcs_blob_name)
            
            # Subir con metadata
            blob.metadata = {
                'extraction_id': extraction_id,
                'source_pipeline': 'sftp-extractor',
                'content_type': 'text/csv',
                'uploaded_at': str(datetime.now(timezone.utc))
            }
            
            # Subir archivo de forma síncrona
            blob.upload_from_filename(local_file_path, content_type='text/csv')
            
            # Generar URL gs:// para uso interno
            gs_url = f"gs://{self.bucket_name}/{gcs_blob_name}"
            
            logger.info(f"✅ Archivo subido exitosamente a GCS: {gs_url}")
            
            # Limpiar archivo local después de subir exitosamente
            try:
                os.remove(local_file_path)
                logger.info(f"🗑️ Archivo local eliminado: {local_file_path}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar archivo local: {e}")
            
            return gs_url
            
        except Exception as e:
            logger.error(f"❌ Error subiendo archivo a GCS: {e}")
            return None


    async def disconnect(self) -> None:  # ✅ Hacer async
        """Cierra conexión con GCS."""
        if self.client:
            # ✅ Google Cloud Storage client no necesita close() explícito
            self.client = None
            self.bucket = None
            self.is_connected = False
            logger.info("🔌 Conexión a GCS cerrada")
