import pika
import json

# --- Teste de conexão ---
try:
    test_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    test_connection.close()
    print('✅ Conexão com RabbitMQ bem-sucedida.')
except pika.exceptions.AMQPConnectionError:
    print('❌ Falha ao conectar ao RabbitMQ. Verifique se o serviço está rodando e acessível.')
    exit(1)