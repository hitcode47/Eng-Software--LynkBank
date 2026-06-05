"Página a ser explicada"


import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}


export default function Dashboard({ apiUrl }) {
  
  const navigate = useNavigate();
  const [loanBooks, setLoanBooks] = useState([]);
  const [books, setBooks] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [loanRequests, setLoanRequests] = useState([]);

"Carrega os empréstimos ativos do usuário."
const loadLoanBooks = async () => {
  setLoading(true);
  setError(null);

  try {
    const token = localStorage.getItem("token");

    const loansResponse = await fetch(`${apiUrl}/api/users/me/loans`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!loansResponse.ok) {
      throw new Error("Erro ao buscar empréstimos");
    }

    const loans = await loansResponse.json();
    const loanBooksPromises = loans.map(async (loan) => {
      const bookResponse = await fetch(`${apiUrl}/api/books/${loan.book_id}`);
      const book = await bookResponse.json();

      return { ...loan, book };
    });

    const loanBooksData = await Promise.all(loanBooksPromises);
    setLoanBooks(loanBooksData);

  } catch (err) {
    console.error("Erro detalhado:", err);
    setError("Erro ao carregar seus empréstimos.");
  } finally {
    setLoading(false);
  }
};

"Carrega as solicitações de empréstimo feitas pelo usuário."
const fetchLoanRequests = async () => {
  try {
    const token = localStorage.getItem("token");

    const response = await fetch(`${apiUrl}/api/users/me/loan-requests`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error("Erro ao buscar solicitações");
    }

    const data = await response.json();
    setLoanRequests(data);

  } catch (err) {
    console.error("Erro ao carregar solicitações:", err);
  }
};
"Renova um empréstimo ativo"
async function handleRenew(loanId) {
  try {
    const token = localStorage.getItem("token");

    const response = await fetch(
      `${apiUrl}/api/loans/${loanId}/renew`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const result = await response.json();

    if (!response.ok) {
      setError(result.message);
      return;
    }

    setMessage(result.message);
    await loadLoanBooks();

  } catch {
    setError("Erro ao renovar empréstimo.");
  }
}

"Busca os dados do usuário autenticado e redireciona para login se não estiver autenticado ou se ocorrer um erro."
async function fetchUserData() {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login-user');
      return;
    }
    const userResponse = await fetch('http://localhost:5000/api/auth/user', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    if (!userResponse.ok) {
      throw new Error('Falha ao buscar dados do usuário');
    }
    const userData = await userResponse.json();
    setCurrentUser(userData);
    localStorage.setItem('currentUser', JSON.stringify(userData));
    await loadLoanBooks();
    await fetchLoanRequests();
  } catch (err) {
    console.error('Erro ao buscar dados do usuário:', err);
    setError('Erro ao carregar dados do usuário.');
    localStorage.removeItem('token');
    localStorage.removeItem('currentUser');
    navigate('/login-user');
  }
}

"Carrega a lista de livros disponíveis para empréstimo."
async function loadBooks() {
  try {
    const response = await fetch(`${apiUrl}/books`);
    const data = await response.json();
    setBooks(Array.isArray(data) ? data : []);
  } catch (err) {
    console.error("Erro ao carregar livros:", err);
  }
}


"Carrega os dados do usuário e os livros disponíveis ao montar o componente."
useEffect(() => {
  fetchUserData();
  loadBooks();
}, [apiUrl, navigate]);

"Filtra os livros com base na consulta de busca do usuário."
const filteredBooks = books.filter((book) => {
  const term = query.toLowerCase();
  return (
    book.title.toLowerCase().includes(term) ||
    book.author.toLowerCase().includes(term) ||
    String(book.year).includes(term)
  );
});

"Solicita um empréstimo para um livro específico."
async function handleRequestLoan(bookId) {
  setError(null);
  setMessage(null);
  const token = localStorage.getItem('token');
  if (!token) {
    setError("Você precisa estar logado para solicitar um livro emprestado.");
    navigate('/login-user');
    return;
  }
  if (!currentUser) {
    setError("Usuário não autenticado.");
    return;
  }
  try {
    const response = await fetch(`${apiUrl}/api/loan-requests`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ book_id: bookId }),
    });
    const result = await response.json();
    console.log('Loan request response:', result);
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('currentUser');
        setError("Sua sessão expirou. Faça login novamente.");
        navigate('/login-user');
        return;
      }
      setError(result.error || "Não foi possível enviar a solicitação.");
      return;
    }
    setMessage("Solicitação enviada ao administrador para aprovação.");
    await fetchLoanRequests();
  } catch (err) {
    setError("Erro na comunicação com o servidor.");
  }
}

"Devolve um livro emprestado, removendo-o da lista de empréstimos ativos."
async function handleReturn(loanId) {
  setError(null);
  setMessage(null);
  try {
    const response = await fetch(`${apiUrl}/loans/${loanId}/return`, {
      method: "PUT",
    });
    const result = await response.json();
    if (!response.ok) {
      setError(result.error || "Falha ao devolver o livro.");
      return;
    }
    setMessage("Livro devolvido com sucesso.");
    setLoanBooks((prev) => prev.filter((loanBook) => loanBook.id !== loanId));
  } catch (err) {
    setError("Erro na comunicação com o servidor.");
  }
}


