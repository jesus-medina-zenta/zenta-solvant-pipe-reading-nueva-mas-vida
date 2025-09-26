from typing import Optional, Dict, Any
import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import get_cloud_run_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CloudRunService:
    """
    Servicio para ejecutar jobs de Cloud Run desde el pipeline.
    Usa únicamente impersonated service account credentials.
    """
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.cloud_run_config = get_cloud_run_config()
        self.project_id = self.cloud_run_config.project_id
        self.location = self.cloud_run_config.region
        self.job_name = self.cloud_run_config.job_name

    def connect(self) -> bool:
        """
        Establece conexión con la API de Cloud Run usando impersonated credentials.
        """
        try:
            if self.service:
                return True

            logger.info("🔗 Conectando a Cloud Run API con impersonated credentials...")
            
            # Esto maneja automáticamente impersonated service accounts
            self.credentials, detected_project = google.auth.default()
            
            logger.info(f"✅ Credenciales de impersonación cargadas")
            logger.info(f"🔍 Proyecto detectado: {detected_project}")
            
            # ✅ Log adicional para verificar tipo de credencial
            credential_type = type(self.credentials).__name__
            logger.info(f"🔍 Tipo de credential: {credential_type}")
            
            # Construir cliente de la API
            self.service = build('run', 'v2', credentials=self.credentials)
            
            logger.info("✅ Conexión a Cloud Run API establecida")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Cloud Run API: {e}")
            logger.error(f"❌ Tipo de error: {type(e)}")
            logger.error("💡 Verificar que GOOGLE_APPLICATION_CREDENTIALS está configurado correctamente")
            return False

    async def execute_transformation_job(self, extraction_id: str = None, gcs_csv_url: str = None) -> Optional[str]:
        """
        Ejecuta el job de transformación.
        """
        try:
            if not self.service and not self.connect():
                logger.error("No se pudo conectar a Cloud Run API")
                return None
            
            logger.info(f"🚀 Ejecutando job de transformación: {self.job_name}")
            if extraction_id:
                logger.info(f"🔍 Triggered by extraction: {extraction_id}")
            if gcs_csv_url:
                logger.info(f"📄 CSV disponible en: {gcs_csv_url}")

            # Body vacío - el job ya sabe qué hacer
            request_body = {}
            
            # Nombre completo del job
            parent = f'projects/{self.project_id}/locations/{self.location}'
            job_path = f"{parent}/jobs/{self.job_name}"
            
            logger.info(f"🔍 Job path: {job_path}")
            
            # Ejecutar job
            request = self.service.projects().locations().jobs().run(
                name=job_path,
                body=request_body
            )

            response = request.execute()
            
            # Procesar respuesta
            execution_name = response.get("name", "")
            execution_id = execution_name.split('/')[-1] if execution_name else "unknown"
            
            logger.info(f"✅ Job de transformación ejecutado exitosamente")
            logger.info(f"🔄 Execution ID: {execution_id}")
            logger.info(f"📋 Execution name: {execution_name}")
            logger.info(f"💡 El job procesará automáticamente registros PENDIENTES")
            
            return execution_name
            
        except HttpError as e:
            logger.error(f"❌ Error HTTP ejecutando job: {e}")
            
            if e.resp.status == 404:
                logger.error(f"❌ Job '{self.job_name}' no encontrado en región '{self.location}'")
                logger.error(f"💡 Verificar job existe: gcloud run jobs list --region={self.location} --project={self.project_id}")
                
            elif e.resp.status == 403:
                logger.error("❌ Sin permisos para ejecutar Cloud Run jobs")
                logger.error("💡 La service account impersonada necesita estos permisos:")
                logger.error("   - roles/run.developer (para ejecutar jobs)")
                logger.error("   - roles/run.admin (alternativa más amplia)")
                logger.error(f"💡 Verificar permisos para el proyecto: {self.project_id}")
                
            elif e.resp.status == 400:
                logger.error("❌ Request inválido")
                logger.error(f"❌ Response: {e.content}")
                
            else:
                logger.error(f"❌ Error HTTP {e.resp.status}: {e.content}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error inesperado ejecutando job: {e}")
            logger.error(f"❌ Tipo de error: {type(e)}")
            return None

    async def trigger_transformation_pipeline(self, extraction_id: str, gcs_csv_url: str) -> bool:
        """
        Método simplificado para activar el pipeline de transformación.
        """
        try:
            logger.info("🚀 Activando pipeline de transformación...")
            
            execution_name = await self.execute_transformation_job(extraction_id, gcs_csv_url)
            
            if execution_name:
                logger.info("✅ Pipeline de transformación activado exitosamente")
                logger.info(f"💡 El job procesará todos los registros PENDIENTES en Firestore")
                
                return True
            else:
                logger.warning("⚠️ No se pudo activar pipeline de transformación")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error activando pipeline de transformación: {e}")
            return False

    def disconnect(self) -> None:
        """
        Cierra conexión con Cloud Run API.
        """
        if self.service or self.credentials:
            self.service = None
            self.credentials = None
            logger.info("🔌 Conexión a Cloud Run API cerrada")