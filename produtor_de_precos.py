import pika
import json
import time
import random

# --- Configurações ---
# RABBITMQ_HOST = 'localhost' # Aqui usamos o nome do serviço localmente
RABBITMQ_HOST = 'rabbitmq' # Usamos o nome do serviço do docker-compose
EXCHANGE_NAME = 'price_update_topic' # Nome da nossa exchange (tópico)

# Configurações de DLQ (para monitoramento opcional)
DEAD_LETTER_QUEUE = 'historico_dlq'

def connect_rabbitmq():
    """Conecta ao RabbitMQ e retorna connection e channel."""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        return connection, channel
    except Exception as e:
        print(f"❌ Erro ao conectar ao RabbitMQ: {e}")
        return None, None

def check_dlq_messages(channel):
    """Verifica quantas mensagens estão na DLQ."""
    try:
        method = channel.queue_declare(queue=DEAD_LETTER_QUEUE, passive=True)
        message_count = method.method.message_count
        if message_count > 0:
            print(f"⚠️  DLQ contém {message_count} mensagem(s) para análise")
        else:
            print("✅ DLQ está vazia")
        return message_count
    except Exception as e:
        print(f"❌ Erro ao verificar DLQ: {e}")
        return 0

def main():
    """Função principal do produtor de preços."""
    connection = None
    channel = None
    
    try:
        # --- Conexão com RabbitMQ ---
        print("🐰 Conectando ao RabbitMQ...")
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        # --- Declaração da Exchange ---
        # Declara uma exchange do tipo 'fanout'.
        # Fanout entrega a mensagem para todas as filas que estão ligadas a ela.
        # É o modelo perfeito para o nosso "tópico" de atualização de preços.
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout', durable=True)

        print("✅ Produtor conectado e pronto para enviar preços.")

        # --- Loop de Publicação ---
        count = 0
        while True:
            count += 1
            message_body = None

            # A cada 5 mensagens, envia uma mensagem "ruim" para testar a DLQ
            if count % 5 == 0:
                voo_simulado_ruim = {
                    'id_voo': 'G31420',
                    'origem': 'NAT',
                    'destino': 'GRU',
                    # 'preco' está faltando propositalmente para testar DLQ
                    'timestamp': time.time()
                }
                message_body = json.dumps(voo_simulado_ruim)
                print(f" [☠️] Enviando mensagem malformada (teste DLQ) - #{count}")
            else:
                preco_simulado = round(random.uniform(500, 4000), 2)
                voo_simulado = {
                    'id_voo': 'G31420',
                    'origem': 'NAT',
                    'destino': 'GRU',
                    'preco': preco_simulado,
                    'timestamp': time.time()
                }
                message_body = json.dumps(voo_simulado)
                print(f" [✈️] Preço enviado: R${preco_simulado} - #{count}")

            # Publica a mensagem
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key='',
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Torna a mensagem persistente
                )
            )
            
            print(f"✅ Mensagem #{count} enviada com sucesso!")
            
            # Verifica se há mensagens na DLQ a cada 10 mensagens enviadas
            if count % 10 == 0:
                print(f"\n📊 Verificando status da DLQ após {count} mensagens...")
                dlq_conn, dlq_channel = connect_rabbitmq()
                if dlq_channel:
                    try:
                        check_dlq_messages(dlq_channel)
                    except Exception as e:
                        print(f"❌ Erro ao verificar DLQ: {e}")
                    finally:
                        if dlq_conn and not dlq_conn.is_closed:
                            dlq_conn.close()
                else:
                    print("❌ Erro ao conectar para verificação da DLQ.")
                print("=" * 50)
            
            # Pausa entre mensagens
            time.sleep(3)

    except pika.exceptions.AMQPConnectionError as e:
        print(f"❌ Erro de conexão com RabbitMQ: {e}")
    except pika.exceptions.ConnectionClosed:
        print("❌ Conexão com RabbitMQ foi fechada.")
    except KeyboardInterrupt:
        print("\n🛑 Produtor interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        # Fechamento seguro da conexão
        if connection and not connection.is_closed:
            try:
                connection.close()
                print("✅ Conexão com RabbitMQ fechada com sucesso.")
            except Exception as e:
                print(f"⚠️  Erro ao fechar conexão: {e}")

if __name__ == '__main__':
    main()