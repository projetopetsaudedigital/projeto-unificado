"""
Rotas de autenticação.

POST /auth/login       → email + senha → JWT
GET  /auth/me          → dados do usuário logado
GET  /auth/usuarios    → lista de usuários (admin)
POST /auth/usuarios    → criar usuário (admin)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.core.database import execute_query
from app.core.logging_config import setup_logging
from app.auth.jwt import (
    verificar_senha,
    criar_hash,
    criar_token,
    buscar_usuario_por_email,
    get_usuario_obrigatorio,
    exigir_perfil,
)

logger = setup_logging("auth.routes")

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    senha: str


class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: str = "leitor"


class UsuarioResponse(BaseModel):
    co_seq_usuario: int
    ds_nome: str
    ds_email: str
    tp_perfil: str
    st_ativo: bool


# ── Login ─────────────────────────────────────────────────────────────────

@router.post("/login", summary="Login com email e senha")
def login(body: LoginRequest):
    """Autentica com email + senha e retorna um JWT (Bearer token)."""
    usuario = buscar_usuario_por_email(body.email)

    if not usuario or not verificar_senha(body.senha, usuario["ds_senha_hash"]):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    # Atualizar último login
    try:
        execute_query(
            "UPDATE auth.tb_usuarios SET dt_ultimo_login = NOW() WHERE co_seq_usuario = :id",
            {"id": usuario["co_seq_usuario"]},
        )
    except Exception:
        pass  # Não falhar o login por isso

    token = criar_token({"sub": str(usuario["co_seq_usuario"]), "perfil": usuario["tp_perfil"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario["co_seq_usuario"],
            "nome": usuario["ds_nome"],
            "email": usuario["ds_email"],
            "perfil": usuario["tp_perfil"],
        },
    }


# ── Me ────────────────────────────────────────────────────────────────────

@router.get("/me", summary="Dados do usuário logado")
def me(usuario: dict = Depends(get_usuario_obrigatorio)):
    """Retorna os dados do usuário autenticado."""
    return {
        "id": usuario["co_seq_usuario"],
        "nome": usuario["ds_nome"],
        "email": usuario["ds_email"],
        "perfil": usuario["tp_perfil"],
    }


# ── CRUD de usuários (admin) ─────────────────────────────────────────────

@router.get("/usuarios", summary="Lista todos os usuários (admin)")
def listar_usuarios(usuario: dict = Depends(exigir_perfil("admin"))):
    """Lista todos os usuários cadastrados. Requer perfil admin."""
    rows = execute_query(
        "SELECT co_seq_usuario, ds_nome, ds_email, tp_perfil, st_ativo, dt_criacao, dt_ultimo_login "
        "FROM auth.tb_usuarios ORDER BY ds_nome"
    )
    return rows


@router.post("/usuarios", summary="Criar novo usuário (admin)", status_code=201)
def criar_usuario(body: UsuarioCreate, usuario: dict = Depends(exigir_perfil("admin"))):
    """Cria um novo usuário. Requer perfil admin."""
    if body.perfil not in ("admin", "operador", "leitor"):
        raise HTTPException(status_code=400, detail="Perfil inválido. Use: admin, operador ou leitor")

    existente = buscar_usuario_por_email(body.email)
    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    senha_hash = criar_hash(body.senha)
    execute_query(
        "INSERT INTO auth.tb_usuarios (ds_nome, ds_email, ds_senha_hash, tp_perfil) "
        "VALUES (:nome, :email, :senha_hash, :perfil)",
        {"nome": body.nome, "email": body.email, "senha_hash": senha_hash, "perfil": body.perfil},
    )

    logger.info(f"Usuário criado: {body.email} (perfil: {body.perfil})")
    return {"status": "criado", "email": body.email, "perfil": body.perfil}
