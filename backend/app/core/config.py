"""
Configurações centralizadas via variáveis de ambiente.
Crie um arquivo .env na raiz de /backend com as credenciais.

Dois bancos:
  - PEC (pet_saude) → somente leitura, banco do e-SUS PEC
  - Admin (admin-esus) → leitura/escrita, views materializadas, controle, auth
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ambiente
    ENVIRONMENT: str = "development"

    # Modo de banco: "fdw" (dois bancos) ou "single" (apenas pet_saude)
    DB_MODE: str = "fdw"

    # ── Banco PEC (pet_saude) — somente leitura ──────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "pet_saude"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_SCHEMA: str = "dashboard"

    # ── Banco Admin (admin-esus) — leitura/escrita ───────────────────────
    ADMIN_DB_HOST: str = "localhost"
    ADMIN_DB_PORT: int = 5432
    ADMIN_DB_NAME: str = "admin-esus"
    ADMIN_DB_USER: str = "postgres"
    ADMIN_DB_PASSWORD: str = ""

    # CORS — origens permitidas para o frontend
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Validação de Pressão Arterial
    PA_PAS_MIN: int = 50
    PA_PAS_MAX: int = 300
    PA_PAD_MIN: int = 30
    PA_PAD_MAX: int = 200

    # Outlier detection
    OUTLIER_ZSCORE_THRESHOLD: float = 3.0   # |z| > 3 → outlier individual
    OUTLIER_IQR_FACTOR: float = 1.5         # Q ± 1.5*IQR → outlier populacional

    # Cache
    CACHE_DIR: str = "data/cache"

    # Anos de histórico a considerar
    ANOS_HISTORICO: int = 10

    # JWT Auth
    JWT_SECRET_KEY: str = "CHANGE-ME-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    @property
    def PEC_DATABASE_URL(self) -> str:
        """URL de conexão com o banco PEC (pet_saude) — somente leitura."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def ADMIN_DATABASE_URL(self) -> str:
        """URL de conexão com o banco admin. No modo single, aponta para pet_saude."""
        if self.DB_MODE == "single":
            return self.PEC_DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.ADMIN_DB_USER}:{self.ADMIN_DB_PASSWORD}"
            f"@{self.ADMIN_DB_HOST}:{self.ADMIN_DB_PORT}/{self.ADMIN_DB_NAME}"
        )

    # Retrocompatibilidade — DATABASE_URL aponta para admin-esus
    @property
    def DATABASE_URL(self) -> str:
        return self.ADMIN_DATABASE_URL

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        return (
            f"postgresql+asyncpg://{self.ADMIN_DB_USER}:{self.ADMIN_DB_PASSWORD}"
            f"@{self.ADMIN_DB_HOST}:{self.ADMIN_DB_PORT}/{self.ADMIN_DB_NAME}"
        )


settings = Settings()
