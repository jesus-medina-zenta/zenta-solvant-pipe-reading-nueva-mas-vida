import paramiko
from typing import List, Dict, Any, Optional

from src.models.registro_txt_full import RegistroTxtFull
from src.utils.logger import get_logger
from services.base_service import BaseService

logger = get_logger(__name__)

class SFTPService(BaseService):
    """
    Servicio para extracción de archivos desde SFTP usando paramiko (sincrónico).
    """
    def __init__(self, connection_config: Optional[Dict[str, Any]] = None):
        super().__init__(connection_config)
        self.transport = None
        self.sftp_client = None

    def connect(self) -> bool:
        try:
            self.transport = paramiko.Transport((self.connection_config.host, self.connection_config.port))
            self.transport.connect(
                username=self.connection_config.username,
                password=self.connection_config.password
            )
            self.sftp_client = paramiko.SFTPClient.from_transport(self.transport)
            self.is_connected = True
            logger.info("Conexión SFTP exitosa (paramiko)")
            return True
        except Exception as e:
            logger.error(f"Error conectando a SFTP: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        if self.sftp_client:
            self.sftp_client.close()
        if self.transport:
            self.transport.close()
        self.is_connected = False
        logger.info("Desconexión SFTP exitosa (paramiko)")

    def extract(self, remote_path: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Descarga y procesa un archivo TXT de campos de ancho fijo desde SFTP.
        """
        try:
            if not self.is_connected:
                self.connect()
            with self.sftp_client.open(remote_path, 'r') as f:
                content = f.read().decode('utf-8')
                lines = content.splitlines()
                data = []
                for line in lines:
                    try:
                        registro = RegistroTxtFull.from_line(line)
                        data.append(registro.model_dump())
                    except Exception as e:
                        logger.warning(f"Registro inválido: {e}")
                logger.info(f"Extraídos {len(data)} registros desde SFTP (txt ancho fijo)")
                return data
        except Exception as e:
            logger.error(f"Error extrayendo archivo SFTP: {e}")
            return []

    def load(self, data: List[Dict[str, Any]], **kwargs) -> bool:
        logger.warning("Carga no soportada en SFTPService")
        return False