"""
4 testes E2E com Playwright cobrindo os fluxos principais do BookStack.

Para executar:
    pytest e2e/ -v --no-cov

Pré-requisito: backend (python app1.py) e frontend (npm run dev) em execução.
"""
import time

from playwright.sync_api import Page, expect

from e2e.conftest import (
    FRONTEND_URL,
    criar_livro_api,
    criar_solicitacao_api,
    criar_usuario_api,
    login_usuario_api,
)


# ─── helpers de UI ────────────────────────────────────────────────────────────

def _fazer_login_usuario(page: Page, email: str, password: str) -> None:
    """Navega até /login-user e autentica como usuário comum."""
    page.goto(f"{FRONTEND_URL}/login-user")
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_url(f"{FRONTEND_URL}/dashboard", timeout=8000)


def _fazer_login_admin(page: Page, login: str, senha: str, chave: str) -> None:
    """Navega até /login-adm e autentica como administrador."""
    page.goto(f"{FRONTEND_URL}/login-adm")
    page.locator("#login").fill(login)
    page.locator("#senha").fill(senha)
    page.locator("#chave").fill(chave)
    page.get_by_role("button", name="Entrar").click()
    # O LoginAdm redireciona após 1 s via setTimeout
    page.wait_for_url(f"{FRONTEND_URL}/admin", timeout=8000)


# ─── Teste E2E 1 ──────────────────────────────────────────────────────────────

def test_e2e_01_usuario_se_cadastra_e_faz_login(page: Page, admin_e2e):
    """
    Fluxo: cadastro de novo usuário via UI → retorno ao login → login → dashboard.

    Valida que o ciclo completo de auto-cadastro funciona sem erros visíveis
    e que o usuário é redirecionado ao painel após autenticar.
    """
    ts = int(time.time() * 1000)
    email = f"e2e01_{ts}@bookstack.test"
    nome = f"E2E User {ts}"

    page.goto(f"{FRONTEND_URL}/login-user")

    # Abre modo de cadastro
    page.get_by_role("button", name="Cadastre-se").click()

    # Preenche formulário de registro
    page.locator("#name").fill(nome)
    page.locator("#email").fill(email)
    page.locator("#password").fill("e2epassword123")
    page.get_by_role("button", name="Registrar").click()

    # Após registro bem-sucedido, volta ao modo login (botão "Cadastre-se" fica visível)
    expect(page.get_by_role("button", name="Cadastre-se")).to_be_visible(timeout=5000)

    # Faz login com as credenciais recém-criadas
    page.locator("#email").fill(email)
    page.locator("#password").fill("e2epassword123")
    page.get_by_role("button", name="Entrar").click()

    # Deve redirecionar para o dashboard
    page.wait_for_url(f"{FRONTEND_URL}/dashboard", timeout=8000)
    expect(page).to_have_url(f"{FRONTEND_URL}/dashboard")


# ─── Teste E2E 2 ──────────────────────────────────────────────────────────────

def test_e2e_02_usuario_busca_livro_e_solicita_emprestimo(page: Page, admin_e2e):
    """
    Fluxo: login como usuário → busca livro pelo título → solicita empréstimo →
    mensagem de confirmação aparece e solicitação fica visível na lista.

    Valida a integração entre o campo de busca, o botão de solicitação e a API.
    """
    ts = int(time.time() * 1000)
    email = f"e2e02_{ts}@bookstack.test"
    titulo_livro = f"Playwright Book {ts}"

    # Cria livro e usuário via API (setup de dados)
    criar_livro_api(titulo_livro, "E2E Author", 2024, 5)
    criar_usuario_api(f"E2E Loan User {ts}", email, "e2epassword123")

    # Faz login via UI
    _fazer_login_usuario(page, email, "e2epassword123")

    # Busca pelo livro criado
    page.get_by_placeholder("Buscar livros...").fill("Playwright Book")
    page.wait_for_timeout(500)  # debounce de renderização do filtro

    # Clica em "Solicitar Empréstimo" no primeiro resultado
    btn_solicitar = page.get_by_role("button", name="Solicitar Empréstimo").first
    expect(btn_solicitar).to_be_visible(timeout=5000)
    btn_solicitar.click()

    # Mensagem de sucesso deve aparecer
    expect(page.get_by_text("Solicitação enviada")).to_be_visible(timeout=5000)

    # A solicitação deve aparecer na seção "Suas solicitações"
    expect(page.get_by_text("Aguardando aprovação")).to_be_visible(timeout=5000)


