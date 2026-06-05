import pytest
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app1


@pytest.fixture(scope="function")
def app():
    fd_u, path_u = tempfile.mkstemp(suffix=".db")
    fd_a, path_a = tempfile.mkstemp(suffix=".db")
    fd_b, path_b = tempfile.mkstemp(suffix=".db")
    os.close(fd_u)
    os.close(fd_a)
    os.close(fd_b)

    orig_users = app1.USERS_DB
    orig_admins = app1.ADMINS_DB
    orig_books = app1.BOOKS_DB

    app1.USERS_DB = path_u
    app1.ADMINS_DB = path_a
    app1.BOOKS_DB = path_b

    app1.init_db()
    app1.app.config["TESTING"] = True

    yield app1.app

    app1.SESSIONS.clear()
    app1.ADMIN_SESSIONS.clear()
    app1.TOKEN_EXPIRY.clear()

    app1.USERS_DB = orig_users
    app1.ADMINS_DB = orig_admins
    app1.BOOKS_DB = orig_books

    for path in (path_u, path_a, path_b):
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def registered_user(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": "test@example.com", "password": "senha123"},
    )
    assert resp.status_code == 201
    return {"name": "Test User", "email": "test@example.com", "password": "senha123"}


@pytest.fixture
def user_token(client, registered_user):
    resp = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    return resp.get_json()["token"]


@pytest.fixture
def registered_admin(client):
    # login gerado: 'adminteste' (name.lower().replace(' ','')[:20])
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
    return {"login": "adminteste", "senha": "admin123", "chave": "CHAVE123"}


@pytest.fixture
def admin_token(client, registered_admin):
    resp = client.post(
        "/api/admin/login",
        json={
            "login": registered_admin["login"],
            "senha": registered_admin["senha"],
            "chave": registered_admin["chave"],
        },
    )
    return resp.get_json()["token"]


@pytest.fixture
def sample_book(client):
    resp = client.post(
        "/books",
        json={"title": "Clean Code", "author": "Robert C. Martin", "year": 2008, "quantity_available": 3},
    )
    assert resp.status_code == 201
    return resp.get_json()


@pytest.fixture
def pending_loan_request(client, user_token, sample_book):
    resp = client.post(
        "/api/loan-requests",
        json={"book_id": sample_book["id"]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    return resp.get_json()
