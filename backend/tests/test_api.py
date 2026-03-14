"""
Testes para os endpoints da API (sem banco de dados).

Usa o TestClient do FastAPI para testar:
  - Health check
  - Schemas de resposta
"""

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt import get_usuario_obrigatorio
from app.modules.pressao_arterial.routes import analytics as analytics_routes


@pytest.fixture
def client():
    """Cria um TestClient do FastAPI."""
    from main import app
    return TestClient(app)


@pytest.fixture
def client_autenticado_mock(monkeypatch):
    """Cliente autenticado com mock da busca de individuos."""
    from main import app

    app.dependency_overrides[get_usuario_obrigatorio] = lambda: {
        "co_seq_usuario": 1,
        "tp_perfil": "leitor",
    }

    monkeypatch.setattr(
        analytics_routes,
        "buscar_individuos_hipertensos",
        lambda **kwargs: {
            "total": 2,
            "dados": [
                {
                    "co_cidadao": 101,
                    "mediana_pas": 146.0,
                    "mediana_pad": 92.0,
                    "n_medicoes_usadas": 3,
                    "dt_ultima_medicao": "2026-03-10",
                },
                {
                    "co_cidadao": 202,
                    "mediana_pas": 142.0,
                    "mediana_pad": 90.0,
                    "n_medicoes_usadas": 2,
                    "dt_ultima_medicao": "2026-03-08",
                },
            ],
        },
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestHealthCheck:
    """Testes do endpoint de health check."""

    def test_health_retorna_200(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200

    def test_health_retorna_status(self, client):
        r = client.get("/api/v1/health")
        data = r.json()
        assert "status" in data


class TestAdminEndpoints:
    """Testes dos endpoints admin (podem falhar sem banco)."""

    def test_admin_status_retorna_json(self, client):
        r = client.get("/api/v1/pressao-arterial/admin/status")
        # Pode ser 200 (banco conectado) ou 500 (banco desconectado)
        assert r.status_code in [200, 500]
        if r.status_code == 200:
            data = r.json()
            assert "schema_dashboard" in data

    def test_admin_processamentos_retorna_lista(self, client):
        r = client.get("/api/v1/pressao-arterial/admin/processamentos")
        if r.status_code == 200:
            data = r.json()
            assert isinstance(data, list)

    def test_admin_treinar_modulo_invalido(self, client):
        r = client.post("/api/v1/pressao-arterial/admin/treinar/xyz")
        assert r.status_code == 400
        assert "não reconhecido" in r.json()["detail"]


class TestMLEndpoints:
    """Testes dos endpoints de ML."""

    def test_modelo_info_retorna_json(self, client):
        r = client.get("/api/v1/pressao-arterial/modelo/info")
        assert r.status_code == 200
        data = r.json()
        assert "disponivel" in data

    def test_status_treino_retorna_json(self, client):
        r = client.get("/api/v1/pressao-arterial/modelo/status-treino")
        assert r.status_code == 200
        data = r.json()
        assert "em_andamento" in data

    def test_predizer_sem_modelo(self, client):
        """Se não houver modelo treinado, deve retornar 503."""
        r = client.post(
            "/api/v1/pressao-arterial/predizer-risco",
            json={"idade": 55, "co_dim_sexo": 1},
        )
        # 200 se modelo existe, 503 se não existe
        assert r.status_code in [200, 503]


class TestIndividuosHipertensao:
    """Testes do endpoint de individuos com hipertensao."""

    def test_individuos_sem_token_retorna_401(self, client):
        r = client.get("/api/v1/pressao-arterial/individuos")
        assert r.status_code == 401

    def test_individuos_periodo_invalido_retorna_422(self, client_autenticado_mock):
        r = client_autenticado_mock.get(
            "/api/v1/pressao-arterial/individuos",
            params={
                "data_ultima_medicao_inicio": "2026-03-10",
                "data_ultima_medicao_fim": "2026-03-01",
            },
        )
        assert r.status_code == 422

    def test_individuos_retorna_estrutura_esperada(self, client_autenticado_mock):
        r = client_autenticado_mock.get(
            "/api/v1/pressao-arterial/individuos",
            params={
                "bairro": "patagonia",
                "sexo": "F",
                "limite": 10,
                "offset": 0,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["limite"] == 10
        assert data["offset"] == 0
        assert "filtros_aplicados" in data
        assert isinstance(data["dados"], list)
        assert data["dados"][0]["co_cidadao"] == 101
        assert data["dados"][0]["mediana_pas"] == 146.0
        assert data["dados"][0]["mediana_pad"] == 92.0
        assert data["dados"][0]["n_medicoes_usadas"] == 3
        assert data["dados"][0]["dt_ultima_medicao"] == "2026-03-10"