# ─── Teste E2E 3 ──────────────────────────────────────────────────────────────

def test_e2e_03_admin_aprova_solicitacao_de_emprestimo(page: Page, admin_e2e):
    """
    Fluxo: cria solicitação pendente via API → admin faz login → aprova a
    solicitação pelo painel → mensagem "aprovada" aparece.

    Valida que o fluxo de aprovação do lado administrativo funciona de ponta a ponta.
    """
    ts = int(time.time() * 1000)
    email_usuario = f"e2e03_{ts}@bookstack.test"
    titulo_livro = f"Approve Book {ts}"

    # Setup: cria livro + usuário + solicitação pendente via API
    livro = criar_livro_api(titulo_livro, "Autor", 2024, 5)
    criar_usuario_api(f"Approve User {ts}", email_usuario, "e2epassword123")
    token = login_usuario_api(email_usuario, "e2epassword123")
    criar_solicitacao_api(token, livro["id"])

    # Admin faz login via UI
    _fazer_login_admin(page, admin_e2e["login"], admin_e2e["senha"], admin_e2e["chave"])

    # Aguarda o painel carregar (seção de solicitações pendentes)
    expect(page.get_by_text("Solicitações Pendentes")).to_be_visible(timeout=8000)

    # Clica em "Aprovar empréstimo" na primeira solicitação pendente
    btn_aprovar = page.get_by_role("button", name="Aprovar empréstimo").first
    expect(btn_aprovar).to_be_visible(timeout=5000)
    btn_aprovar.click()

    # Feedback de sucesso deve aparecer
    expect(page.get_by_text("aprovada com sucesso")).to_be_visible(timeout=5000)


# ─── Teste E2E 4 ──────────────────────────────────────────────────────────────

def test_e2e_04_admin_rejeita_solicitacao_de_emprestimo(page: Page, admin_e2e):
    """
    Fluxo: cria solicitação pendente via API → admin faz login → nega a
    solicitação pelo painel → mensagem "recusada" aparece.

    Valida a funcionalidade de negação implementada na branch atual
    (teste-negacao-emprestimo).
    """
    ts = int(time.time() * 1000)
    email_usuario = f"e2e04_{ts}@bookstack.test"
    titulo_livro = f"Reject Book {ts}"

    # Setup: cria livro + usuário + solicitação pendente via API
    livro = criar_livro_api(titulo_livro, "Autor", 2024, 5)
    criar_usuario_api(f"Reject User {ts}", email_usuario, "e2epassword123")
    token = login_usuario_api(email_usuario, "e2epassword123")
    criar_solicitacao_api(token, livro["id"])

    # Admin faz login via UI
    _fazer_login_admin(page, admin_e2e["login"], admin_e2e["senha"], admin_e2e["chave"])

    # Aguarda o painel carregar
    expect(page.get_by_text("Solicitações Pendentes")).to_be_visible(timeout=8000)

    # Clica em "Negar empréstimo" na primeira solicitação pendente
    btn_negar = page.get_by_role("button", name="Negar empréstimo").first
    expect(btn_negar).to_be_visible(timeout=5000)
    btn_negar.click()

    # Feedback de sucesso deve aparecer
    expect(page.get_by_text("recusada com sucesso")).to_be_visible(timeout=5000)