"Realiza o logout do usuário, limpando os dados de autenticação e redirecionando para a página de login."
function handleLogout() {
  localStorage.removeItem('token');
  localStorage.removeItem('currentUser');
  navigate('/');
}

function getCoverUrl(book) {
  return book.cover || book.cover_url || book.image || book.coverImage || null;
}

"Filtra os empréstimos para mostrar apenas os ativos (aqueles que ainda não foram devolvidos)."
const activeLoanBooks = loanBooks;

  return (
    <section>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 className="section-heading">Bem-vindo, {currentUser?.name}!</h1>
            <p className="page-subtitle">
              Veja seus empréstimos ativos, devolva livros e busque novos títulos.
            </p>
          </div>
          <button className="button button-secondary" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </div>

      {message && <div className="message">{message}</div>}
      {error && <div className="alert">{error}</div>}

      <div className="card" style={{ marginTop: "24px" }}>
        <h2 className="section-heading">Buscar obras</h2>
        <p className="page-subtitle">Pesquise por título, autor ou ano.</p>
        <input
          className="input"
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar livros..."
        />
      </div>

      <div className="grid grid-3" style={{ marginTop: "24px" }}>
        {filteredBooks.length === 0 ? (
          <div className="card">Nenhum livro encontrado.</div>
        ) : (
          filteredBooks.map((book) => {
            const coverUrl = getCoverUrl(book);
            return (
              <div
                key={book.id}
                className="card"
                style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}
              >
                {coverUrl ? (
                  <img
                    src={coverUrl}
                    alt={`Capa de ${book.title}`}
                    style={{
                      width: "120px",
                      height: "160px",
                      objectFit: "cover",
                      borderRadius: "4px",
                      flexShrink: 0,
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: "120px",
                      height: "160px",
                      background: "#f5f5f5",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#666",
                      borderRadius: "4px",
                      flexShrink: 0,
                    }}
                  >
                    Sem capa
                  </div>
                )}
                <div style={{ flex: 1 }}>
                  <h2>{book.title}</h2>
                  <p className="small-text">Autor: {book.author}</p>
                  <p className="small-text">Ano: {book.year}</p>
                  <p className="small-text">Disponíveis: {book.quantity}</p>
                  <button
                    className="button"
                    disabled={book.quantity_available <= 0}
                    onClick={() => handleRequestLoan(book.id)}
                    style={{ marginTop: "18px" }}
                  >
                    Solicitar Empréstimo
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="card" style={{ marginTop: "24px" }}>      
        <div className="card" style={{ marginTop: "24px" }}>
          <h2 className="section-heading">Suas solicitações</h2>

          {loanRequests.length === 0 ? (
            <p>Nenhuma solicitação realizada.</p>
          ) : (
            loanRequests.map((request) => (
              <div
                key={request.id}
                className="card"
                style={{ marginTop: "16px" }}
              >
                <p>
                  <strong>{request.book_title}</strong>
                </p>
            
                <p className="small-text">
                  Status: {
                    request.status === "pending"
                      ? "Aguardando aprovação"
                      : request.status === "approved"
                      ? "Aprovado"
                      : "Recusado"
                  }
                </p>
                
                <p className="small-text">
                  Solicitado em: {formatDate(request.request_date)}
                </p>
              </div>
            ))
          )}
        </div>
        <h2 className="section-heading">Seus empréstimos ativos</h2>
      </div>

      {loading ? (
        <div className="card">Carregando seus empréstimos...</div>
      ) : activeLoanBooks.length === 0 ? (
        <div className="card">Nenhum empréstimo ativo encontrado.</div>
      ) : (
        activeLoanBooks.map((loanBook) => {
          const coverUrl = getCoverUrl(loanBook.book);
          return (
            <div
              key={loanBook.id}
              className="loan-item"
              style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}
            >
              {coverUrl ? (
                <img
                  src={coverUrl}
                  alt={`Capa de ${loanBook.book.title}`}
                  style={{
                    width: "120px",
                    height: "160px",
                    objectFit: "cover",
                    borderRadius: "4px",
                    flexShrink: 0,
                  }}
                />
              ) : (
                <div
                  style={{
                    width: "120px",
                    height: "160px",
                    background: "#f5f5f5",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#666",
                    borderRadius: "4px",
                    flexShrink: 0,
                  }}
                >
                  Sem capa
                </div>
              )}
              <div style={{ flex: 1 }}>
                <p>
                  <strong>{loanBook.book.title}</strong>
                </p>
                <p className="small-text">Autor: {loanBook.book.author}</p>
                <p className="small-text">Ano: {loanBook.book.year}</p>
                <p className="small-text">Emprestado em: {formatDate(loanBook.loan_date)}</p>
                <p className="small-text">Prazo previsto: {loanBook.due_date ? formatDate(loanBook.due_date) : "Não definido"}</p>
                <p className="small-text">Renovações: {loanBook.renewals ?? 0}/5</p>
                <button
                  className="button"
                  onClick={() => handleRenew(loanBook.id)}
                  disabled={loanBook.renewals >= 5}
                  style={{ marginTop: "12px" }}
                >
                  {loanBook.renewals >= 5
                    ? "Limite atingido"
                    : "Renovar por +15 dias"}
                </button>
              </div>
            </div>
          );
        })
      )}
    </section>
  );
}
