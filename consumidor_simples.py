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

# --- Configurações ---
RABBITMQ_HOST = 'localhost'
EXCHANGE_NAME = 'price_update_topic'

# --- Conexão com RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()

# --- Declaração da Exchange (boa prática declarar em ambos os lados) ---
channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')

# --- Declaração da Fila ---
# Declara uma fila com um nome exclusivo gerado pelo RabbitMQ.
# exclusive=True significa que a fila será deletada quando a conexão for fechada.
# Isso é perfeito para consumidores de um tópico, pois cada um tem sua própria "cópia" da mensagem.
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

# --- Binding (Ligação) ---
# Liga a nossa fila à exchange. Agora, todas as mensagens publicadas na exchange
# 'price_update_topic' serão enviadas para a nossa fila.
channel.queue_bind(exchange=EXCHANGE_NAME, queue=queue_name)

print("✅ Consumidor conectado. Aguardando preços...")

# --- Função de Callback ---
def callback(ch, method, properties, body):
    """Função executada quando uma mensagem é recebida."""
    dados_do_preco = json.loads(body)
    print(f" [📥] Preço recebido: {dados_do_preco}")
    # Por enquanto, só imprimimos. No futuro, aqui entrará a lógica de negócio.
    
# --- Inicia o Consumo ---
channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=True # Acknowledge automático por simplicidade neste passo
)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("\n🛑 Consumidor interrompido.")
    connection.close()