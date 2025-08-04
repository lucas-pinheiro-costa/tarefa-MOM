#!/usr/bin/env python3
"""
Monitor para Dead Letter Queue (DLQ)
Permite visualizar e gerenciar mensagens na DLQ do sistema de arquivamento de preços.
"""

import pika
import json
import os
from datetime import datetime

# Configurações (mesmas do arquivador)
RABBITMQ_HOST = 'rabbitmq'
DEAD_LETTER_EXCHANGE = 'historico_dlx'
DEAD_LETTER_QUEUE = 'historico_dlq'

def connect_rabbitmq():
    """Conecta ao RabbitMQ e retorna channel."""
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
        print(f"📊 Dead Letter Queue contém {message_count} mensagem(s)")
        return message_count
    except Exception as e:
        print(f"❌ Erro ao verificar DLQ: {e}")
        return 0

def consume_dlq_messages(channel, limit=10):
    """Consome e exibe mensagens da DLQ sem removê-las."""
    print(f"🔍 Exibindo até {limit} mensagens da DLQ:")
    
    messages_processed = 0
    
    def callback(ch, method, properties, body):
        nonlocal messages_processed
        try:
            data = json.loads(body)
            print(f"\n📄 Mensagem {messages_processed + 1}:")
            print(f"   - ID Voo: {data.get('id_voo', 'N/A')}")
            print(f"   - Origem: {data.get('origem', 'N/A')}")
            print(f"   - Destino: {data.get('destino', 'N/A')}")
            print(f"   - Preço: {data.get('preco', 'N/A')}")
            print(f"   - Timestamp: {data.get('timestamp', 'N/A')}")
            if 'timestamp' in data:
                try:
                    dt = datetime.fromtimestamp(data['timestamp'])
                    print(f"   - Data/Hora: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    pass
        except json.JSONDecodeError:
            print(f"\n📄 Mensagem {messages_processed + 1} (JSON inválido):")
            print(f"   - Conteúdo bruto: {body.decode('utf-8', errors='replace')}")
        except Exception as e:
            print(f"\n📄 Mensagem {messages_processed + 1} (erro ao processar):")
            print(f"   - Erro: {e}")
            print(f"   - Conteúdo: {body.decode('utf-8', errors='replace')}")
        
        messages_processed += 1
        
        # Rejeita a mensagem mas mantém na fila (requeue=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        if messages_processed >= limit:
            ch.stop_consuming()
    
    try:
        channel.basic_consume(queue=DEAD_LETTER_QUEUE, on_message_callback=callback, auto_ack=False)
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    
    print(f"\n✅ Processadas {messages_processed} mensagens da DLQ")

def purge_dlq(channel):
    """Remove todas as mensagens da DLQ."""
    try:
        result = channel.queue_purge(queue=DEAD_LETTER_QUEUE)
        print(f"🗑️  {result.method.message_count} mensagens removidas da DLQ")
    except Exception as e:
        print(f"❌ Erro ao limpar DLQ: {e}")

def reprocess_dlq_messages(channel, exchange_name='price_update_topic'):
    """Reprocessa mensagens da DLQ enviando-as de volta ao exchange principal."""
    print("🔄 Reprocessando mensagens da DLQ...")
    
    messages_reprocessed = 0
    
    def callback(ch, method, properties, body):
        nonlocal messages_reprocessed
        try:
            # Reenvia a mensagem para o exchange principal
            channel.basic_publish(
                exchange=exchange_name,
                routing_key='',
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Torna a mensagem persistente
                )
            )
            messages_reprocessed += 1
            print(f"   ✅ Mensagem {messages_reprocessed} reenviada")
            
            # Remove a mensagem da DLQ
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"   ❌ Erro ao reprocessar mensagem: {e}")
            # Mantém a mensagem na DLQ em caso de erro
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    try:
        # Declara o exchange principal caso não exista
        channel.exchange_declare(exchange=exchange_name, exchange_type='fanout', durable=True)
        
        # Consome mensagens da DLQ
        channel.basic_consume(queue=DEAD_LETTER_QUEUE, on_message_callback=callback, auto_ack=False)
        channel.start_consuming()
        
    except KeyboardInterrupt:
        channel.stop_consuming()
    
    print(f"\n🔄 {messages_reprocessed} mensagens reprocessadas")

def main():
    """Menu principal do monitor de DLQ."""
    connection, channel = connect_rabbitmq()
    if not channel:
        return
    
    try:
        while True:
            print("\n" + "="*50)
            print("🔍 MONITOR DE DEAD LETTER QUEUE")
            print("="*50)
            print("1. Verificar status da DLQ")
            print("2. Visualizar mensagens (sem remover)")
            print("3. Reprocessar mensagens da DLQ")
            print("4. Limpar DLQ (remover todas as mensagens)")
            print("5. Sair")
            print("="*50)
            
            choice = input("Escolha uma opção (1-5): ").strip()
            
            if choice == '1':
                check_dlq_messages(channel)
            
            elif choice == '2':
                limit = input("Quantas mensagens exibir? (padrão: 10): ").strip()
                try:
                    limit = int(limit) if limit else 10
                except ValueError:
                    limit = 10
                consume_dlq_messages(channel, limit)
            
            elif choice == '3':
                confirm = input("⚠️  Tem certeza que deseja reprocessar todas as mensagens da DLQ? (s/N): ").strip().lower()
                if confirm == 's':
                    reprocess_dlq_messages(channel)
                else:
                    print("❌ Operação cancelada")
            
            elif choice == '4':
                confirm = input("⚠️  Tem certeza que deseja REMOVER todas as mensagens da DLQ? (s/N): ").strip().lower()
                if confirm == 's':
                    purge_dlq(channel)
                else:
                    print("❌ Operação cancelada")
            
            elif choice == '5':
                print("👋 Saindo...")
                break
            
            else:
                print("❌ Opção inválida")
    
    except KeyboardInterrupt:
        print("\n👋 Monitor interrompido")
    
    finally:
        if connection and not connection.is_closed:
            connection.close()

if __name__ == '__main__':
    main()
