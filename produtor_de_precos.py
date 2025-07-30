import pika
import json
import time
import random

# --- Configurações ---
# RABBITMQ_HOST = 'localhost' # Aqui usamos o nome do serviço localmente
RABBITMQ_HOST = 'rabbitmq' # Usamos o nome do serviço do docker-compose
EXCHANGE_NAME = 'price_update_topic' # Nome da nossa exchange (tópico)

# --- Conexão com RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()

# --- Declaração da Exchange ---
# Declara uma exchange do tipo 'fanout'.
# Fanout entrega a mensagem para todas as filas que estão ligadas a ela.
# É o modelo perfeito para o nosso "tópico" de atualização de preços.
channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')

print("✅ Produtor conectado e pronto para enviar preços.")

# --- Loop de Publicação ---
try:
    while True:
        # Simula a descoberta de um novo preço
        preco_simulado = round(random.uniform(500, 4000), 2)
        voo_simulado = {
            'id_voo': 'G31420',
            'origem': 'NAT',
            'destino': 'GRU',
            'preco': preco_simulado,
            'timestamp': time.time()
        }
        
        # Converte o dicionário Python para uma string JSON
        message_body = json.dumps(voo_simulado)
        
        # Publica a mensagem na exchange
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key='',  # routing_key é ignorada em exchanges fanout
            body=message_body
        )
        
        print(f" [✈️] Preço enviado: {message_body}")
        
        # Espera um tempo aleatório para simular a próxima descoberta
        time.sleep(random.uniform(1, 5))

except KeyboardInterrupt:
    print("\n🛑 Produtor interrompido.")
    connection.close()