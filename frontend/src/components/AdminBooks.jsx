import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function AdminBooks({ apiUrl, librarianId }) {
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [year, setYear] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [stockBooks, setStockBooks] = useState([]);
  const [loanedBooks, setLoanedBooks] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [currentAdmin, setCurrentAdmin] = useState(null);

  function getCoverUrl(book) {
    return book.cover || book.cover_url || book.image || book.coverImage || null;
  }

useEffect(() => {
  fetchAdminData();
}, []);

if (!currentAdmin) {
  return <div className="card">Carregando painel administrativo...</div>;
}

async function fetchAdminData() {
  try {
    const token = localStorage.getItem("adminToken");

    if (!token) {
      navigate("/login-adm");
      return;
    }

    const response = await fetch(`${apiUrl}/api/admin/perfil`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error("Sessão inválida");
    }

    const adminData = await response.json();

    setCurrentAdmin(adminData);

    await fetchBooks();
    await fetchLoans();
    await fetchPendingRequests();

  } catch (err) {
    console.error("Erro ao validar admin:", err);

    localStorage.removeItem("adminToken");
    navigate("/login-admin");
  }
}

  async function fetchBooks() {
    try {
      const response = await fetch(`${apiUrl}/books`);
      if (!response.ok) throw new Error("Erro ao buscar livros");
      const books = await response.json();
      setStockBooks(books);
    } catch (err) {
      console.error("Erro ao buscar livros:", err);
    }
  }

  async function fetchLoans() {
    try {
      const response = await fetch(`${apiUrl}/loans`);
      if (!response.ok) throw new Error("Erro ao buscar empréstimos");
      const loans = await response.json();
      setLoanedBooks(loans);
    } catch (err) {
      console.error("Erro ao buscar empréstimos:", err);
    }
  }

  async function fetchPendingRequests() {
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${apiUrl}/api/admin/loan-requests`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) throw new Error("Erro ao buscar solicitações pendentes");
      const requests = await response.json();
      setPendingRequests(requests);
    } catch (err) {
      console.error("Erro ao buscar solicitações pendentes:", err);
    }
  }

  async function approveRequest(requestId) {
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(
        `${apiUrl}/api/admin/loan-requests/${requestId}/approve`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || result.mensagem || "Erro ao aprovar solicitação.");
      }

      setMessage("Solicitação aprovada com sucesso.");
      await fetchPendingRequests();
      await fetchBooks();
      await fetchLoans();
    } catch (err) {
      console.error("Erro ao aprovar solicitação:", err);
      setError(err.message || "Erro ao aprovar solicitação.");
    } finally {
      setLoading(false);
    }
  }

async function rejectRequest(requestId) {
  setError(null);
  setMessage(null);
  setLoading(true);

  try {
    const token = localStorage.getItem("adminToken");

    const response = await fetch(
      `${apiUrl}/api/admin/loan-requests/${requestId}/reject`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Erro ao recusar solicitação.");
    }

    setMessage("Solicitação recusada com sucesso.");
    await fetchPendingRequests();

  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (!title || !author || !year) {
      setError("Preencha todos os campos do formulário.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${apiUrl}/books`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          author,
          year: Number(year),
          quantity_available: Number(quantity),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        setError(result.error || "Não foi possível cadastrar o livro.");
        return;
      }

      const newBook = {
        id: result.id,
        title: result.title,
        author: result.author,
        year: result.year,
        quantity: result.quantity_available,
      };

      setStockBooks((prev) => [...prev, newBook]);
      setTitle("");
      setAuthor("");
      setYear("");
      setQuantity(1);
      setMessage(`Livro "${newBook.title}" cadastrado com sucesso.`);
    } catch (err) {
      setError("Erro ao enviar dados para o servidor.");
    } finally {
      setLoading(false);
    }
  }


 async function handleReturn(loanId) {
  setLoading(true);

  try {
    const token = localStorage.getItem("adminToken");

    const response = await fetch(
      `${apiUrl}/api/admin/loans/${loanId}/return`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Erro ao devolver livro");
    }

    setMessage("Livro devolvido com sucesso.");

    await fetchLoans();
    await fetchBooks();

  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

async function handleDeleteBook(bookId, bookTitle) {
  const confirmDelete = window.confirm(
    `Tem certeza que deseja excluir o livro "${bookTitle}"?`
  );

  if (!confirmDelete) return;

  setLoading(true);

  try {
    const response = await fetch(`${apiUrl}/books/${bookId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || "Erro ao excluir livro");
    }

    setMessage(`Livro "${bookTitle}" excluído com sucesso.`);
    await fetchBooks();
  } catch (err) {
    setError(err.message || "Erro ao excluir livro");
  } finally {
    setLoading(false);
  }
}

  return (
    <section>
      <div className="card">
        <h1 className="section-heading">Bem-vindo, {currentAdmin?.name}</h1>
        <p className="page-subtitle">
          Adicione um novo livro ao acervo usando o formulário abaixo.
        </p>
      </div>

      {message && <div className="message">{message}</div>}
      {error && <div className="alert">{error}</div>}

      <div className="card" style={{ marginTop: "24px" }}>
        <form onSubmit={handleSubmit}>
          <label>
            Título
            <input
              className="input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Nome do livro"
              disabled={loading}
            />
          </label>

          <label style={{ marginTop: "16px", display: "block" }}>
            Autor
            <input
              className="input"
              value={author}
              onChange={(event) => setAuthor(event.target.value)}
              placeholder="Nome do autor"
              disabled={loading}
            />
          </label>

          <div
            style={{
              display: "grid",
              gap: "16px",
              marginTop: "16px",
              gridTemplateColumns: "1fr 1fr",
            }}
          >
            <label>
              Ano
              <input
                className="input"
                type="number"
                value={year}
                onChange={(event) => setYear(event.target.value)}
                placeholder="2025"
                disabled={loading}
              />
            </label>
            <label>
              Quantidade disponível
              <input
                className="input"
                type="number"
                min="1"
                value={quantity}
                onChange={(event) => setQuantity(Number(event.target.value))}
                disabled={loading}
              />
            </label>
          </div>

          <button
            type="submit"
            className="button"
            style={{ marginTop: "20px" }}
            disabled={loading}
          >
            {loading ? "Adicionando..." : "Adicionar livro"}
          </button>
        </form>
      </div>

      <div className="card" style={{ marginTop: "24px" }}>
        <h2>Em estoque</h2>
        {stockBooks.length === 0 ? (
          <p>Nenhum livro em estoque.</p>
        ) : (
          stockBooks.map((book) => {
            const coverUrl = getCoverUrl(book);
            return (
              <div
                key={book.id}
                className="card"
                style={{ marginBottom: "16px", display: "flex", gap: "16px", alignItems: "flex-start" }}
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
                  <p>
                    <strong>ID:</strong> {book.id}
                  </p>
                  <p>
                    <strong>Nome do livro:</strong> {book.title}
                  </p>
                  <p>
                    <strong>Autor:</strong> {book.author}
                  </p>
                  <p>
                    <strong>Ano:</strong> {book.year}
                  </p>
                  <p>
                    <strong>Quantidade:</strong> {book.quantity}
                  </p>
                  <button
                    type="button"
                    className="button"
                    onClick={() => handleDeleteBook(book.id, book.title)}
                    disabled={loading}
                    style={{ marginTop: "12px", backgroundColor: "#dc3545", borderColor: "#dc3545" }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = "#c82333"}
                    onMouseLeave={(e) => e.target.style.backgroundColor = "#dc3545"}
                  >
                    {loading ? "Processando..." : "Excluir livro"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="card" style={{ marginTop: "24px" }}>
        <h2>Solicitações Pendentes</h2>
        {pendingRequests.length === 0 ? (
          <p>Nenhuma solicitação pendente.</p>
        ) : (
          pendingRequests.map((request) => (
            <div key={request.request_id} className="card" style={{ marginBottom: "16px" }}>
              <p>
                <strong>Usuário:</strong> {request.user_name}
              </p>
              <p>
                <strong>Livro:</strong> {request.book_title}
              </p>
              <p>
                <strong>Data da solicitação:</strong> {request.request_date}
              </p>
              <div style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
                <button
                  type="button"
                  className="button"
                  onClick={() => approveRequest(request.request_id)}
                  disabled={loading}
                  style={{ flex: 1 }}
                >
                  {loading ? "Processando..." : "Aprovar empréstimo"}
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={() => rejectRequest(request.request_id)}
                  disabled={loading}
                  style={{ flex: 1, backgroundColor: "#dc3545", borderColor: "#dc3545" }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = "#c82333"}
                  onMouseLeave={(e) => e.target.style.backgroundColor = "#dc3545"}
                >
                  {loading ? "Processando..." : "Negar empréstimo"}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="card" style={{ marginTop: "24px" }}>
        <h2>Emprestados</h2>
        {loanedBooks.length === 0 ? (
          <p>Nenhum livro emprestado.</p>
        ) : (
          loanedBooks.map((item) => (
            <div key={item.id} className="card" style={{ marginBottom: "16px" }}>
              <p>
                <strong>ID:</strong> {item.id}
              </p>
              <p>
                <strong>Nome do livro:</strong> {item.title}
              </p>
              <p>
                <strong>Autor:</strong> {item.author}
              </p>
              <p>
                <strong>Quem pegou:</strong> {item.borrowerName}
              </p>
              <p>
                <strong>Data de empréstimo:</strong> {new Date(item.loanDate).toLocaleDateString("pt-BR")}
              </p>
              <p>
                <strong>Prazo previsto:</strong> {new Date(item.dueDate).toLocaleDateString("pt-BR")}
              </p>
              <button
                type="button"
                className="button"
                style={{ marginTop: "12px" }}
                onClick={() => handleReturn(item.id)}
                disabled={loading}
              >
                {loading ? "Processando..." : "Marcar como devolvido"}
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
 