import paramiko
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.models.registro_txt_full import RegistroTxtFull
from src.utils.client_record import decode_content, detect_delimiter
from src.utils.logger import get_logger
from src.services.base_service import BaseService

logger = get_logger(__name__)

class SFTPService(BaseService):
    """
    Servicio para extracción de archivos desde SFTP usando paramiko (sincrónico).
    """
    def __init__(self, connection_config: Optional[Dict[str, Any]] = None):
        super().__init__(connection_config)
        self.ssh_client = None
        self.sftp_client = None
        self.last_error: Optional[str] = None

    def connect(self) -> bool:
        try:
            self.last_error = None
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.connection_config.host,
                port=self.connection_config.port,
                username=self.connection_config.username,
                password=self.connection_config.password,
                timeout=30,
            )
            self.sftp_client = self.ssh_client.open_sftp()
            self.is_connected = True
            logger.info("Conexión SFTP exitosa (paramiko)")
            return True
        except Exception as e:
            logger.error(f"Error conectando a SFTP: {e}")
            self.last_error = str(e)
            if self.sftp_client:
                self.sftp_client.close()
            if self.ssh_client:
                self.ssh_client.close()
            self.sftp_client = None
            self.ssh_client = None
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        if self.sftp_client:
            self.sftp_client.close()
        if self.ssh_client:
            self.ssh_client.close()
        self.sftp_client = None
        self.ssh_client = None
        self.is_connected = False
        logger.info("Desconexión SFTP exitosa (paramiko)")

    def get_modified_time(self, remote_path: str) -> datetime:
        """Fecha y hora (UTC) de la última modificación de un archivo remoto."""
        if not self.sftp_client:
            raise RuntimeError("Cliente SFTP no inicializado")
        return datetime.fromtimestamp(self.sftp_client.stat(remote_path).st_mtime, tz=timezone.utc)

    def extract(self, remote_path: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Descarga y procesa un archivo desde SFTP.
        Soporta CSV (delimitado por coma) y TXT de ancho fijo (por extensión).
        """
        try:
            if not self.is_connected:
                if not self.connect():
                    logger.error("No fue posible establecer conexión SFTP; extracción cancelada")
                    return []
            if not self.sftp_client:
                logger.error("Cliente SFTP no inicializado; extracción cancelada")
                return []
            with self.sftp_client.open(remote_path, 'r') as f:
                # El archivo del cliente viene en cp1252; decode_content prueba UTF-8 primero
                content = decode_content(f.read())

            ext = remote_path.rsplit('.', 1)[-1].lower() if '.' in remote_path else ''
            if ext == 'csv':
                return self._parse_csv(content)
            else:
                return self._parse_fixed_width(content)
        except Exception as e:
            logger.error(f"Error extrayendo archivo SFTP: {e}")
            self.last_error = str(e)
            return []

    def _parse_csv(self, content: str) -> List[Dict[str, Any]]:
        """Parsea contenido CSV con cabecera (separador ',' o ';') y retorna lista de dicts."""
        import csv
        import io
        delimiter = detect_delimiter(content)
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        data = [dict(row) for row in reader if any((v or "").strip() for v in row.values() if isinstance(v, str))]
        logger.info(f"Extraídos {len(data)} registros desde SFTP (CSV, separador '{delimiter}')")
        return data

    def _parse_fixed_width(self, content: str) -> List[Dict[str, Any]]:
        """Parsea contenido TXT de ancho fijo y retorna lista de dicts."""
        data = []
        for line in content.splitlines():
            try:
                registro = RegistroTxtFull.from_line(line)
                data.append(registro.model_dump())
            except Exception as e:
                logger.warning(f"Registro inválido: {e}")
        logger.info(f"Extraídos {len(data)} registros desde SFTP (txt ancho fijo)")
        return data

    def load(self, data: List[Dict[str, Any]], **kwargs) -> bool:
        logger.warning("Carga no soportada en SFTPService")
        return False