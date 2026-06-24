"""Testes de autenticação de administradores (registro, login, perfil, logout)"""


class TestAdminRegister:
    def test_registro_sucesso(self, client):
        resp = client.post(
            "/api/admin/register",
            json={
                "name": "Admin Teste",
                "email": "admin@exemplo.com",
                "senha": "admin123",
                "chave": "CHAVE123",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["login"] == "adminteste"

    def test_registro_email_duplicado(self, client, registered_admin):
        resp = client.post(
            "/api/admin/register",
            json={
                "name": "Outro Admin",
                "email": "admin@exemplo.com",  # mesmo email do fixture
                "senha": "outrasenha",
                "chave": "CHAVE456",
            },
        )
        assert resp.status_code == 409

    def test_registro_email_invalido(self, client):
        resp = client.post(
            "/api/admin/register",
            json={
                "name": "Admin Teste",
                "email": "nao-eh-email",
                "senha": "admin123",
                "chave": "CHAVE123",
            },
        )
        assert resp.status_code == 400

    def test_registro_senha_curta(self, client):
        resp = client.post(
            "/api/admin/register",
            json={
                "name": "Admin Teste",
                "email": "admin@exemplo.com",
                "senha": "123",
                "chave": "CHAVE123",
            },
        )
        assert resp.status_code == 400

    def test_registro_chave_curta(self, client):
        resp = client.post(
            "/api/admin/register",
            json={
                "name": "Admin Teste",
                "email": "admin@exemplo.com",
                "senha": "admin123",
                "chave": "AB",
            },
        )
        assert resp.status_code == 400

    def test_registro_nome_curto(self, client):
        resp = client.post(
            "/api/admin/register",
            json={
                "name": "AB",
                "email": "admin@exemplo.com",
                "senha": "admin123",
                "chave": "CHAVE123",
            },
        )
        assert resp.status_code == 400

    def test_registro_sem_body(self, client):
        # Flask/Werkzeug retorna 415 quando falta Content-Type
        resp = client.post("/api/admin/register")
        assert resp.status_code in (400, 415)

    def test_registro_deduplica_login(self, client):
        # Dois admins com mesmo nome geram logins diferentes
        client.post(
            "/api/admin/register",
            json={
                "name": "Admin Teste",
                "email": "admin1@exemplo.com",
                "senha": "admin123",
                "chave": "CHAVE123",
            },
        )
        resp = client.post(
            "/api/admin/register",
            json={
                "name": "Admin Teste",
                "email": "admin2@exemplo.com",
                "senha": "admin123",
                "chave": "CHAVE123",
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["login"] == "adminteste1"


class TestAdminLogin:
    def test_login_sucesso(self, client, registered_admin):
        resp = client.post(
            "/api/admin/login",
            json={
                "login": registered_admin["login"],
                "senha": registered_admin["senha"],
                "chave": registered_admin["chave"],
            },
        )
        assert resp.status_code == 200
        assert "token" in resp.get_json()

    def test_login_senha_errada(self, client, registered_admin):
        resp = client.post(
            "/api/admin/login",
            json={
                "login": registered_admin["login"],
                "senha": "senhaerrada",
                "chave": registered_admin["chave"],
            },
        )
        assert resp.status_code == 401

    def test_login_chave_errada(self, client, registered_admin):
        resp = client.post(
            "/api/admin/login",
            json={
                "login": registered_admin["login"],
                "senha": registered_admin["senha"],
                "chave": "CHAVEERRADA",
            },
        )
        assert resp.status_code == 401

    def test_login_usuario_inexistente(self, client):
        resp = client.post(
            "/api/admin/login",
            json={"login": "ninguem", "senha": "admin123", "chave": "CHAVE123"},
        )
        assert resp.status_code == 401

    def test_login_campos_faltando(self, client):
        resp = client.post("/api/admin/login", json={"login": "admin"})
        assert resp.status_code == 400

    def test_login_sem_body(self, client):
        # Flask/Werkzeug retorna 415 quando falta Content-Type
        resp = client.post("/api/admin/login")
        assert resp.status_code in (400, 415)


class TestAdminPerfil:
    def test_perfil_sucesso(self, client, admin_token):
        resp = client.get(
            "/api/admin/perfil",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "name" in data
        assert "email" in data
        assert "login" in data

    def test_perfil_sem_token(self, client):
        resp = client.get("/api/admin/perfil")
        assert resp.status_code == 401

    def test_perfil_token_invalido(self, client):
        resp = client.get(
            "/api/admin/perfil",
            headers={"Authorization": "Bearer tokeninvalido"},
        )
        assert resp.status_code == 401


class TestAdminLogout:
    def test_logout_sucesso(self, client, admin_token):
        resp = client.post(
            "/api/admin/logout",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    def test_token_invalida_apos_logout(self, client, admin_token):
        client.post("/api/admin/logout", headers={"Authorization": f"Bearer {admin_token}"})
        resp = client.get("/api/admin/perfil", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 401

    def test_logout_token_invalido(self, client):
        resp = client.post(
            "/api/admin/logout",
            headers={"Authorization": "Bearer tokeninvalido"},
        )
        assert resp.status_code == 401
