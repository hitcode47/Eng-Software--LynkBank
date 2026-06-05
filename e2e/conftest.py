"""Fixtures compartilhadas para testes E2E com Playwright"""
import time

import pytest
import requests

API_URL = "http://localhost:5000"
FRONTEND_URL = "http://localhost:5173"


def _aguardar_servidor(url: str, tentativas: int = 15) -> bool:
    for _ in range(tentativas):
        try:
            requests.get(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


@pytest.fixture(scope="session", autouse=True)
def verificar_servidores():
    if not _aguardar_servidor(f"{API_URL}/health"):
        pytest.skip(
            "Backend não está rodando em localhost:5000.\n"
            "Inicie com:  python app1.py"
        )
    if not _aguardar_servidor(FRONTEND_URL):
        pytest.skip(
            "Frontend não está rodando em localhost:5173.\n"
            "Inicie com:  cd frontend && npm run dev"
        )


@pytest.fixture(scope="session")
def admin_e2e():
    """Cria (ou reutiliza) um admin de teste para os testes E2E.

    login gerado de 'E2E Admin' → 'e2eadmin'
    """
    creds = {
        "name": "E2E Admin",
        "email": "e2eadmin@bookstack.test",
        "senha": "e2eadmin123",
        "chave": "E2ECHAVE123",
        "login": "e2eadmin",
    }
    requests.post(
        f"{API_URL}/api/admin/register",
        json={"name": creds["name"], "email": creds["email"], "senha": creds["senha"], "chave": creds["chave"]},
    )
    return creds


def criar_usuario_api(name: str, email: str, password: str) -> None:
    requests.post(f"{API_URL}/api/auth/register", json={"name": name, "email": email, "password": password})


def login_usuario_api(email: str, password: str) -> str:
    resp = requests.post(f"{API_URL}/api/auth/login", json={"email": email, "password": password})
    return resp.json().get("token", "")


def criar_livro_api(title: str, author: str, year: int, quantity: int) -> dict:
    resp = requests.post(
        f"{API_URL}/books",
        json={"title": title, "author": author, "year": year, "quantity_available": quantity},
    )
    return resp.json()


def criar_solicitacao_api(token: str, book_id: int) -> dict:
    resp = requests.post(
        f"{API_URL}/api/loan-requests",
        json={"book_id": book_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()
