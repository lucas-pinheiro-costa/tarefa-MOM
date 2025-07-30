"""
Este é o nosso novo worker inteligente. Ele vai ouvir todos os preços, e para cada um, verificar se algum alerta deve ser disparado.
Este consumidor faz duas coisas: lê do tópico de preços e, quando encontra uma correspondência, publica uma nova mensagem em uma fila de trabalho específica para notificações. Isso é um padrão de arquitetura muito poderoso.
"""

import pika
import json
import os
import psycopg2
import time
from psycopg2.extras import RealDictCursor

# --- Configurações (semelhante ao arquivador) ---
RABBITMQ_HOST = 'rabbitmq'
EXCHANGE_NAME = 'price_update_topic'
NOTIFICATION_QUEUE = 'notificacoes_queue' # Nova fila para enviar notificações

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def connect_postgres():
    # (Função de conexão idêntica à do arquivador_historico.py)
    while True:
        try:
            conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, cursor_factory=RealDictCursor)
            print("🧠 [Motor de Alertas] Conexão com o PostgreSQL estabelecida.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"🧠 [Motor de Alertas] Falha ao conectar ao PostgreSQL: {e}. Tentando novamente...")
            time.sleep(5)

def main():
    db_conn = connect_postgres()
    
    # Conexão com RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    # Consome da exchange de preços
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=queue_name)
    
    # Declara a fila de notificações para onde VAI PUBLICAR
    channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True)

    print("✅ [Motor de Alertas] Pronto. Verificando preços contra alertas...")

    def callback(ch, method, properties, body):
        dados_do_preco = json.loads(body)
        preco_atual = dados_do_preco['preco']
        id_voo = dados_do_preco['id_voo']
        
        print(f"🧠 [Motor de Alertas] Preço recebido: {id_voo} por R${preco_atual}")
        
        try:
            with db_conn.cursor() as cur:
                # Procura por alertas ativos que correspondam ao voo e ao preço
                cur.execute("""
                    SELECT * FROM alertas
                    WHERE id_voo = %s AND preco_desejado >= %s AND status = 'ativo';
                """, (id_voo, preco_atual))
                alertas_correspondentes = cur.fetchall()

                if alertas_correspondentes:
                    for alerta in alertas_correspondentes:
                        print(f"🎯 Alerta correspondente encontrado para {alerta['email_usuario']}! Preço desejado: R${alerta['preco_desejado']}")
                        
                        # 1. Publica uma mensagem na fila de notificação
                        mensagem_notificacao = {
                            'email': alerta['email_usuario'],
                            'id_voo': id_voo,
                            'preco_encontrado': preco_atual
                        }
                        channel.basic_publish(
                            exchange='',
                            routing_key=NOTIFICATION_QUEUE,
                            body=json.dumps(mensagem_notificacao),
                            properties=pika.BasicProperties(delivery_mode=2) # Mensagem persistente
                        )
                        print(f"   -> Mensagem enviada para a fila de notificação.")

                        # 2. Atualiza o status do alerta para 'disparado' para não notificar de novo
                        cur.execute("UPDATE alertas SET status = 'disparado' WHERE id = %s;", (alerta['id'],))
                        print(f"   -> Status do alerta ID {alerta['id']} atualizado para 'disparado'.")
            
            db_conn.commit()

        except (Exception, psycopg2.Error) as error:
            print(f"❌ [Motor de Alertas] Erro durante o processamento: {error}")
            db_conn.rollback()

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    main()