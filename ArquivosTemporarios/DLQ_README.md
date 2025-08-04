# Dead Letter Queue (DLQ) - Documentação

## Visão Geral

A Dead Letter Queue (DLQ) foi implementada no sistema de arquivamento de preços para garantir que mensagens problemáticas não sejam perdidas e possam ser analisadas posteriormente.

## Como Funciona

### 1. Configuração Automática
- **Exchange DLX**: `historico_dlx` (fanout, durável)
- **Fila DLQ**: `historico_dlq` (durável)
- **Fila Principal**: `historico_queue` (durável, com DLQ configurada)

### 2. Cenários que Enviam Mensagens para DLQ

#### Mensagens Malformadas:
- JSON inválido
- Campos obrigatórios ausentes (`id_voo`, `origem`, `destino`, `preco`, `timestamp`)
- Tipos de dados incorretos (preço não numérico, timestamp inválido)

#### Erros de Banco de Dados:
- Falhas de conexão com PostgreSQL
- Violações de constraint
- Erros de SQL

#### TTL Expirado:
- Mensagens que ficaram mais de 1 hora na fila principal

### 3. Validações Implementadas

```python
# Campos obrigatórios
required_fields = ['id_voo', 'origem', 'destino', 'preco', 'timestamp']

# Validações de tipo
- preco: deve ser número positivo
- timestamp: deve ser número (UNIX timestamp)
```

## Monitoramento da DLQ

### Script de Monitoramento

Execute o monitor da DLQ:

```bash
python dlq_monitor.py
```

### Funcionalidades do Monitor:

1. **Verificar Status**: Conta quantas mensagens estão na DLQ
2. **Visualizar Mensagens**: Mostra conteúdo sem remover
3. **Reprocessar Mensagens**: Reenvia mensagens para processamento
4. **Limpar DLQ**: Remove todas as mensagens (cuidado!)

## Configurações

### Variáveis de Ambiente Necessárias:

```bash
# RabbitMQ
RABBITMQ_HOST=rabbitmq

# PostgreSQL
DB_HOST=postgres
DB_PORT=5432
DB_NAME=flight_prices
DB_USER=postgres
DB_PASSWORD=sua_senha
```

### Configurações de DLQ (arquivador_historico.py):

```python
# Nomes para DLQ
DEAD_LETTER_EXCHANGE = 'historico_dlx'
DEAD_LETTER_QUEUE = 'historico_dlq'

# TTL da fila principal (1 hora)
"x-message-ttl": 3600000
```

## Boas Práticas

### 1. Monitoramento Regular
- Verifique a DLQ regularmente
- Analise padrões de mensagens problemáticas
- Configure alertas para DLQ com muitas mensagens

### 2. Análise de Mensagens
- Investigue causas raiz dos erros
- Corrija problemas no produtor se necessário
- Ajuste validações se apropriado

### 3. Reprocessamento
- Teste correções antes de reprocessar
- Reprocesse em lotes pequenos
- Monitore durante reprocessamento

### 4. Limpeza
- Remova mensagens irreparáveis após análise
- Mantenha logs das mensagens removidas
- Documente padrões de erro

## Logs e Debugging

### Logs do Arquivador:
```
✅ [Arquivador] Pronto com DLQ configurada
⚠️  Dead Letter Queue contém 5 mensagem(s) para análise
❌ Erro ao processar mensagem: Mensagem malformada: campos ausentes: ['preco']
   -> Rejeitando mensagem e enviando para a DLQ
```

### Logs do Monitor:
```
📊 Dead Letter Queue contém 3 mensagem(s)
🔄 Reprocessando mensagens da DLQ...
   ✅ Mensagem 1 reenviada
🔄 3 mensagens reprocessadas
```

## Troubleshooting

### Problema: Muitas mensagens na DLQ
**Causa**: Problemas no produtor ou esquema de dados
**Solução**: Analisar mensagens, corrigir produtor

### Problema: Mensagens não chegam na DLQ
**Causa**: Configuração incorreta ou auto_ack=True
**Solução**: Verificar configuração de DLX e usar auto_ack=False

### Problema: Perda de performance
**Causa**: DLQ muito cheia ou processamento lento
**Solução**: Limpar DLQ regularmente, otimizar validações

## Exemplo de Uso

### 1. Executar o Arquivador:
```bash
python arquivador_historico.py
```

### 2. Monitorar DLQ:
```bash
python dlq_monitor.py
# Escolha opção 1 para verificar status
```

### 3. Reprocessar se necessário:
```bash
python dlq_monitor.py
# Escolha opção 3 para reprocessar mensagens
```

## Estrutura de Mensagem Esperada

```json
{
    "id_voo": "TAM123",
    "origem": "GRU",
    "destino": "CGH",
    "preco": 299.99,
    "timestamp": 1693891200
}
```

## Melhorias Futuras

1. **Alertas Automáticos**: Notificações quando DLQ atinge limite
2. **Dashboard**: Interface web para monitoramento
3. **Métricas**: Integração com Prometheus/Grafana
4. **Retry Policy**: Tentativas automáticas com backoff
5. **Classificação de Erros**: Diferentes estratégias por tipo de erro
