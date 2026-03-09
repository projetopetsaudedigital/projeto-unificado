"""
Autenticação JWT para a plataforma.

Funções:
  - criar_hash / verificar_senha — bcrypt
  - criar_token / decodificar_token — JWT (HS256)
  - get_usuario_atual — dependência FastAPI (Depends)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("auth")

# ── Segurança HTTP Bearer ─────────────────────────────────────────────────

security = HTTPBearer(auto_error=False)

# ── Hash de senha (bcrypt direto) ─────────────────────────────────────

try:
    import bcrypt as _bcrypt

    def criar_hash(senha: str) -> str:
        return _bcrypt.hashpw(senha.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

    def verificar_senha(senha: str, hash_armazenado: str) -> bool:
        return _bcrypt.checkpw(senha.encode("utf-8"), hash_armazenado.encode("utf-8"))

except ImportError:
    import hashlib
    logger.warning("bcrypt não instalado — usando fallback SHA-256 (NÃO USAR EM PRODUÇÃO)")

    def criar_hash(senha: str) -> str:
        return hashlib.sha256(senha.encode()).hexdigest()

    def verificar_senha(senha: str, hash_armazenado: str) -> bool:
        return hashlib.sha256(senha.encode()).hexdigest() == hash_armazenado

# ── JWT ───────────────────────────────────────────────────────────────────

try:
    from jose import jwt, JWTError
except ImportError:
    logger.warning("python-jose não instalado — auth desabilitada")
    jwt = None
    JWTError = Exception


def criar_token(dados: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um JWT com os dados fornecidos."""
    to_encode = dados.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Decodifica e valida um JWT. Levanta HTTPException se inválido."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

# ── Busca de usuário ──────────────────────────────────────────────────────

def buscar_usuario_por_email(email: str) -> Optional[dict]:
    """Busca um usuário ativo pelo email."""
    rows = execute_query(
        "SELECT * FROM auth.tb_usuarios WHERE ds_email = :email AND st_ativo = TRUE",
        {"email": email},
    )
    return rows[0] if rows else None


def buscar_usuario_por_id(user_id: int) -> Optional[dict]:
    """Busca um usuário pelo ID."""
    rows = execute_query(
        "SELECT * FROM auth.tb_usuarios WHERE co_seq_usuario = :id AND st_ativo = TRUE",
        {"id": user_id},
    )
    return rows[0] if rows else None


# ── Dependência FastAPI ───────────────────────────────────────────────────

async def get_usuario_atual(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Dependência FastAPI — retorna o usuário logado ou None.
    Uso: Depends(get_usuario_atual)
    """
    if not credentials or not jwt:
        return None

    payload = decodificar_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        return None

    usuario = buscar_usuario_por_id(int(user_id))
    return usuario


async def get_usuario_obrigatorio(
    usuario: Optional[dict] = Depends(get_usuario_atual),
) -> dict:
    """
    Dependência FastAPI — exige autenticação.
    Retorna 401 se não autenticado.
    """
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária",
        )
    return usuario


def exigir_perfil(*perfis: str):
    """
    Factory de dependência que exige um perfil específico.
    Uso: Depends(exigir_perfil('admin'))
    """
    async def _check(usuario: dict = Depends(get_usuario_obrigatorio)):
        if usuario["tp_perfil"] not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Perfil necessário: {', '.join(perfis)}",
            )
        return usuario
    return _check
