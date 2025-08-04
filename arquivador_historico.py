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

# Nomes para a configuração de DLQ
DEAD_LETTER_EXCHANGE = 'historico_dlx'
DEAD_LETTER_QUEUE = 'historico_dlq'

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

def validate_message_data(dados_do_preco):
    """Valida se a mensagem contém todos os campos necessários."""
    required_fields = ['id_voo', 'origem', 'destino', 'preco', 'timestamp']
    missing_fields = [field for field in required_fields if field not in dados_do_preco]
    
    if missing_fields:
        raise ValueError(f"Mensagem malformada: campos ausentes: {missing_fields}")
    
    # Validações adicionais
    if not isinstance(dados_do_preco['preco'], (int, float)) or dados_do_preco['preco'] <= 0:
        raise ValueError("Preço deve ser um número positivo")
    
    if not isinstance(dados_do_preco['timestamp'], (int, float)):
        raise ValueError("Timestamp deve ser um número")

def check_dlq_status(channel):
    """Verifica o status da Dead Letter Queue e retorna informações sobre mensagens."""
    try:
        method = channel.queue_declare(queue=DEAD_LETTER_QUEUE, passive=True)
        message_count = method.method.message_count
        if message_count > 0:
            print(f"⚠️  Dead Letter Queue contém {message_count} mensagem(s) para análise")
        return message_count
    except Exception as e:
        print(f"❌ Erro ao verificar status da DLQ: {e}")
        return 0

def setup_dlq_infrastructure(channel):
    """Configura toda a infraestrutura de Dead Letter Queue."""
    print("🔧 Configurando infraestrutura de Dead Letter Queue...")
    
    # 1. Declara a exchange de dead-letter (DLX)
    channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type='fanout', durable=True)
    
    # 2. Declara a fila de dead-letter (DLQ) - durável para persistir mensagens
    channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)
    
    # 3. Liga a DLQ à DLX
    channel.queue_bind(exchange=DEAD_LETTER_EXCHANGE, queue=DEAD_LETTER_QUEUE)
    
    print("✅ Dead Letter Queue configurada com sucesso")

def main():
    db_conn = connect_postgres()
    
    while True:
        try:
            print("🐰 [Arquivador] Tentando conectar ao RabbitMQ...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()

            # Configura a infraestrutura de DLQ
            setup_dlq_infrastructure(channel)
            
            # Verifica se há mensagens na DLQ
            check_dlq_status(channel)

            # Declara a exchange principal de preços
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout', durable=True)

            # Argumentos para configurar a DLQ na fila principal
            # Adiciona TTL de 1 hora para mensagens que ficarem muito tempo na fila
            args = {
                "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
                "x-message-ttl": 3600000  # 1 hora em milissegundos
            }
            
            # Fila durável para garantir que não perdemos mensagens em caso de restart
            result = channel.queue_declare(queue='historico_queue', durable=True, arguments=args)
            queue_name = result.method.queue
            channel.queue_bind(exchange=EXCHANGE_NAME, queue=queue_name)
            
            # Configurar QoS para processar uma mensagem por vez
            channel.basic_qos(prefetch_count=1)

            print("✅ [Arquivador] Pronto com DLQ configurada. Aguardando preços...")

            def callback(ch, method, properties, body):
                try:
                    # Tentativa de parsing JSON com tratamento específico
                    try:
                        dados_do_preco = json.loads(body)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Mensagem não é um JSON válido: {e}")
                    
                    print(f" [📥] Preço recebido: {dados_do_preco.get('preco', 'N/A')}")
                    
                    # Valida a estrutura da mensagem
                    validate_message_data(dados_do_preco)

                    # Tentativa de inserção no banco com rollback automático
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
                    
                    except (psycopg2.Error, psycopg2.OperationalError) as db_error:
                        print(f"❌ Erro de banco de dados: {db_error}")
                        db_conn.rollback()
                        # Para erros de BD, rejeitamos sem requeue para evitar loop infinito
                        raise db_error
                    
                    # Confirma o sucesso do processamento
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception as error:
                    print(f"❌ Erro ao processar mensagem: {error}")
                    print(f"   -> Mensagem: {body.decode('utf-8', errors='replace')}")
                    print(f"   -> Rejeitando mensagem e enviando para a DLQ.")
                    
                    # Rejeita a mensagem SEM recolocá-la na fila original (requeue=False)
                    # Isso fará com que ela seja enviada para a DLQ
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            # MUDANÇA IMPORTANTE: auto_ack=False para controle manual de acknowledgment
            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ [Arquivador] Falha ao conectar ao RabbitMQ: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 [Arquivador] Interrompido pelo usuário.")
            try:
                if 'channel' in locals() and not channel.is_closed:
                    channel.stop_consuming()
                    channel.close()
                if 'connection' in locals() and not connection.is_closed:
                    connection.close()
            except Exception as e:
                print(f"⚠️  Erro ao fechar conexões: {e}")
            finally:
                if db_conn:
                    db_conn.close()
                    print("📦 Conexão com PostgreSQL fechada.")
            break
        except Exception as e:
            print(f"❌ [Arquivador] Erro inesperado: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()