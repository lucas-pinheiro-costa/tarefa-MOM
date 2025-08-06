# 🛫 Sistema de precificação dinâmica e alertas de viagens

Um sistema distribuído construído com **Middleware Orientado a Mensagens (MOM)** que simula a descoberta, processamento e armazenamento de preços de voos em tempo real, incluindo sistema de alertas automatizados e tratamento de falhas com Dead Letter Queue (DLQ).

## 📋 Sobre o projeto

Este projeto demonstra a implementação de um pipeline de dados assíncrono e escalável, utilizando **RabbitMQ** como middleware de mensageria para desacoplar os componentes do sistema. O sistema coleta, processa, armazena, expõe informações de preços de voos e gerencia alertas de preços de forma contínua e confiável, com tratamento robusto de falhas.

## 🏗️ Arquitetura do sistema

O sistema é composto por **7 componentes principais**:

### 1. 🐳 A fundação: ambiente de desenvolvimento (Dev Container)
- **O que é**: Ambiente de desenvolvimento isolado e consistente usando Docker e Docker Compose
- **O que faz**: Configura automaticamente toda a infraestrutura necessária (Python, RabbitMQ, PostgreSQL) com um único comando

### 2. 🏭 O ponto de partida: produtor de dados
- **Arquivo**: `produtor_de_precos.py`
- **O que faz**: Simula um robô que descobre novos preços de voos a cada poucos segundos, funcionando como a fonte primária de informações do sistema. Além disso, testa automaticamente a DLQ e gera mensagens malformadas propositalmente para demonstração

### 3. 🐰 O coração da comunicação: RabbitMQ
- **O que é**: Middleware Orientado a Mensagens (MOM)
- **O que faz**: Atua como um "carteiro" central, recebendo mensagens do produtor e distribuindo-as para todos os consumidores interessados através do tópico `price_update_topic`
- **Infraestrutura DLQ**: Configurado com Dead Letter Exchange e Dead Letter Queue para tratamento de falhas

### 4. 💾 A memória do sistema: arquivador e PostgreSQL
- **Arquivo**: `arquivador_historico.py`
- **O que faz**: 
  - Assina o tópico de preços no RabbitMQ
  - Valida mensagens recebidas
  - Conecta ao PostgreSQL e salva permanentemente na tabela `historico_precos`
  - Envia mensagens problemáticas para a DLQ com tratamento robusto de erros

### 5. 🧠 O motor inteligente: motor de alertas
- **Arquivo**: `motor_de_alertas.py`
- **O que faz**:
  - Monitora todos os preços publicados no tópico
  - Verifica alertas ativos no banco de dados
  - Dispara notificações quando preços desejados são encontrados
  - Atualiza status dos alertas para evitar duplicação

### 6. 📧 O notificador: sistema de notificações
- **Arquivo**: `notificador.py`
- **O que faz**:
  - Processa fila dedicada de notificações
  - Simula envio de e-mails para usuários
  - Confirma processamento das notificações

### 7. 🌐 A vitrine para o mundo: API Gateway
- **Arquivo**: `api_gateway.py` 
- **O que faz**: 
  - Expõe API REST para consultar preços: `GET /api/v1/voos/recentes`
  - Permite criação de alertas: `POST /api/v1/alertas`
  - Interface de documentação automática em `/docs`

### 8. � Monitor de DLQ: ferramenta de diagnóstico
- **Arquivo**: `dlq_monitor.py`
- **O que faz**:
  - Monitora mensagens na Dead Letter Queue
  - Permite visualizar, reprocessar ou limpar mensagens problemáticas
  - Interface interativa para gerenciamento de falhas

## �🔄 Fluxo completo de dados

```
                                   ┌─ [Motor de Alertas] ─→ [Fila de Notificações] ─→ [Notificador]
                                   │                                                        │
[Produtor] ─→ [RabbitMQ] ─┬─ [Arquivador] ─→ [PostgreSQL] ←─ [API Gateway] ←─ [Usuário]   │
                          │        │                                                       │
                          │        └─ Mensagens problemáticas ─→ [DLQ] ←─ [Monitor DLQ] ←─┘
                          │
                          └─ [Outros Consumidores...]
```

