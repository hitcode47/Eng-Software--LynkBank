"""Testes de CRUD de livros e endpoint de estatísticas/health"""


class TestCreateBook:
    def test_criar_livro_sucesso(self, client):
        resp = client.post(
            "/books",
            json={"title": "Clean Code", "author": "Robert C. Martin", "year": 2008, "quantity_available": 3},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Clean Code"
        assert data["author"] == "Robert C. Martin"
        assert data["year"] == 2008
        assert data["quantity_available"] == 3
        assert "id" in data

    def test_criar_livro_quantidade_default(self, client):
        resp = client.post(
            "/books",
            json={"title": "DDD", "author": "Eric Evans", "year": 2003},
        )
        assert resp.status_code == 201
        assert resp.get_json()["quantity_available"] == 1

    def test_criar_livro_sem_titulo(self, client):
        resp = client.post(
            "/books",
            json={"author": "Autor", "year": 2020},
        )
        assert resp.status_code == 400

    def test_criar_livro_sem_autor(self, client):
        resp = client.post(
            "/books",
            json={"title": "Livro", "year": 2020},
        )
        assert resp.status_code == 400

    def test_criar_livro_sem_ano(self, client):
        resp = client.post(
            "/books",
            json={"title": "Livro", "author": "Autor"},
        )
        assert resp.status_code == 400

    def test_criar_multiplos_livros(self, client):
        for i in range(3):
            resp = client.post(
                "/books",
                json={"title": f"Livro {i}", "author": "Autor", "year": 2020 + i, "quantity_available": 1},
            )
            assert resp.status_code == 201

        resp = client.get("/books")
        assert len(resp.get_json()) == 3


class TestGetBooks:
    def test_listar_livros_vazio(self, client):
        resp = client.get("/books")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_listar_livros_com_resultados(self, client, sample_book):
        resp = client.get("/books")
        assert resp.status_code == 200
        livros = resp.get_json()
        assert len(livros) >= 1
        assert any(l["title"] == "Clean Code" for l in livros)

    def test_livros_sem_estoque_nao_aparecem(self, client):
        client.post(
            "/books",
            json={"title": "Esgotado", "author": "Autor", "year": 2020, "quantity_available": 0},
        )
        resp = client.get("/books")
        livros = resp.get_json()
        assert not any(l["title"] == "Esgotado" for l in livros)

    def test_resposta_tem_campos_esperados(self, client, sample_book):
        resp = client.get("/books")
        livro = resp.get_json()[0]
        for campo in ("id", "title", "author", "year", "quantity"):
            assert campo in livro


class TestGetBook:
    def test_buscar_livro_por_id(self, client, sample_book):
        resp = client.get(f"/api/books/{sample_book['id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["title"] == "Clean Code"
        assert data["id"] == sample_book["id"]

    def test_livro_nao_encontrado(self, client):
        resp = client.get("/api/books/99999")
        assert resp.status_code == 404


class TestDeleteBook:
    def test_deletar_livro_sucesso(self, client, sample_book):
        resp = client.delete(f"/books/{sample_book['id']}")
        assert resp.status_code == 200
        assert "deletado" in resp.get_json()["message"]

    def test_livro_some_do_acervo_apos_delete(self, client, sample_book):
        client.delete(f"/books/{sample_book['id']}")
        resp = client.get("/books")
        assert not any(l["id"] == sample_book["id"] for l in resp.get_json())

    def test_deletar_livro_inexistente(self, client):
        resp = client.delete("/books/99999")
        assert resp.status_code == 404


class TestHealthAndStats:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "OK"

    def test_stats_retorna_campos(self, client):
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_books" in data
        assert "total_available" in data
        assert "total_loaned" in data

    def test_stats_com_livros_cadastrados(self, client, sample_book):
        resp = client.get("/stats")
        data = resp.get_json()
        assert data["total_books"] >= 1
        assert data["total_available"] >= 1
