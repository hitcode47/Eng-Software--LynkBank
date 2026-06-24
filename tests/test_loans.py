"""Testes de solicitações de empréstimo, aprovação, rejeição, renovação e devolução"""
import pytest


class TestLoanRequests:
    def test_criar_solicitacao_sucesso(self, client, user_token, sample_book):
        resp = client.post(
            "/api/loan-requests",
            json={"book_id": sample_book["id"]},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "pending"
        assert data["book_id"] == sample_book["id"]
        assert "request_date" in data

    def test_criar_solicitacao_sem_book_id(self, client, user_token):
        resp = client.post(
            "/api/loan-requests",
            json={},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 400

    def test_criar_solicitacao_livro_inexistente(self, client, user_token):
        resp = client.post(
            "/api/loan-requests",
            json={"book_id": 99999},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 404

    def test_criar_solicitacao_sem_estoque(self, client, user_token):
        resp = client.post(
            "/books",
            json={"title": "Esgotado", "author": "Autor", "year": 2020, "quantity_available": 0},
        )
        book_id = resp.get_json()["id"]

        resp = client.post(
            "/api/loan-requests",
            json={"book_id": book_id},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 400
        assert "estoque" in resp.get_json()["error"].lower()

    def test_criar_solicitacao_duplicada_pendente(self, client, user_token, sample_book):
        client.post(
            "/api/loan-requests",
            json={"book_id": sample_book["id"]},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        resp = client.post(
            "/api/loan-requests",
            json={"book_id": sample_book["id"]},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 400
        assert "pendente" in resp.get_json()["error"].lower()

    def test_criar_solicitacao_sem_autenticacao(self, client, sample_book):
        resp = client.post("/api/loan-requests", json={"book_id": sample_book["id"]})
        assert resp.status_code == 401

    def test_criar_solicitacao_body_invalido(self, client, user_token):
        # JSON malformado é capturado pelo except geral → 500
        resp = client.post(
            "/api/loan-requests",
            data="not json",
            content_type="application/json",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code >= 400

    def test_listar_solicitacoes_do_usuario(self, client, user_token, pending_loan_request):
        resp = client.get(
            "/api/users/me/loan-requests",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["status"] == "pending"
        assert "book_title" in data[0]

    def test_listar_solicitacoes_usuario_sem_autenticacao(self, client):
        resp = client.get("/api/users/me/loan-requests")
        assert resp.status_code == 401


class TestAdminApproveReject:
    def test_listar_solicitacoes_pendentes(self, client, admin_token, pending_loan_request):
        resp = client.get(
            "/api/admin/loan-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "user_name" in data[0]
        assert "book_title" in data[0]

    def test_listar_pendentes_sem_autenticacao(self, client):
        resp = client.get("/api/admin/loan-requests")
        assert resp.status_code == 401

    def test_aprovar_solicitacao_sucesso(self, client, admin_token, pending_loan_request):
        request_id = pending_loan_request["id"]
        resp = client.put(
            f"/api/admin/loan-requests/{request_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "approved"
        assert data["request_id"] == request_id

    def test_aprovar_solicitacao_inexistente(self, client, admin_token):
        resp = client.put(
            "/api/admin/loan-requests/99999/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_aprovar_solicitacao_ja_processada(self, client, admin_token, pending_loan_request):
        request_id = pending_loan_request["id"]
        client.put(
            f"/api/admin/loan-requests/{request_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.put(
            f"/api/admin/loan-requests/{request_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    def test_rejeitar_solicitacao_sucesso(self, client, admin_token, pending_loan_request):
        request_id = pending_loan_request["id"]
        resp = client.put(
            f"/api/admin/loan-requests/{request_id}/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["status"] == "rejected"

    def test_rejeitar_solicitacao_inexistente(self, client, admin_token):
        resp = client.put(
            "/api/admin/loan-requests/99999/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_rejeitar_solicitacao_ja_processada(self, client, admin_token, pending_loan_request):
        request_id = pending_loan_request["id"]
        client.put(
            f"/api/admin/loan-requests/{request_id}/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.put(
            f"/api/admin/loan-requests/{request_id}/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    def test_aprovar_sem_estoque_disponivel(self, client, admin_token, user_token):
        # Cria livro com 1 cópia e dois usuários solicitando
        book_resp = client.post(
            "/books",
            json={"title": "Uma Copia", "author": "Autor", "year": 2024, "quantity_available": 1},
        )
        book_id = book_resp.get_json()["id"]

        client.post("/api/auth/register", json={"name": "User2", "email": "user2@ex.com", "password": "senha123"})
        token2 = client.post("/api/auth/login", json={"email": "user2@ex.com", "password": "senha123"}).get_json()["token"]

        req1 = client.post(
            "/api/loan-requests",
            json={"book_id": book_id},
            headers={"Authorization": f"Bearer {user_token}"},
        ).get_json()
        req2 = client.post(
            "/api/loan-requests",
            json={"book_id": book_id},
            headers={"Authorization": f"Bearer {token2}"},
        ).get_json()

        # Aprova primeiro — estoque vai a 0
        client.put(
            f"/api/admin/loan-requests/{req1['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Tenta aprovar segundo — sem estoque
        resp = client.put(
            f"/api/admin/loan-requests/{req2['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    def test_aprovacao_cria_emprestimo_ativo(self, client, admin_token, user_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loans_resp = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"})
        assert len(loans_resp.get_json()) == 1

    def test_aprovacao_reduz_estoque(self, client, admin_token, user_token, pending_loan_request, sample_book):
        book_antes = client.get(f"/api/books/{sample_book['id']}").get_json()
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        book_depois = client.get(f"/api/books/{sample_book['id']}").get_json()
        assert book_depois["quantity_available"] == book_antes["quantity_available"] - 1


class TestActiveLoans:
    def test_listar_emprestimos_usuario_vazio(self, client, user_token):
        resp = client.get(
            "/api/users/me/loans",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_listar_emprestimos_usuario_sem_autenticacao(self, client):
        resp = client.get("/api/users/me/loans")
        assert resp.status_code == 401

    def test_renovar_emprestimo_sucesso(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loan_id = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()[0]["id"]

        resp = client.put(
            f"/api/loans/{loan_id}/renew",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert "new_due_date" in resp.get_json()

    def test_renovar_incrementa_contador(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loan = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()[0]
        loan_id = loan["id"]
        renovacoes_antes = loan["renewals"]

        client.put(f"/api/loans/{loan_id}/renew", headers={"Authorization": f"Bearer {user_token}"})
        loan_depois = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()[0]
        assert loan_depois["renewals"] == renovacoes_antes + 1

    def test_renovar_emprestimo_inexistente(self, client, user_token):
        resp = client.put(
            "/api/loans/99999/renew",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 404

    def test_renovar_emprestimo_outro_usuario(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loan_id = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()[0]["id"]

        client.post("/api/auth/register", json={"name": "Outro", "email": "outro@ex.com", "password": "senha123"})
        token2 = client.post("/api/auth/login", json={"email": "outro@ex.com", "password": "senha123"}).get_json()["token"]

        resp = client.put(f"/api/loans/{loan_id}/renew", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403

    def test_devolver_emprestimo_pelo_usuario(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loan_id = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()[0]["id"]

        resp = client.put(
            f"/api/loans/{loan_id}/return",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200

    def test_devolucao_remove_dos_emprestimos_ativos(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loan_id = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()[0]["id"]
        client.put(f"/api/loans/{loan_id}/return", headers={"Authorization": f"Bearer {user_token}"})

        loans = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()
        assert len(loans) == 0

    def test_devolver_emprestimo_inexistente(self, client, user_token):
        resp = client.put("/api/loans/99999/return", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 404

    def test_devolver_emprestimo_outro_usuario(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loan_id = client.get("/api/users/me/loans", headers={"Authorization": f"Bearer {user_token}"}).get_json()[0]["id"]

        client.post("/api/auth/register", json={"name": "Outro", "email": "outro2@ex.com", "password": "senha123"})
        token2 = client.post("/api/auth/login", json={"email": "outro2@ex.com", "password": "senha123"}).get_json()["token"]

        resp = client.put(f"/api/loans/{loan_id}/return", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403

    def test_admin_devolve_emprestimo(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        loan_id = client.get("/loans").get_json()[0]["id"]

        resp = client.put(
            f"/api/admin/loans/{loan_id}/return",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    def test_admin_devolucao_emprestimo_inexistente(self, client, admin_token):
        resp = client.put(
            "/api/admin/loans/99999/return",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_listar_todos_emprestimos(self, client, user_token, admin_token, pending_loan_request):
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get("/loans")
        assert resp.status_code == 200
        loans = resp.get_json()
        assert len(loans) >= 1
        assert "borrowerName" in loans[0]
        assert "title" in loans[0]


class TestLegacyLoanEndpoints:
    def test_criar_emprestimo_legado(self, client, sample_book):
        resp = client.post(
            "/loans",
            json={
                "book_id": sample_book["id"],
                "borrower_name": "João Silva",
                "loan_date": "2025-01-01",
                "return_date": "2025-01-15",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["borrower_name"] == "João Silva"

    def test_criar_emprestimo_legado_campos_faltando(self, client):
        resp = client.post("/loans", json={"book_id": 1})
        assert resp.status_code == 400

    def test_criar_emprestimo_legado_livro_inexistente(self, client):
        resp = client.post(
            "/loans",
            json={
                "book_id": 99999,
                "borrower_name": "João",
                "loan_date": "2025-01-01",
                "return_date": "2025-01-15",
            },
        )
        assert resp.status_code == 404

    def test_criar_emprestimo_legado_sem_estoque(self, client):
        book_resp = client.post(
            "/books",
            json={"title": "Esgotado", "author": "Autor", "year": 2020, "quantity_available": 0},
        )
        book_id = book_resp.get_json()["id"]
        resp = client.post(
            "/loans",
            json={"book_id": book_id, "borrower_name": "João", "loan_date": "2025-01-01", "return_date": "2025-01-15"},
        )
        assert resp.status_code == 400

    def test_devolver_emprestimo_legado(self, client, sample_book):
        loan_id = client.post(
            "/loans",
            json={
                "book_id": sample_book["id"],
                "borrower_name": "João",
                "loan_date": "2025-01-01",
                "return_date": "2025-01-15",
            },
        ).get_json()["id"]

        resp = client.delete(f"/loans/{loan_id}")
        assert resp.status_code == 200

    def test_devolver_emprestimo_legado_inexistente(self, client):
        resp = client.delete("/loans/99999")
        assert resp.status_code == 404

    def test_solicitacao_nao_criada_se_ja_emprestado(self, client, user_token, admin_token, pending_loan_request, sample_book):
        # Aprovação cria empréstimo ativo
        client.put(
            f"/api/admin/loan-requests/{pending_loan_request['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Tenta solicitar o mesmo livro novamente (já está emprestado para este usuário)
        resp = client.post(
            "/api/loan-requests",
            json={"book_id": sample_book["id"]},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 400