### Fluxo de um preço:
1. **Produtor** gera e publica preço no tópico RabbitMQ
2. **Arquivador** consome, valida e salva no PostgreSQL
3. **Motor de Alertas** verifica se há alertas para esse preço
4. Se houver match, publica na **Fila de Notificações**
5. **Notificador** processa e "envia" e-mail ao usuário
6. **API Gateway** expõe dados para consulta externa

### Fluxo de falhas:
1. Mensagem malformada chega no **Arquivador**
2. Validação falha, mensagem é rejeitada sem requeue
3. RabbitMQ envia automaticamente para a **DLQ**
4. **Monitor DLQ** permite análise e reprocessamento

## 🚀 Como executar o sistema

### Pré-requisitos
- Docker e Docker Compose instalados
- VS Code com extensão Dev Containers (recomendado)

### Configuração inicial

1. **Clone o repositório**:
   ```bash
   git clone https://www.github.com/lucas-pinheiro-costa/tarefa-MOM.git
   cd tarefa-MOM
   ```

2. **Configure o arquivo .env** (crie na raiz do projeto):
   ```bash
   # PostgreSQL
   DB_HOST=postgres
   DB_PORT=5432
   DB_NAME=precos_viagens
   DB_USER=postgres
   DB_PASSWORD=postgres
   
   # RabbitMQ
   RABBITMQ_HOST=rabbitmq
   ```

