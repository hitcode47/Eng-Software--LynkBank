from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from functools import wraps
from datetime import datetime, timedelta
import re

app = Flask(__name__)
CORS(app)
app.secret_key = 'bookstack'

# Databases
USERS_DB = 'users.db'
ADMINS_DB = 'administradores.db'
BOOKS_DB = 'biblioteca.db'

# Sessions
SESSIONS = {}  # user sessions: token -> user_data
ADMIN_SESSIONS = {}  # admin sessions: token -> admin_data
TOKEN_EXPIRY = {}  # admin token expiry

# ==================== DATABASE INITIALIZATION ====================

def init_db():
    """Initialize all databases with required tables"""
    init_users_db()
    init_admins_db()
    init_books_db()

def init_users_db():
    """Initialize users database"""
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_logged_in INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            loan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date TIMESTAMP NOT NULL,
            return_date TIMESTAMP,
            renewals INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS loan_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_by INTEGER NULL,
            approved_at TIMESTAMP NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(approved_by) REFERENCES administradores(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def init_admins_db():
    """Initialize admins database"""
    conn = sqlite3.connect(ADMINS_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS administradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            chave TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def init_books_db():
    """Initialize books database"""
    conn = sqlite3.connect(BOOKS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            quantity_available INTEGER DEFAULT 0,
            quantity_total INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            borrower_name TEXT NOT NULL,
            loan_date DATE NOT NULL,
            return_date DATE NOT NULL,
            returned BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================

def hash_password(password):
    """Hash password using Werkzeug security"""
    return generate_password_hash(password)

def verify_password(password, password_hash):
    """Verify password against hash"""
    return check_password_hash(password_hash, password)

def generate_session_token():
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def gerar_token():
    """Generate admin token"""
    token = secrets.token_urlsafe(32)
    TOKEN_EXPIRY[token] = datetime.utcnow() + timedelta(hours=24)
    return token

def validar_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_entrada(name, email, senha, chave):
    """Validate admin registration input"""
    errors = []
    
    if not name or not name.strip():
        errors.append('Nome é obrigatório.')
    elif len(name.strip()) < 3:
        errors.append('Nome deve ter no mínimo 3 caracteres.')
    
    if not email or not email.strip():
        errors.append('Email é obrigatório.')
    elif not validar_email(email.strip()):
        errors.append('Email inválido.')
    
    if not senha or not senha.strip():
        errors.append('Senha é obrigatória.')
    elif len(senha.strip()) < 6:
        errors.append('Senha deve ter no mínimo 6 caracteres.')
    
    if not chave or not chave.strip():
        errors.append('Chave da biblioteca é obrigatória.')
    elif len(chave.strip()) < 3:
        errors.append('Chave da biblioteca deve ter no mínimo 3 caracteres.')
    
    return errors

def get_db_books():
    """Get books database connection"""
    conn = sqlite3.connect(BOOKS_DB)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== DECORATORS ====================

def token_required(f):
    """Decorator for routes requiring user authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'message': 'Token não fornecido'}), 401
        
        if token not in SESSIONS:
            return jsonify({'message': 'Token inválido ou expirado'}), 401
        
        session_data = SESSIONS[token]
        if session_data['expires'] < datetime.now():
            del SESSIONS[token]
            return jsonify({'message': 'Token expirado'}), 401
        
        user_id = session_data['user_id']
        return f(user_id, *args, **kwargs)
    return decorated

def verificar_token(f):
    """Decorator for routes requiring admin authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'mensagem': 'Token ausente.'}), 401
        
        try:
            token = token.replace('Bearer ', '')
            if token not in ADMIN_SESSIONS:
                return jsonify({'mensagem': 'Token inválido.'}), 401
            
            if datetime.utcnow() > TOKEN_EXPIRY.get(token, datetime.utcnow()):
                del ADMIN_SESSIONS[token]
                del TOKEN_EXPIRY[token]
                return jsonify({'mensagem': 'Token expirado.'}), 401
        except:
            return jsonify({'mensagem': 'Token inválido.'}), 401
        
        return f(token, *args, **kwargs)
    return decorated

# ==================== USER AUTHENTICATION ROUTES ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ('name', 'email', 'password')):
            return jsonify({
                'success': False,
                'message': 'Campos obrigatórios: nome, email e senha'
            }), 400
        
        name = data['name'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        if not name:
            return jsonify({
                'success': False,
                'message': 'Nome não pode estar vazio'
            }), 400
        
        if len(name) > 100:
            return jsonify({
                'success': False,
                'message': 'Nome não pode exceder 100 caracteres'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'Senha deve ter no mínimo 6 caracteres'
            }), 400
        
        if len(password) > 128:
            return jsonify({
                'success': False,
                'message': 'Senha não pode exceder 128 caracteres'
            }), 400
        
        password_hash = hash_password(password)
        
        try:
            conn = sqlite3.connect(USERS_DB)
            c = conn.cursor()
            c.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                     (name, email, password_hash))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Usuário registrado com sucesso',
                'email': email
            }), 201
        
        except sqlite3.IntegrityError:
            return jsonify({
                'success': False,
                'message': 'Este email já está registrado. Por favor, use outro email ou faça login.'
            }), 409
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Erro ao registrar usuário. Por favor, tente novamente.'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return session token"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ('email', 'password')):
            return jsonify({
                'success': False,
                'message': 'Campos obrigatórios: email e senha'
            }), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT id, name, email, password_hash FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Email ou senha incorretos'
            }), 401
        
        user_id = user['id']
        name = user['name']
        password_hash = user['password_hash']
        
        if not verify_password(password, password_hash):
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Email ou senha incorretos'
            }), 401
        
        # Update login status
        c.execute('UPDATE users SET is_logged_in = 1 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        # Create session
        token = generate_session_token()
        SESSIONS[token] = {
            'user_id': user_id,
            'expires': datetime.now() + timedelta(hours=24)
        }
        
        return jsonify({
            'success': True,
            'message': 'Login realizado com sucesso',
            'token': token,
            'user': {
                'id': user_id,
                'name': name,
                'email': email
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Erro ao fazer login. Por favor, tente novamente.'
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    try:
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'message': 'Token não fornecido'}), 400
        
        if token in SESSIONS:
            session_data = SESSIONS[token]
            user_id = session_data['user_id']
            
            conn = sqlite3.connect(USERS_DB)
            c = conn.cursor()
            c.execute('UPDATE users SET is_logged_in = 0 WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            del SESSIONS[token]
        
        return jsonify({'message': 'Logout realizado com sucesso'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Erro ao fazer logout: {str(e)}'}), 500

@app.route('/api/auth/user', methods=['GET'])
@token_required
def get_current_user(user_id):
    """Get current authenticated user data"""
    try:
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT id, name, email, created_at FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'message': 'Usuário não encontrado'}), 404
        
        return jsonify({
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'created_at': user['created_at']
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Erro ao buscar usuário: {str(e)}'}), 500

@app.route('/api/auth/verify', methods=['POST'])
def verify_token_route():
    """Verify if a token is valid"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'message': 'Token não fornecido'}), 400
        
        if token in SESSIONS:
            session_data = SESSIONS[token]
            if session_data['expires'] >= datetime.now():
                return jsonify({'message': 'Token válido', 'valid': True, 'user_id': session_data['user_id']}), 200
            else:
                del SESSIONS[token]
        
        return jsonify({'message': 'Token inválido ou expirado', 'valid': False}), 401
    
    except Exception as e:
        return jsonify({'message': f'Erro ao verificar token: {str(e)}'}), 500

# ==================== ADMIN AUTHENTICATION ROUTES ====================

@app.route('/api/admin/register', methods=['POST'])
def registrar():
    """Register a new administrator"""
    data = request.get_json()
    
    if not data:
        return jsonify({'mensagem': 'Dados inválidos.'}), 400
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    senha = data.get('senha', '').strip()
    chave = data.get('chave', '').strip()
    
    login = name.lower().replace(' ', '').replace('-', '').replace('_', '')[:20]
    
    errors = validar_entrada(name, email, senha, chave)
    if errors:
        return jsonify({'mensagem': ' '.join(errors)}), 400
    
    try:
        conn = sqlite3.connect(ADMINS_DB)
        c = conn.cursor()
        
        c.execute('SELECT id FROM administradores WHERE email = ?', (email,))
        if c.fetchone():
            conn.close()
            return jsonify({'mensagem': 'Email já cadastrado.'}), 409
        
        login_base = login
        counter = 1
        while True:
            c.execute('SELECT id FROM administradores WHERE login = ?', (login,))
            if not c.fetchone():
                break
            login = f"{login_base}{counter}"
            counter += 1
        
        senha_hash = hash_password(senha)
        c.execute(
            'INSERT INTO administradores (name, email, login, senha, chave) VALUES (?, ?, ?, ?, ?)',
            (name, email, login, senha_hash, chave)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'mensagem': 'Registro realizado com sucesso!',
            'login': login
        }), 201
    
    except sqlite3.IntegrityError:
        return jsonify({'mensagem': 'Erro ao registrar: dados duplicados.'}), 409
    except Exception as e:
        return jsonify({'mensagem': f'Erro ao registrar: {str(e)}'}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login"""
    data = request.get_json()
    
    if not data:
        return jsonify({'mensagem': 'Dados inválidos.'}), 400
    
    login_user = data.get('login', '').strip()
    senha = data.get('senha', '').strip()
    chave = data.get('chave', '').strip()
    
    if not login_user or not senha or not chave:
        return jsonify({'mensagem': 'Por favor preencha todos os campos.'}), 400
    
    try:
        conn = sqlite3.connect(ADMINS_DB)
        c = conn.cursor()
        c.execute(
            'SELECT id, login, senha, chave, name, email FROM administradores WHERE login = ?',
            (login_user,)
        )
        admin = c.fetchone()
        conn.close()
        
        if not admin:
            return jsonify({'mensagem': 'Login ou senha incorretos.'}), 401
        
        admin_id, login_db, senha_hash, chave_db, name, email = admin
        
        if not check_password_hash(senha_hash, senha):
            return jsonify({'mensagem': 'Login ou senha incorretos.'}), 401
        
        if chave != chave_db:
            return jsonify({'mensagem': 'Chave da biblioteca incorreta.'}), 401
        
        token = gerar_token()
        ADMIN_SESSIONS[token] = {
            'id': admin_id,
            'login': login_db,
            'name': name,
            'email': email
        }
        
        return jsonify({
            'mensagem': 'Login realizado com sucesso.',
            'token': token
        }), 200
    
    except Exception as e:
        return jsonify({'mensagem': f'Erro ao fazer login: {str(e)}'}), 500

@app.route('/api/admin/perfil', methods=['GET'])
@verificar_token
def perfil(token):
    """Get admin profile"""
    try:
        if token not in ADMIN_SESSIONS:
            return jsonify({'mensagem': 'Sessão inválida.'}), 401
        
        admin = ADMIN_SESSIONS[token]
        
        return jsonify({
            'id': admin['id'],
            'name': admin['name'],
            'email': admin['email'],
            'login': admin['login']
        }), 200
    
    except Exception as e:
        return jsonify({'mensagem': f'Erro ao buscar perfil: {str(e)}'}), 500

@app.route('/api/admin/logout', methods=['POST'])
@verificar_token
def admin_logout(token):
    """Admin logout"""
    if token in ADMIN_SESSIONS:
        del ADMIN_SESSIONS[token]
    if token in TOKEN_EXPIRY:
        del TOKEN_EXPIRY[token]
    
    return jsonify({'mensagem': 'Logout realizado com sucesso.'}), 200

# ==================== BOOKS MANAGEMENT ROUTES ====================

@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book"""
    data = request.get_json()
    
    try:
        title = data.get('title')
        author = data.get('author')
        year = data.get('year')
        quantity_available = data.get('quantity_available', 1)
        
        if not title or not author or not year:
            return jsonify({'error': 'Campos obrigatórios: title, author, year'}), 400
        
        conn = get_db_books()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO books (title, author, year, quantity_available, quantity_total)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, author, year, quantity_available, quantity_available))
        
        conn.commit()
        book_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'id': book_id,
            'title': title,
            'author': author,
            'year': year,
            'quantity_available': quantity_available
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/books', methods=['GET'])
def get_books():
    """Get all available books"""
    try:
        conn = get_db_books()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, author, year, quantity_available, quantity_total
            FROM books
            WHERE quantity_available > 0
        ''')
        
        books = []
        for row in cursor.fetchall():
            books.append({
                'id': row['id'],
                'title': row['title'],
                'author': row['author'],
                'year': row['year'],
                'quantity': row['quantity_available']
            })
        
        conn.close()
        return jsonify(books), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get specific book data"""
    try:
        conn = get_db_books()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, author, year, quantity_available, quantity_total FROM books WHERE id = ?', (book_id,))
        book = cursor.fetchone()
        conn.close()
        
        if not book:
            return jsonify({'message': 'Livro não encontrado'}), 404
        
        return jsonify(dict(book)), 200
    
    except Exception as e:
        return jsonify({'message': f'Erro ao buscar livro: {str(e)}'}), 500

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book from the database"""
    try:
        conn = get_db_books()
        cursor = conn.cursor()
        
        # Verify book exists
        cursor.execute('SELECT id, title FROM books WHERE id = ?', (book_id,))
        book = cursor.fetchone()
        
        if not book:
            conn.close()
            return jsonify({'error': 'Livro não encontrado'}), 404
        
        # Delete the book
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Livro "{book["title"]}" deletado com sucesso',
            'book_id': book_id
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Erro ao deletar livro: {str(e)}'}), 500


@app.route('/api/admin/loans/<int:loan_id>/return', methods=['PUT'])
@verificar_token
def admin_return_loan(token, loan_id):
    try:
        conn_users = sqlite3.connect(USERS_DB)
        conn_users.row_factory = sqlite3.Row
        cursor_users = conn_users.cursor()

        cursor_users.execute('''
            SELECT book_id
            FROM loans
            WHERE id = ? AND return_date IS NULL
        ''', (loan_id,))

        loan = cursor_users.fetchone()

        if not loan:
            conn_users.close()
            return jsonify({'error': 'Empréstimo não encontrado'}), 404

        book_id = loan['book_id']

        cursor_users.execute('''
            UPDATE loans
            SET return_date = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), loan_id))

        conn_books = get_db_books()
        cursor_books = conn_books.cursor()

        cursor_books.execute('''
            UPDATE books
            SET quantity_available = quantity_available + 1
            WHERE id = ?
        ''', (book_id,))

        conn_users.commit()
        conn_books.commit()

        conn_users.close()
        conn_books.close()

        return jsonify({
            'message': 'Livro devolvido com sucesso'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ==================== LOAN REQUESTS ROUTES ====================

@app.route('/api/users/me/loan-requests', methods=['GET'])
@token_required
def get_user_requests(user_id):
    try:
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, book_id, status, request_date
            FROM loan_requests
            WHERE user_id = ?
            ORDER BY request_date DESC
        ''', (user_id,))

        requests = cursor.fetchall()
        results = []

        conn_books = get_db_books()
        cursor_books = conn_books.cursor()

        for req in requests:
            cursor_books.execute(
                'SELECT title FROM books WHERE id = ?',
                (req['book_id'],)
            )

            book = cursor_books.fetchone()

            results.append({
                'id': req['id'],
                'book_id': req['book_id'],
                'book_title': book['title'] if book else 'Livro removido',
                'status': req['status'],
                'request_date': req['request_date']
            })

        conn.close()
        conn_books.close()

        return jsonify(results), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/loan-requests', methods=['POST'])
@token_required
def create_loan_request(user_id):
    """Create a loan request"""

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados inválidos'}), 400

        book_id = data.get('book_id')

        if not book_id:
            return jsonify({'error': 'book_id é obrigatório'}), 400

        # Verifica livro
        conn_books = get_db_books()
        cursor_books = conn_books.cursor()

        cursor_books.execute(
            'SELECT id, quantity_available, title FROM books WHERE id = ?',
            (book_id,)
        )

        book = cursor_books.fetchone()
        conn_books.close()

        if not book:
            return jsonify({'error': 'Livro não encontrado'}), 404

        if book['quantity_available'] <= 0:
            return jsonify({'error': 'Livro sem estoque disponível'}), 400

        # Verifica banco de usuários
        conn_users = sqlite3.connect(USERS_DB)
        conn_users.row_factory = sqlite3.Row
        cursor_users = conn_users.cursor()

        # Já possui solicitação pendente?
        cursor_users.execute('''
            SELECT id
            FROM loan_requests
            WHERE user_id = ?
            AND book_id = ?
            AND status = 'pending'
        ''', (user_id, book_id))

        existing_request = cursor_users.fetchone()

        if existing_request:
            conn_users.close()
            return jsonify({
                'error': 'Você já possui uma solicitação pendente para este livro.'
            }), 400

        # Já está com o livro emprestado?
        cursor_users.execute('''
            SELECT id
            FROM loans
            WHERE user_id = ?
            AND book_id = ?
            AND return_date IS NULL
        ''', (user_id, book_id))

        existing_loan = cursor_users.fetchone()

        if existing_loan:
            conn_users.close()
            return jsonify({
                'error': 'Você já está com este livro emprestado.'
            }), 400

        # Criar solicitação
        cursor_users.execute('''
            INSERT INTO loan_requests (user_id, book_id, status)
            VALUES (?, ?, 'pending')
        ''', (user_id, book_id))

        conn_users.commit()

        request_id = cursor_users.lastrowid

        cursor_users.execute(
            'SELECT request_date FROM loan_requests WHERE id = ?',
            (request_id,)
        )

        request_row = cursor_users.fetchone()

        conn_users.close()

        return jsonify({
            'id': request_id,
            'user_id': user_id,
            'book_id': book_id,
            'status': 'pending',
            'request_date': request_row['request_date'],
            'message': 'Solicitação enviada com sucesso'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/loan-requests', methods=['GET'])
@verificar_token
def get_pending_loan_requests(token):
    """Get all pending loan requests"""
    try:
        conn_users = sqlite3.connect(USERS_DB)
        conn_users.row_factory = sqlite3.Row
        cursor_users = conn_users.cursor()
        
        cursor_users.execute('''
            SELECT lr.id, lr.user_id, lr.book_id, lr.status, lr.request_date,
                   u.name as user_name
            FROM loan_requests lr
            JOIN users u ON lr.user_id = u.id
            WHERE lr.status = 'pending'
            ORDER BY lr.request_date ASC
        ''')
        
        pending_requests = []
        for row in cursor_users.fetchall():
            # Get book info
            conn_books = get_db_books()
            cursor_books = conn_books.cursor()
            cursor_books.execute('SELECT id, title FROM books WHERE id = ?', (row['book_id'],))
            book = cursor_books.fetchone()
            conn_books.close()
            
            if book:
                pending_requests.append({
                    'request_id': row['id'],
                    'user_id': row['user_id'],
                    'user_name': row['user_name'],
                    'book_id': row['book_id'],
                    'book_title': book['title'],
                    'status': row['status'],
                    'request_date': row['request_date']
                })
        
        conn_users.close()
        return jsonify(pending_requests), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/loan-requests/<int:request_id>/reject', methods=['PUT'])
@verificar_token
def reject_loan_request(token, request_id):
    """Reject a loan request"""
    try:
        # Get admin info
        if token not in ADMIN_SESSIONS:
            return jsonify({'mensagem': 'Sessão inválida.'}), 401
        
        admin = ADMIN_SESSIONS[token]
        admin_id = admin['id']
        
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, status
            FROM loan_requests
            WHERE id = ?
        ''', (request_id,))

        request_data = cursor.fetchone()

        if not request_data:
            conn.close()
            return jsonify({'error': 'Solicitação não encontrada'}), 404

        if request_data['status'] != 'pending':
            conn.close()
            return jsonify({'error': 'Solicitação já foi processada'}), 400

        # Update loan request status to rejected with admin info
        rejected_at = datetime.now().isoformat()
        cursor.execute('''
            UPDATE loan_requests
            SET status = 'rejected', approved_by = ?, approved_at = ?
            WHERE id = ?
        ''', (admin_id, rejected_at, request_id))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Solicitação rejeitada com sucesso',
            'request_id': request_id,
            'status': 'rejected'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/loan-requests/<int:request_id>/approve', methods=['PUT'])
@verificar_token
def approve_loan_request(token, request_id):
    """Approve a loan request and create the actual loan"""
    try:
        # Get admin info
        if token not in ADMIN_SESSIONS:
            return jsonify({'mensagem': 'Sessão inválida.'}), 401
        
        admin = ADMIN_SESSIONS[token]
        admin_id = admin['id']
        
        # Get loan request
        conn_users = sqlite3.connect(USERS_DB)
        conn_users.row_factory = sqlite3.Row
        cursor_users = conn_users.cursor()
        
        cursor_users.execute('''
            SELECT id, user_id, book_id, status
            FROM loan_requests
            WHERE id = ?
        ''', (request_id,))
        
        loan_request = cursor_users.fetchone()
        
        if not loan_request:
            conn_users.close()
            return jsonify({'error': 'Solicitação não encontrada'}), 404
        
        if loan_request['status'] != 'pending':
            conn_users.close()
            return jsonify({'error': 'Solicitação já foi processada'}), 400
        
        user_id = loan_request['user_id']
        book_id = loan_request['book_id']
        
        # Check book availability
        conn_books = get_db_books()
        cursor_books = conn_books.cursor()
        cursor_books.execute('SELECT quantity_available FROM books WHERE id = ?', (book_id,))
        book = cursor_books.fetchone()
        
        if not book:
            conn_users.close()
            conn_books.close()
            return jsonify({'error': 'Livro não encontrado'}), 404
        
        if book['quantity_available'] <= 0:
            conn_users.close()
            conn_books.close()
            return jsonify({'error': 'Livro sem estoque disponível'}), 400
        
        # Create the actual loan
        
        loan_date = datetime.now()
        due_date = loan_date + timedelta(days=15)

        cursor_users.execute('''
            INSERT INTO loans (user_id, book_id, loan_date, due_date, return_date, renewals)
            VALUES (?, ?, ?, ?, NULL, 0)
        ''', (
            user_id,
            book_id,
            loan_date.isoformat(),
            due_date.isoformat()
        ))
        
        # Reduce available quantity
        cursor_books.execute('''
            UPDATE books SET quantity_available = quantity_available - 1
            WHERE id = ?
        ''', (book_id,))
        
        # Update loan request status
        approved_at = datetime.now().isoformat()
        cursor_users.execute('''
            UPDATE loan_requests 
            SET status = 'approved', approved_by = ?, approved_at = ?
            WHERE id = ?
        ''', (admin_id, approved_at, request_id))
        
        conn_users.commit()
        conn_books.commit()
        conn_users.close()
        conn_books.close()
        
        return jsonify({
            'message': 'Solicitação aprovada e empréstimo criado com sucesso',
            'request_id': request_id,
            'status': 'approved'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== LOANS ROUTES ====================

@app.route('/api/loans/<int:loan_id>/renew', methods=['PUT'])
@token_required
def renew_loan(user_id, loan_id):
    try:
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT user_id, due_date, renewals
            FROM loans
            WHERE id = ? AND return_date IS NULL
        ''', (loan_id,))

        loan = c.fetchone()

        if not loan:
            conn.close()
            return jsonify({'message': 'Empréstimo não encontrado'}), 404

        if loan['user_id'] != user_id:
            conn.close()
            return jsonify({'message': 'Acesso negado'}), 403

        if loan['renewals'] >= 5:
            conn.close()
            return jsonify({
                'message': 'Limite máximo de renovações atingido'
            }), 400

        current_due = datetime.fromisoformat(loan['due_date'])
        new_due = current_due + timedelta(days=15)

        c.execute('''
            UPDATE loans
            SET due_date = ?, renewals = renewals + 1
            WHERE id = ?
        ''', (new_due.isoformat(), loan_id))

        conn.commit()
        conn.close()

        return jsonify({
            'message': 'Empréstimo renovado com sucesso',
            'new_due_date': new_due.isoformat()
        }), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/loans', methods=['POST'])
def create_loan():
    """Register a new book loan"""
    data = request.get_json()
    
    try:
        book_id = data.get('book_id')
        borrower_name = data.get('borrower_name')
        loan_date = data.get('loan_date')
        return_date = data.get('return_date')
        
        if not all([book_id, borrower_name, loan_date, return_date]):
            return jsonify({'error': 'Campos obrigatórios: book_id, borrower_name, loan_date, return_date'}), 400
        
        conn = get_db_books()
        cursor = conn.cursor()
        
        # Check if book exists and has availability
        cursor.execute('SELECT quantity_available FROM books WHERE id = ?', (book_id,))
        book = cursor.fetchone()
        
        if not book:
            conn.close()
            return jsonify({'error': 'Livro não encontrado'}), 404
        
        if book['quantity_available'] <= 0:
            conn.close()
            return jsonify({'error': 'Livro sem estoque disponível'}), 400
        
        # Register loan
        cursor.execute('''
            INSERT INTO loans_books (book_id, borrower_name, loan_date, return_date)
            VALUES (?, ?, ?, ?)
        ''', (book_id, borrower_name, loan_date, return_date))
        
        # Reduce available quantity
        cursor.execute('''
            UPDATE books SET quantity_available = quantity_available - 1
            WHERE id = ?
        ''', (book_id,))
        
        conn.commit()
        loan_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'id': loan_id,
            'book_id': book_id,
            'borrower_name': borrower_name,
            'loan_date': loan_date,
            'return_date': return_date
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/loans', methods=['GET'])
def get_loans():
    try:
        conn_users = sqlite3.connect(USERS_DB)
        conn_users.row_factory = sqlite3.Row
        cursor = conn_users.cursor()

        cursor.execute('''
            SELECT l.id, l.book_id, l.loan_date, l.due_date, l.return_date,
            u.name as borrower_name
            FROM loans l
            JOIN users u ON l.user_id = u.id
            WHERE l.return_date IS NULL
        ''')

        loans = []

        for row in cursor.fetchall():
            conn_books = get_db_books()
            cursor_books = conn_books.cursor()

            cursor_books.execute(
                'SELECT title, author, year FROM books WHERE id = ?',
                (row['book_id'],)
            )

            book = cursor_books.fetchone()
            conn_books.close()

            if book:
                loans.append({
                    'id': row['id'],
                    'book_id': row['book_id'],
                    'title': book['title'],
                    'author': book['author'],
                    'year': book['year'],
                    'borrowerName': row['borrower_name'],
                    'loanDate': row['loan_date'],
                    'dueDate': row['due_date'],
                    'returnDate': row['return_date']
                })

        conn_users.close()
        return jsonify(loans), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/users/me/loans', methods=['GET'])
@token_required
def get_user_loans(user_id):
    try:
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT 
                id,
                user_id,
                book_id,
                loan_date,
                due_date,
                return_date,
                renewals
            FROM loans
            WHERE user_id = ?
            AND return_date IS NULL
            ORDER BY loan_date DESC
        ''', (user_id,))

        loans = c.fetchall()
        conn.close()

        return jsonify([dict(loan) for loan in loans]), 200

    except Exception as e:
        return jsonify({
            'message': f'Erro ao buscar empréstimos: {str(e)}'
        }), 500


@app.route('/loans/<int:loan_id>', methods=['DELETE'])
def return_loan(loan_id):
    """Register book return"""
    try:
        conn = get_db_books()
        cursor = conn.cursor()
        
        # Find loan
        cursor.execute('SELECT book_id FROM loans_books WHERE id = ? AND returned = 0', (loan_id,))
        loan = cursor.fetchone()
        
        if not loan:
            conn.close()
            return jsonify({'error': 'Empréstimo não encontrado ou já devolvido'}), 404
        
        book_id = loan['book_id']
        
        # Mark as returned
        cursor.execute('UPDATE loans_books SET returned = 1 WHERE id = ?', (loan_id,))
        
        # Increase available quantity
        cursor.execute('''
            UPDATE books SET quantity_available = quantity_available + 1
            WHERE id = ?
        ''', (book_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Livro devolvido com sucesso'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/loans/<int:loan_id>/return', methods=['PUT'])
@token_required
def return_loan_user(user_id, loan_id):
    """Mark a loan as returned (user endpoint)"""
    try:
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT user_id, book_id FROM loans WHERE id = ?', (loan_id,))
        loan = c.fetchone()
        
        if not loan:
            conn.close()
            return jsonify({'message': 'Empréstimo não encontrado'}), 404
        
        if loan['user_id'] != user_id:
            conn.close()
            return jsonify({'message': 'Acesso negado'}), 403
        
        book_id = loan['book_id']
        
        # Update return date
        c.execute('UPDATE loans SET return_date = ? WHERE id = ?', 
                 (datetime.now().isoformat(), loan_id))
        
        # Increment available quantity
        conn_books = get_db_books()
        cursor_books = conn_books.cursor()
        cursor_books.execute('UPDATE books SET quantity_available = quantity_available + 1 WHERE id = ?', (book_id,))
        conn_books.commit()
        conn_books.close()
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Livro devolvido com sucesso'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Erro ao devolver livro: {str(e)}'}), 500

# ==================== STATISTICS ROUTE ====================

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get library statistics"""
    try:
        conn = get_db_books()
        cursor = conn.cursor()
        
        # Total books
        cursor.execute('SELECT COUNT(*) as total FROM books')
        total_books = cursor.fetchone()['total']
        
        # Total available
        cursor.execute('SELECT SUM(quantity_available) as total FROM books')
        total_available = cursor.fetchone()['total'] or 0
        
        # Total loaned
        cursor.execute('SELECT COUNT(*) as total FROM loans_books WHERE returned = 0')
        total_loaned = cursor.fetchone()['total']
        
        conn.close()
        
        return jsonify({
            'total_books': total_books,
            'total_available': total_available,
            'total_loaned': total_loaned
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'OK'}), 200

# ==================== MAIN ====================

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='localhost', port=5000)
