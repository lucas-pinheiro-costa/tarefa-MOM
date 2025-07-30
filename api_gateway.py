import os
import psycopg2
from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
from typing import List
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração da Aplicação FastAPI ---
app = FastAPI(
    title="API de Preços de Viagens",
    description="API para consultar preços de voos e criar alertas.",
    version="1.0.0"
)

# --- Configuração do Banco de Dados ---
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor  # Retorna resultados como dicionários
        )
        return conn
    except psycopg2.OperationalError as e:
        # Em um ambiente real, logaríamos este erro
        print(f"Erro de conexão com o banco de dados: {e}")
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao banco de dados.")

# --- Modelos de Dados (Pydantic) ---
# Define a estrutura da resposta para garantir consistência
class VooResponse(BaseModel):
    id: int
    id_voo: str
    origem: str
    destino: str
    preco: float
    timestamp_captura: datetime
    data_insercao: datetime

    class Config:
        from_attributes = True # Permite mapear de objetos de banco de dados
        
class AlertaCreate(BaseModel):
    email_usuario: str
    id_voo: str
    origem: str
    destino: str
    preco_desejado: float

# --- Endpoints da API ---
@app.get("/api/v1/voos/recentes", 
         response_model=List[VooResponse],
         summary="Consulta os voos mais recentes",
         tags=["Voos"])
def get_voos_recentes():
    """
    Retorna uma lista com os 20 preços de voos mais recentes
    capturados e armazenados no banco de dados.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM historico_precos
                ORDER BY data_insercao DESC
                LIMIT 20;
            """)
            voos = cur.fetchall()
            return voos
    except Exception as e:
        # Em um ambiente real, logaríamos o erro específico
        print(f"Erro ao consultar voos: {e}")
        raise HTTPException(status_code=500, detail="Ocorreu um erro ao processar sua solicitação.")
    finally:
        if conn:
            conn.close()

@app.post("/api/v1/alertas", 
          status_code=201,
          summary="Cria um novo alerta de preço",
          tags=["Alertas"])
def criar_alerta(alerta: AlertaCreate):
    """
    Recebe os dados de um novo alerta e o armazena no banco de dados
    para ser processado posteriormente.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alertas (email_usuario, id_voo, origem, destino, preco_desejado)
                VALUES (%s, %s, %s, %s, %s);
            """, (alerta.email_usuario, alerta.id_voo, alerta.origem, alerta.destino, alerta.preco_desejado))
            conn.commit()
    except Exception as e:
        print(f"Erro ao inserir alerta: {e}")
        raise HTTPException(status_code=500, detail="Ocorreu um erro ao criar o alerta.")
    finally:
        if conn:
            conn.close()
    
    return {"message": "Alerta criado com sucesso e aguardando verificação de preço."}

@app.get("/", include_in_schema=False)
def root():
    return {"message": "Bem-vindo à API de Preços de Viagens! Acesse /docs para ver a documentação."}