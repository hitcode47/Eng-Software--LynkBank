"""Testes de autenticação de usuários (registro, login, logout, token)"""


class TestUserRegister:
    def test_registro_sucesso(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "João Silva", "email": "joao@exemplo.com", "password": "senha123"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["email"] == "joao@exemplo.com"

    def test_registro_email_duplicado(self, client, registered_user):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Outro", "email": registered_user["email"], "password": "senha123"},
        )
        assert resp.status_code == 409
        assert resp.get_json()["success"] is False

    def test_registro_sem_nome(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "test@exemplo.com", "password": "senha123"},
        )
        assert resp.status_code == 400

    def test_registro_sem_email(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Test User", "password": "senha123"},
        )
        assert resp.status_code == 400

    def test_registro_sem_senha(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Test User", "email": "test@exemplo.com"},
        )
        assert resp.status_code == 400

    def test_registro_senha_muito_curta(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Test User", "email": "test@exemplo.com", "password": "123"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_registro_senha_muito_longa(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Test User", "email": "test@exemplo.com", "password": "a" * 129},
        )
        assert resp.status_code == 400

    def test_registro_nome_muito_longo(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "a" * 101, "email": "test@exemplo.com", "password": "senha123"},
        )
        assert resp.status_code == 400

    def test_registro_nome_apenas_espacos(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "   ", "email": "test@exemplo.com", "password": "senha123"},
        )
        assert resp.status_code == 400

    def test_registro_sem_body(self, client):
        # Flask retorna 500 (except geral) ou 415 dependendo da versão
        resp = client.post("/api/auth/register")
        assert resp.status_code >= 400

    def test_registro_normaliza_email_para_minusculo(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Test User", "email": "TEST@EXEMPLO.COM", "password": "senha123"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["email"] == "test@exemplo.com"


class TestUserLogin:
    def test_login_sucesso(self, client, registered_user):
        resp = client.post(
            "/api/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "token" in data
        assert "user" in data

    def test_login_senha_errada(self, client, registered_user):
        resp = client.post(
            "/api/auth/login",
            json={"email": registered_user["email"], "password": "senhaerrada"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["success"] is False

    def test_login_email_inexistente(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "ninguem@exemplo.com", "password": "senha123"},
        )
        assert resp.status_code == 401

    def test_login_campos_faltando(self, client):
        resp = client.post("/api/auth/login", json={"email": "test@exemplo.com"})
        assert resp.status_code == 400

    def test_login_sem_body(self, client):
        # Flask captura como exceção no except geral → 500
        resp = client.post("/api/auth/login")
        assert resp.status_code >= 400

    def test_login_retorna_dados_do_usuario(self, client, registered_user):
        resp = client.post(
            "/api/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        data = resp.get_json()
        assert data["user"]["email"] == registered_user["email"]
        assert data["user"]["name"] == registered_user["name"]


class TestUserLogout:
    def test_logout_sucesso(self, client, user_token):
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200

    def test_logout_sem_token(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 400

    def test_logout_token_invalido(self, client):
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer tokeninvalido"},
        )
        assert resp.status_code == 200  # graceful: token não encontrado na sessão

    def test_token_invalida_apos_logout(self, client, user_token):
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {user_token}"})
        resp = client.get("/api/auth/user", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 401


class TestGetCurrentUser:
    def test_busca_usuario_autenticado(self, client, user_token, registered_user):
        resp = client.get(
            "/api/auth/user",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["email"] == registered_user["email"]
        assert data["name"] == registered_user["name"]
        assert "id" in data

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/api/auth/user")
        assert resp.status_code == 401

    def test_token_invalido_retorna_401(self, client):
        resp = client.get(
            "/api/auth/user",
            headers={"Authorization": "Bearer tokeninvalido"},
        )
        assert resp.status_code == 401

    def test_authorization_header_malformado(self, client):
        resp = client.get(
            "/api/auth/user",
            headers={"Authorization": "sembearer"},
        )
        assert resp.status_code == 401


class TestVerifyToken:
    def test_token_valido(self, client, user_token):
        resp = client.post("/api/auth/verify", json={"token": user_token})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valid"] is True

    def test_token_invalido(self, client):
        resp = client.post("/api/auth/verify", json={"token": "tokeninvalido"})
        assert resp.status_code == 401
        assert resp.get_json()["valid"] is False

    def test_sem_token_no_body(self, client):
        resp = client.post("/api/auth/verify", json={})
        assert resp.status_code == 400
