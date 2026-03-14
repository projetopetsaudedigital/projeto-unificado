-- =====================================================================
-- TABELAS DE AUTENTICAÇÃO
-- Schema: auth
-- Banco: admin-esus
--
-- Perfis: admin, operador, leitor
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS auth;

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS auth.tb_usuarios (
    co_seq_usuario  SERIAL PRIMARY KEY,
    ds_nome         VARCHAR(150) NOT NULL,
    ds_email        VARCHAR(200) NOT NULL UNIQUE,
    ds_senha_hash   VARCHAR(300) NOT NULL,
    tp_perfil       VARCHAR(20)  NOT NULL DEFAULT 'leitor'
                    CHECK (tp_perfil IN ('admin', 'operador', 'leitor')),
    st_ativo        BOOLEAN      NOT NULL DEFAULT TRUE,
    dt_criacao      TIMESTAMP    NOT NULL DEFAULT NOW(),
    dt_ultimo_login TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_auth_usuarios_email
    ON auth.tb_usuarios (ds_email);

CREATE INDEX IF NOT EXISTS idx_auth_usuarios_ativo
    ON auth.tb_usuarios (st_ativo);

-- Inserir um admin padrão (senha: admin123 — TROCAR EM PRODUÇÃO!)
-- Hash bcrypt de 'admin123'
INSERT INTO auth.tb_usuarios (ds_nome, ds_email, ds_senha_hash, tp_perfil)
VALUES (
    'Administrador',
    'admin@admin.com',
    '$2b$12$O0zc9Gaucxpjvb8BBddM1eT/nxbQFPZPHY75XHPC9gDwPXOs.RpR2',
    'admin'
), (
    'Gestor',
    'gestor@gestor.com',
    '$2a$12$gAJq/nZkSzC1exOuOOgzjuIkw8VwpWl74Obp/xR7WDq7iscHSExn.',
    'leitor'
), (
    'Equipe',
    'equipe@equipe.com',
    '$2a$12$1VE1oFEn0d8DBnZ9JX/XIeWTOOTV3pkvvNmMqBNWLT353FNR6Z0b.',
    'leitor'
) ON CONFLICT (ds_email) DO NOTHING;

COMMENT ON TABLE auth.tb_usuarios IS
    'Usuários da plataforma com perfis (admin/operador/leitor). '
    'Senha armazenada como hash bcrypt.';
