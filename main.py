import json
import os
import sqlite3
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o FastAPI
app = FastAPI()

# Caminho do banco de dados
DB_PATH = os.getenv("DB_PATH", "senhas.db")

# Conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

# Modelo de dados para entrada/saída
class SenhaBase(BaseModel):
    base: str | None = None
    senha: str
    data_criacao: str

class SenhaCreate(BaseModel):
    base: str | None = None
    total_chars: int

class SenhaUpdate(BaseModel):
    senha: str

# Inicialização do banco de dados
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            senha TEXT NOT NULL,
            base TEXT,
            data_criacao TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Endpoint para criar uma nova senha
@app.post("/senhas/", response_model=SenhaBase)
def criar_senha(senha_data: SenhaCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Gerar a senha
    base = senha_data.base
    total_chars = senha_data.total_chars

    if base:
        # Substituir caracteres da base
        char_map = json.loads(os.getenv("CHAR_MAP", "{}"))
        senha = "".join(char_map.get(letra, letra) for letra in base)
    else:
        # Gerar senha aleatória
        import secrets, string
        alfanumerico = string.ascii_letters + string.digits
        senha = "".join(secrets.choice(alfanumerico) for _ in range(total_chars))

    data_criacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Salvar no banco
    cursor.execute("INSERT INTO senhas (senha, base, data_criacao) VALUES (?, ?, ?)",
                   (senha, base, data_criacao))
    conn.commit()
    conn.close()

    return SenhaBase(senha=senha, base=base, data_criacao=data_criacao)

# Endpoint para listar todas as senhas
@app.get("/senhas/", response_model=List[SenhaBase])
def listar_senhas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM senhas")
    rows = cursor.fetchall()
    conn.close()

    return [SenhaBase(senha=row["senha"], base=row["base"], data_criacao=row["data_criacao"]) for row in rows]

# Endpoint para atualizar uma senha
@app.put("/senhas/{senha_id}", response_model=SenhaBase)
def atualizar_senha(senha_id: int, senha_data: SenhaUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Atualizar a senha no banco
    cursor.execute("UPDATE senhas SET senha = ? WHERE id = ?", (senha_data.senha, senha_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Senha não encontrada")

    # Buscar a senha atualizada
    cursor.execute("SELECT * FROM senhas WHERE id = ?", (senha_id,))
    row = cursor.fetchone()
    conn.close()

    return SenhaBase(senha=row["senha"], base=row["base"], data_criacao=row["data_criacao"])

# Endpoint para apagar uma senha por ID
@app.delete("/senhas/{senha_id}")
def apagar_senha(senha_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Deletar a senha no banco
    cursor.execute("DELETE FROM senhas WHERE id = ?", (senha_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Senha não encontrada")

    conn.commit()
    conn.close()

    return {"message": "Senha apagada com sucesso"}

# Endpoint para apagar todas as senhas
@app.delete("/senhas/")
def apagar_todas_senhas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM senhas")
    conn.commit()
    conn.close()

    return {"message": "Todas as senhas foram apagadas com sucesso"}
