import sqlite3

DB_NAME = 'licitacoes.db'

def get_connection():
    """Retorna uma conexão com o banco, com row_factory para acesso por nome."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Cria a tabela de alertas se ainda não existir."""
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                palavra_chave TEXT NOT NULL
            )
        ''')

def listar_alertas():
    with get_connection() as conn:
        return conn.execute('SELECT id, palavra_chave FROM alertas ORDER BY id').fetchall()

def inserir_alerta(palavra):
    with get_connection() as conn:
        conn.execute('INSERT INTO alertas (palavra_chave) VALUES (?)', (palavra,))

def excluir_alerta(id_alerta):
    with get_connection() as conn:
        conn.execute('DELETE FROM alertas WHERE id = ?', (id_alerta,))