import pika
import json
import os
import psycopg2
from datetime import datetime
import time

# --- Configurações ---
# RABBITMQ_HOST = 'localhost' # Aqui usamos o nome do serviço localmente
RABBITMQ_HOST = 'rabbitmq' # Usamos o nome do serviço do docker-compose
EXCHANGE_NAME = 'price_update_topic'

# Carrega as credenciais do banco de dados a partir das variáveis de ambiente
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def connect_postgres():
    """Conecta ao banco de dados PostgreSQL e retorna a conexão."""
    while True:
        try:
            print("📦 Tentando conectar ao PostgreSQL...")
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            print("✅ Conexão com o PostgreSQL estabelecida com sucesso.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"❌ Falha ao conectar ao PostgreSQL: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)

def main():
    db_conn = connect_postgres()
    
    while True:
        try:
            print("🐰 Tentando conectar ao RabbitMQ...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(exchange=EXCHANGE_NAME, queue=queue_name)

            print("✅ Consumidor/Arquivador pronto. Aguardando preços...")

            def callback(ch, method, properties, body):
                dados_do_preco = json.loads(body)
                print(f" [📥] Preço recebido: {dados_do_preco['preco']}")

                try:
                    with db_conn.cursor() as cur:
                        # Converte o timestamp UNIX para um objeto datetime
                        timestamp_captura = datetime.fromtimestamp(dados_do_preco['timestamp'])

                        insert_query = """
                            INSERT INTO historico_precos (id_voo, origem, destino, preco, timestamp_captura)
                            VALUES (%s, %s, %s, %s, %s);
                        """
                        data_tuple = (
                            dados_do_preco['id_voo'],
                            dados_do_preco['origem'],
                            dados_do_preco['destino'],
                            dados_do_preco['preco'],
                            timestamp_captura
                        )
                        cur.execute(insert_query, data_tuple)
                        db_conn.commit()
                        print("   [💾] Dados salvos no PostgreSQL.")

                except (Exception, psycopg2.Error) as error:
                    print(f"❌ Erro ao inserir no PostgreSQL: {error}")
                    db_conn.rollback() # Desfaz a transação em caso de erro

            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ Falha ao conectar ao RabbitMQ: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Arquivador interrompido.")
            if db_conn:
                db_conn.close()
            break

if __name__ == '__main__':
    main()