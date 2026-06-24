"""Testes para funções utilitárias de app1.py"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app1 import (
    hash_password,
    verify_password,
    validar_email,
    validar_entrada,
    generate_session_token,
    gerar_token,
    TOKEN_EXPIRY,
)


class TestPasswordHashing:
    def test_hash_returns_string_diferente_do_original(self):
        h = hash_password("senha123")
        assert isinstance(h, str)
        assert h != "senha123"

    def test_verify_senha_correta(self):
        h = hash_password("senha123")
        assert verify_password("senha123", h) is True

    def test_verify_senha_incorreta(self):
        h = hash_password("senha123")
        assert verify_password("errada", h) is False

    def test_hashes_com_salt_diferentes(self):
        h1 = hash_password("senha123")
        h2 = hash_password("senha123")
        assert h1 != h2  # werkzeug usa salt aleatório
        assert verify_password("senha123", h1)
        assert verify_password("senha123", h2)


class TestValidarEmail:
    # validar_email retorna bool (re.match(...) is not None)

    def test_email_valido(self):
        assert validar_email("usuario@exemplo.com") is True

    def test_email_com_subdominio(self):
        assert validar_email("user@mail.example.com.br") is True

    def test_email_sem_arroba(self):
        assert validar_email("invalido") is False

    def test_email_sem_dominio(self):
        assert validar_email("user@") is False

    def test_email_sem_tld(self):
        assert validar_email("user@domain") is False

    def test_email_vazio(self):
        assert validar_email("") is False


class TestValidarEntrada:
    def test_entrada_valida(self):
        erros = validar_entrada("Admin Silva", "admin@exemplo.com", "senha123", "CHAVE123")
        assert erros == []

    def test_nome_vazio(self):
        erros = validar_entrada("", "admin@exemplo.com", "senha123", "CHAVE123")
        assert len(erros) > 0
        assert any("Nome" in e for e in erros)

    def test_nome_muito_curto(self):
        erros = validar_entrada("AB", "admin@exemplo.com", "senha123", "CHAVE123")
        assert len(erros) > 0

    def test_email_invalido(self):
        erros = validar_entrada("Admin Silva", "nao-eh-email", "senha123", "CHAVE123")
        assert len(erros) > 0
        assert any("Email" in e for e in erros)

    def test_senha_muito_curta(self):
        erros = validar_entrada("Admin Silva", "admin@exemplo.com", "123", "CHAVE123")
        assert len(erros) > 0
        assert any("Senha" in e for e in erros)

    def test_chave_muito_curta(self):
        erros = validar_entrada("Admin Silva", "admin@exemplo.com", "senha123", "AB")
        assert len(erros) > 0
        assert any("Chave" in e for e in erros)

    def test_multiplos_erros(self):
        erros = validar_entrada("", "invalido", "12", "A")
        assert len(erros) >= 4

    def test_nome_apenas_espacos(self):
        erros = validar_entrada("   ", "admin@exemplo.com", "senha123", "CHAVE123")
        assert len(erros) > 0


class TestTokenGeneration:
    def test_token_usuario_e_string(self):
        token = generate_session_token()
        assert isinstance(token, str)
        assert len(token) >= 20

    def test_tokens_usuario_sao_unicos(self):
        tokens = {generate_session_token() for _ in range(20)}
        assert len(tokens) == 20

    def test_gerar_token_admin_registra_expiry(self):
        token = gerar_token()
        assert token in TOKEN_EXPIRY
        TOKEN_EXPIRY.pop(token, None)

    def test_tokens_admin_sao_unicos(self):
        tokens = [gerar_token() for _ in range(10)]
        TOKEN_EXPIRY.clear()
        assert len(set(tokens)) == 10