3. **Inicie o ambiente com Dev Container**:
   - Abra o projeto no VS Code
   - Aceite abrir no Dev Container quando solicitado
   - Ou use: `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"

4. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure o banco de dados** (execute no PostgreSQL):
   ```sql
   -- Criar banco
   CREATE DATABASE precos_viagens;
   
   -- Usar o banco
   \c precos_viagens;
   
   -- Tabela de histórico de preços
   CREATE TABLE historico_precos (
       id SERIAL PRIMARY KEY,
       id_voo VARCHAR(20) NOT NULL,
       origem VARCHAR(10) NOT NULL,
       destino VARCHAR(10) NOT NULL,
       preco DECIMAL(10,2) NOT NULL,
       timestamp_captura TIMESTAMP NOT NULL,
       data_insercao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   
   -- Tabela de alertas
   CREATE TABLE alertas (
       id SERIAL PRIMARY KEY,
       email_usuario VARCHAR(255) NOT NULL,
       id_voo VARCHAR(20) NOT NULL,
       origem VARCHAR(10) NOT NULL,
       destino VARCHAR(10) NOT NULL,
       preco_desejado DECIMAL(10,2) NOT NULL,
       status VARCHAR(20) DEFAULT 'ativo',
       data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

### Execução do sistema completo

Execute cada componente em um terminal separado:

**Terminal 1 - Produtor de Preços**:
```bash
python produtor_de_precos.py
```

**Terminal 2 - Arquivador de Histórico**:
```bash
python arquivador_historico.py
```

**Terminal 3 - Motor de Alertas**:
```bash
python motor_de_alertas.py
```

**Terminal 4 - Notificador**:
```bash
python notificador.py
```

**Terminal 5 - API Gateway**:
```bash
uvicorn api_gateway:app --host 0.0.0.0 --port 5000 --reload
```

## 🎯 Demonstrações do Sistema

### 🔄 Demonstração 1: O ciclo de vida de um preço

Esta demonstração mostra como um preço de voo é capturado, processado, armazenado e gera alertas.

#### Pré-requisitos:
- Sistema básico funcionando (Terminais 1, 2, 3, 4 e 5)
- API Gateway acessível em `http://localhost:5000`

#### Passos:

1. **Criar um alerta via API**:
   ```bash
   curl -X POST "http://localhost:5000/api/v1/alertas" \
        -H "Content-Type: application/json" \
        -d '{
          "email_usuario": "usuario@exemplo.com",
          "id_voo": "G31420",
          "origem": "NAT",
          "destino": "GRU",
          "preco_desejado": 2000.00
        }'
   ```

2. **Observar os terminais**:
   - **Terminal 1 (Produtor)**: Verá preços sendo gerados
   - **Terminal 2 (Arquivador)**: Verá preços sendo salvos no BD
   - **Terminal 3 (Motor de Alertas)**: Verá verificação de alertas
   - **Terminal 4 (Notificador)**: Verá notificação sendo enviada quando preço for ≤ R$2000

3. **Verificar dados via API**:
   ```bash
   curl http://localhost:5000/api/v1/voos/recentes
   ```

4. **Resultado esperado**:
   - Preço capturado → Salvo no BD → Alerta verificado → Notificação enviada
   - Status do alerta mudou para "disparado"

---

### 🚨 Demonstração 2: Tratando falhas com DLQ (Dead Letter Queue)

Esta demonstração mostra como o sistema lida com mensagens problemáticas.

#### Pré-requisitos:
- Terminais 1 e 2 rodando (Produtor e Arquivador)

#### Passos:

1. **Observar mensagens malformadas**:
   - O produtor automaticamente envia mensagens malformadas a cada 5 mensagens
   - No **Terminal 1**, procure por: `[☠️] Enviando mensagem malformada (teste DLQ)`
   - No **Terminal 2**, procure por: `❌ Erro ao processar mensagem` e `Rejeitando mensagem e enviando para a DLQ`

2. **Monitorar a DLQ**:
   ```bash
   # Em um novo terminal
   python dlq_monitor.py
   ```

3. **No monitor, escolher opções**:
   - **Opção 1**: Verificar quantas mensagens estão na DLQ
   - **Opção 2**: Visualizar conteúdo das mensagens problemáticas
   - Observe campos ausentes como `preco`

4. **Resultado esperado**:
   - Mensagens malformadas são automaticamente isoladas na DLQ
   - Sistema principal continua funcionando normalmente
   - Mensagens problemáticas ficam disponíveis para análise

---

### 🔧 Demonstração 3: Fechando o ciclo de recuperação

Esta demonstração mostra como recuperar mensagens da DLQ após correção de problemas.

#### Pré-requisitos:
- DLQ com mensagens (da Demonstração 2)
- Monitor DLQ aberto

#### Cenário de "correção":

1. **Simular correção no arquivador** (comentar validação temporariamente):
   - Pare o arquivador (Ctrl+C no Terminal 2)
   - Edite `arquivador_historico.py` e comente a linha de validação:
   ```python
   # validate_message_data(dados_do_preco)  # TEMPORÁRIO: para demonstração
   ```
   - Reinicie o arquivador

2. **Reprocessar mensagens da DLQ**:
   - No monitor DLQ, escolha **Opção 3**: "Reprocessar mensagens da DLQ"
   - Confirme com 's'

3. **Observar os terminais**:
   - **Terminal 2**: Verá mensagens sendo reprocessadas e salvas
   - **Monitor DLQ**: Mostrará quantas mensagens foram reprocessadas

4. **Verificar DLQ vazia**:
   - No monitor, escolha **Opção 1** para confirmar que DLQ está vazia

5. **Restaurar validação**:
   - Pare o arquivador
   - Descomente a linha de validação
   - Reinicie o arquivador

#### Resultado esperado:
- Mensagens "problemáticas" foram recuperadas e processadas
- Ciclo completo de tratamento de falhas demonstrado
- Sistema voltou ao estado normal com validações ativas

## 🧪 Testes adicionais do sistema

### 1. Teste de conectividade RabbitMQ
```bash
python ArquivosTemporarios/teste_conexao_rabbitmq.py
```

### 2. Teste da API Gateway
- **Interface interativa**: `http://localhost:5000/docs`
- **Consultar preços**: `http://localhost:5000/api/v1/voos/recentes`
- **Criar alerta via curl**:
  ```bash
  curl -X POST "http://localhost:5000/api/v1/alertas" \
       -H "Content-Type: application/json" \
       -d '{"email_usuario": "test@example.com", "id_voo": "G31420", "origem": "NAT", "destino": "GRU", "preco_desejado": 1500.00}'
  ```

### 3. Monitoramento do RabbitMQ
- **Interface web**: `http://localhost:15672`
- **Usuário**: `guest` / **Senha**: `guest`
- Visualize exchanges, filas e mensagens em tempo real

### 4. Ferramentas de diagnóstico
- **Monitor DLQ**: `python dlq_monitor.py`
- **Logs dos componentes**: Cada terminal mostra logs detalhados
- **Status das filas**: Verificação automática no produtor a cada 10 mensagens

- **Python 3**: Linguagem principal
- **RabbitMQ**: Middleware de mensageria
- **PostgreSQL**: Banco de dados relacional
- **FastAPI**: Framework para API REST
- **Pika**: Cliente Python para RabbitMQ
- **Docker & Docker Compose**: Containerização
- **VS Code Dev Containers**: Ambiente de desenvolvimento

## �️ Tecnologias Utilizadas

- **Python 3.11**: Linguagem principal
- **RabbitMQ**: Middleware de mensageria com DLQ
- **PostgreSQL**: Banco de dados relacional
- **FastAPI**: Framework para API REST com documentação automática
- **Pika**: Cliente Python para RabbitMQ
- **Psycopg2**: Driver PostgreSQL para Python
- **Uvicorn**: Servidor ASGI para FastAPI
- **Docker & Docker Compose**: Containerização
- **VS Code Dev Containers**: Ambiente de desenvolvimento

## �📂 Estrutura do Projeto

```
tarefa-MOM/
├── 🏭 Componentes principais
│   ├── produtor_de_precos.py          # Produtor de dados com DLQ monitoring
│   ├── arquivador_historico.py        # Consumidor com validação e DLQ
│   ├── motor_de_alertas.py            # Processador de alertas
│   ├── notificador.py                 # Sistema de notificações
│   └── api_gateway.py                 # API REST para consultas e alertas
├── 🔧 Ferramentas de diagnóstico
│   └── dlq_monitor.py                 # Monitor interativo da DLQ
├── 📦 Configuração
│   ├── requirements.txt               # Dependências Python
│   ├── .env                          # Variáveis de ambiente (criar)
│   └── .devcontainer/                # Configuração Dev Container
├── 📄 Documentação
│   ├── README.md                     # Este arquivo
│
│
│
│
│
└── 🗃️ Dados
    └── __pycache__/                  # Cache Python (ignorado pelo git)
```

## 🎯 Objetivos de Aprendizado

Este projeto demonstra:

### 📡 Middleware Orientado a Mensagens (MOM)
- ✅ Implementação de arquitetura orientada a mensagens
- ✅ Desacoplamento de componentes usando RabbitMQ
- ✅ Padrões pub/sub e point-to-point
- ✅ Exchanges, filas e roteamento de mensagens

### 🛡️ Tratamento de Falhas e Confiabilidade
- ✅ Dead Letter Queue (DLQ) para mensagens problemáticas
- ✅ Validação robusta de dados
- ✅ Recovery e reprocessamento de mensagens
- ✅ Acknowledgments manuais para controle de fluxo

### 🏗️ Arquitetura de Microsserviços
- ✅ Pipeline de dados assíncrono e escalável
- ✅ Separação de responsabilidades
- ✅ Sistema de alertas baseado em eventos
- ✅ Monitoramento e observabilidade

### 🔧 Integração Tecnológica
- ✅ Containerização com Docker e Dev Containers
- ✅ APIs REST com FastAPI e documentação automática
- ✅ Persistência de dados com PostgreSQL
- ✅ Desenvolvimento em ambiente isolado

### 📊 Padrões de Processamento
- ✅ Event-driven architecture
- ✅ Message validation e error handling
- ✅ Workflow de notificações
- ✅ Monitoramento de sistema distribuído

---

## 💡 Dicas importantes

- **Ordem de execução**: Sempre inicie o ambiente Dev Container primeiro
- **Logs detalhados**: Cada componente fornece logs coloridos e informativos
- **Interface web RabbitMQ**: Use `http://localhost:15672` para monitoramento visual
- **Documentação API**: Acesse `http://localhost:5000/docs` para interface interativa
- **DLQ Monitoring**: Use o monitor sempre que houver problemas
- **Desenvolvimento**: O sistema suporta hot-reload para facilitar mudanças
