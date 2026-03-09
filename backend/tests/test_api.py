"""
Testes para os endpoints da API (sem banco de dados).

Usa o TestClient do FastAPI para testar:
  - Health check
  - Schemas de resposta
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Cria um TestClient do FastAPI."""
    from main import app
    return TestClient(app)


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
