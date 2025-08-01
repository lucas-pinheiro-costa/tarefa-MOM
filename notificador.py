"""
Este worker tem uma única e simples tarefa: ouvir a fila de notificações e (simular) o envio de um e-mail.
"""

import pika
import json
import time

RABBITMQ_HOST = 'rabbitmq'
NOTIFICATION_QUEUE = 'notificacoes_queue'

connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()

# Fila de trabalho durável
channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True)
print("✅ [Notificador] Aguardando por mensagens de notificação...")

def callback(ch, method, properties, body):
    dados = json.loads(body)
    print(f"\n📧 [Notificador] Recebida ordem para notificar!")
    print(f"  -> Enviando e-mail de alerta de preço para: {dados['email']}")
    print(f"  -> Voo: {dados['id_voo']} encontrado por R${dados['preco_encontrado']}!")
    
    # Simula o trabalho de enviar o e-mail
    time.sleep(2)
    print("  -> E-mail enviado com sucesso.")
    
    # Confirma que a mensagem foi processada
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=NOTIFICATION_QUEUE, on_message_callback=callback)
channel.start_consuming()