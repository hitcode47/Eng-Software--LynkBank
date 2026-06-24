# Guia de Testes — BookStack

## Visão Geral

A suíte de testes do BookStack é dividida em duas camadas independentes:

| Camada | Localização | Framework | Objetivo |
|---|---|---|---|
| Unidade / Integração | `tests/` | pytest + pytest-cov | Verificar lógica do backend isoladamente |
| E2E (ponta a ponta) | `e2e/` | Playwright | Simular um usuário real no navegador |

---

## Instalação

```bash
# Dependências de teste
pip install -r requirements-test.txt

# Instalar navegadores do Playwright (necessário apenas para E2E)
playwright install chromium
```

---

## Testes de Unidade e Integração

### Como executar

```bash
# Roda todos os testes + relatório de cobertura no terminal
pytest

# Gera relatório HTML (abre htmlcov/index.html)
pytest --cov-report=html

# Apenas um arquivo
pytest tests/test_loans.py -v

# Apenas uma classe ou um teste
pytest tests/test_auth_user.py::TestUserLogin::test_login_sucesso -v
```

### Estrutura dos arquivos

```
tests/
├── conftest.py          # Fixtures compartilhadas (banco em memória, tokens, livros)
├── test_utils.py        # Funções utilitárias: hash, validação, geração de token
├── test_auth_user.py    # Registro, login, logout e verificação de token de usuário
├── test_auth_admin.py   # Registro, login, perfil e logout de administrador
├── test_books.py        # CRUD de livros, health check e estatísticas
└── test_loans.py        # Solicitações, aprovação, rejeição, renovação e devolução
```

### Arquitetura dos fixtures

Os fixtures em `conftest.py` seguem uma cadeia de dependências que evita duplicação:

```
app (banco isolado em arquivo temporário)
 └── client (Flask test client)
      ├── registered_user → user_token
      ├── registered_admin → admin_token
      ├── sample_book
      └── pending_loan_request  ← depende de user_token + sample_book
```

Cada teste recebe um banco de dados **vazio e isolado** (escopo `function`). As tabelas são criadas do zero e os arquivos temporários são deletados ao final do teste, garantindo total independência entre testes.

### Cobertura mínima

A configuração em `pytest.ini` exige **≥ 80 %** de cobertura de `app1.py`. O relatório detalhado é gerado em `htmlcov/index.html`.

---

## Testes E2E

### Pré-requisitos

Os testes E2E precisam dos dois servidores **em execução ao mesmo tempo**:

```bash
# Terminal 1 — backend Flask
python app1.py

# Terminal 2 — frontend React/Vite
cd frontend
npm run dev
```

### Como executar

```bash
# Roda os 4 testes E2E (sem coletar cobertura de backend)
pytest e2e/ -v --no-cov

# Com browser visível (útil para depuração)
pytest e2e/ -v --no-cov --headed

# Modo lento para acompanhar visualmente
pytest e2e/ -v --no-cov --headed --slowmo=500
```

### Os 4 testes E2E

#### Teste 1 — Usuário se cadastra e faz login
**Arquivo:** `e2e/test_e2e.py::test_e2e_01_usuario_se_cadastra_e_faz_login`

Simula o fluxo completo de auto-cadastro:
1. Navega até `/login-user`
2. Clica em "Cadastre-se" para abrir o formulário de registro
3. Preenche nome, e-mail e senha
4. Clica em "Registrar" — sistema retorna ao modo login (indicando sucesso)
5. Faz login com as credenciais recém-criadas
6. Verifica que a URL mudou para `/dashboard`

**Por que este teste importa:** valida que o fluxo mais comum de novos usuários funciona de ponta a ponta.

---

#### Teste 2 — Usuário busca livro e solicita empréstimo
**Arquivo:** `e2e/test_e2e.py::test_e2e_02_usuario_busca_livro_e_solicita_emprestimo`

1. Cria livro e usuário via API (setup rápido)
2. Faz login como usuário no frontend
3. Digita no campo de busca — verifica que o livro aparece
4. Clica em "Solicitar Empréstimo"
5. Verifica mensagem de confirmação `"Solicitação enviada"`
6. Verifica que a solicitação aparece na lista com status `"Aguardando aprovação"`

**Por que este teste importa:** valida a integração entre busca, chamada à API e feedback visual ao usuário.

---

#### Teste 3 — Admin aprova solicitação de empréstimo
**Arquivo:** `e2e/test_e2e.py::test_e2e_03_admin_aprova_solicitacao_de_emprestimo`

1. Cria livro, usuário e solicitação pendente via API
2. Admin faz login em `/login-adm`
3. Aguarda o painel carregar (seção "Solicitações Pendentes")
4. Clica em "Aprovar empréstimo"
5. Verifica mensagem `"aprovada com sucesso"`

**Por que este teste importa:** valida o fluxo mais crítico do lado administrativo.

---

#### Teste 4 — Admin nega solicitação de empréstimo
**Arquivo:** `e2e/test_e2e.py::test_e2e_04_admin_rejeita_solicitacao_de_emprestimo`

1. Cria livro, usuário e solicitação pendente via API
2. Admin faz login em `/login-adm`
3. Aguarda o painel carregar
4. Clica em "Negar empréstimo"
5. Verifica mensagem `"recusada com sucesso"`

**Por que este teste importa:** valida especificamente a funcionalidade da branch `teste-negacao-emprestimo`, que é o foco do desenvolvimento atual.

---

## Visão Geral da Cobertura

| Módulo testado | Testes que cobrem |
|---|---|
| Autenticação de usuário | `test_auth_user.py` (35 cenários) |
| Autenticação de administrador | `test_auth_admin.py` (16 cenários) |
| CRUD de livros | `test_books.py` (15 cenários) |
| Empréstimos e solicitações | `test_loans.py` (32 cenários) |
| Funções utilitárias | `test_utils.py` (20 cenários) |

---

## Decisões de Design

### Por que pytest e não unittest?
pytest tem sintaxe mais concisa, suporte nativo a fixtures encadeadas e integração direta com `pytest-cov`. Ideal para projetos Flask.

### Por que Playwright e não Cypress?
Playwright tem suporte nativo a Python (mesma linguagem do backend), permite controle de rede via `page.route()` e roda headless por padrão — mais simples de integrar em CI.

### Por que bancos temporários e não mocks?
Mocks de banco de dados mascaram incompatibilidades entre SQL e a camada Python. Usar SQLite em arquivos temporários garante que os testes exercitam o mesmo código que roda em produção, apenas com dados isolados.

### Por que fixtures encadeadas?
A cadeia `app → client → registered_user → user_token → pending_loan_request` permite que cada teste expresse apenas sua pré-condição real, sem repetir setup. Se um teste precisa de um empréstimo pendente, basta declarar `pending_loan_request` como parâmetro.
