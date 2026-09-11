"""Sistema de logging centralizado de Pacioli."""

import logging
import os
from pathlib import Path


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configura el logging de la aplicación.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Logger configurado
    """
    # Crear directorio de logs si no existe
    log_dir = Path.home() / ".local" / "share" / "pacioli" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configurar logger
    logger = logging.getLogger("pacioli")
    logger.setLevel(getattr(logging, level.upper()))

    # Evitar handlers duplicados
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(log_dir / "pacioli.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (solo para WARNING y superior)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Logger global
logger = setup_logging()
