"""
Configuração de logging estruturado para toda a aplicação.

Centraliza:
  - Formato padronizado (ISO timestamp + level + module + message)
  - Log para stdout (desenvolvimento) e arquivo (produção)
  - Rotação automática de arquivo de log
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


# Diretório de logs (relativo à raiz do backend)
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "plataforma_saude.log"

# Formato padronizado
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Flag para inicialização do root logger (uma vez)
_root_configured = False


def _configure_root():
    """Configura o root logger uma vez (arquivo + stdout)."""
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt=_FORMAT, datefmt=_DATE_FORMAT)

    # Handler: stdout (sempre)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Handler: arquivo rotativo (se for produção ou se o dir existir)
    env = os.getenv("ENVIRONMENT", "development")
    try:
        _LOG_DIR.mkdir(exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            _LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG if env == "development" else logging.INFO)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except (OSError, PermissionError):
        # Em ambientes restritos, funcionamos só com stdout
        pass


def setup_logging(name: str) -> logging.Logger:
    """
    Retorna um logger nomeado com configuração centralizada.

    Uso típico:
        from app.core.logging_config import setup_logging
        logger = setup_logging("pa.analytics.mapa")
        logger.info("Carregando dados...")
    """
    _configure_root()

    logger = logging.getLogger(name)
    # Não adiciona handlers individuais — herda do root
    logger.propagate = True
    return logger
