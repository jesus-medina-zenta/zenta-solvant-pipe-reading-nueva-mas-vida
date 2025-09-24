"""
Configuración de logging para la aplicación.
"""
import logging
import sys
from typing import Dict
from ..config import get_config

# Diccionario para evitar reconfiguración
_configured_loggers: Dict[str, logging.Logger] = {}
_root_configured = False

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para un módulo específico.
    
    Args:
        name: Nombre del módulo (típicamente __name__)
        
    Returns:
        logging.Logger: Logger configurado
    """
    global _root_configured
    
    # Configurar root logger una sola vez
    if not _root_configured:
        _setup_root_logger()
        _root_configured = True
    
    # Si el logger ya fue configurado, retornarlo
    if name in _configured_loggers:
        return _configured_loggers[name]
    
    # Crear logger específico
    logger = logging.getLogger(name)
    
    # ✅ CLAVE: Evitar propagación al root para evitar duplicación
    logger.propagate = False
    
    # Solo agregar handler si no tiene ninguno
    if not logger.handlers:
        # Crear handler propio
        handler = logging.StreamHandler(sys.stdout)
        
        # Obtener configuración
        app_config = get_config()
        log_level = getattr(logging, app_config.log_level.upper())
        
        # Configurar handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
        
        # Agregar handler al logger
        logger.addHandler(handler)
        logger.setLevel(log_level)
        
        # Set debug level if in development
        if app_config.environment == "development":
            logger.setLevel(logging.DEBUG)
    
    # Guardar para evitar reconfiguración
    _configured_loggers[name] = logger
    return logger

def _setup_root_logger():
    """Configura el root logger una sola vez."""
    root_logger = logging.getLogger()
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Configurar nivel para el root (solo errores críticos)
    root_logger.setLevel(logging.ERROR)
    
    # Configurar loggers de terceros para ser menos verbosos
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("pandas").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)  # ✅ Para reducir logs de SFTP

# ✅ No llamar setup automáticamente al importar