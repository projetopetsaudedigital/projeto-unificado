"""
Testes para configuração e logging.

Cobre:
  - Carregamento de settings com defaults
  - Configuração de logging
"""

import pytest
import logging


class TestLogging:
    """Testes para setup_logging."""

    def test_setup_logging_cria_logger(self):
        from app.core.logging_config import setup_logging
        logger = setup_logging("test.logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.logger"

    def test_setup_logging_tem_handler(self):
        from app.core.logging_config import setup_logging
        logger = setup_logging("test.handler")
        # Handlers são no root logger (centralizado) — child propaga
        root = logging.getLogger()
        assert len(root.handlers) >= 1

    def test_setup_logging_nivel_info(self):
        from app.core.logging_config import setup_logging
        logger = setup_logging("test.level")
        # Level é definido no root logger
        assert logger.getEffectiveLevel() == logging.INFO

    def test_setup_logging_idempotente(self):
        from app.core.logging_config import setup_logging
        logger1 = setup_logging("test.idempotente")
        logger2 = setup_logging("test.idempotente")
        assert logger1 is logger2

    def test_propagate_true(self):
        """Child loggers propagam para o root (centralized logging)."""
        from app.core.logging_config import setup_logging
        logger = setup_logging("test.propagate")
        assert logger.propagate is True


class TestConfig:
    """Testes para settings padrão."""

    def test_pa_limites_existem(self):
        from app.core.config import settings
        assert hasattr(settings, 'PA_PAS_MIN')
        assert hasattr(settings, 'PA_PAS_MAX')
        assert hasattr(settings, 'PA_PAD_MIN')
        assert hasattr(settings, 'PA_PAD_MAX')

    def test_pa_limites_coerentes(self):
        from app.core.config import settings
        assert settings.PA_PAS_MIN < settings.PA_PAS_MAX
        assert settings.PA_PAD_MIN < settings.PA_PAD_MAX
        assert settings.PA_PAD_MIN < settings.PA_PAS_MIN  # PAD minimo < PAS minimo

    def test_outlier_thresholds(self):
        from app.core.config import settings
        assert settings.OUTLIER_ZSCORE_THRESHOLD > 0
        assert settings.OUTLIER_IQR_FACTOR > 0
