# 🛫 Sistema de precificação dinâmica e alertas de viagens

Um sistema distribuído construído com **Middleware Orientado a Mensagens (MOM)** que simula a descoberta, processamento e armazenamento de preços de voos em tempo real.

## 📋 Sobre o projeto

Este projeto demonstra a implementação de um pipeline de dados assíncrono e escalável, utilizando **RabbitMQ** como middleware de mensageria para desacoplar os componentes do sistema. O sistema coleta, processa, armazena e expõe informações de preços de voos de forma contínua e confiável.

## 🏗️ Arquitetura do sistema

O sistema é composto por **5 pilares principais**:

### 1. 🐳 A fundação: ambiente de desenvolvimento (Dev Container)
- **O que é**: Ambiente de desenvolvimento isolado e consistente usando Docker e Docker Compose
- **O que faz**: Configura automaticamente toda a infraestrutura necessária (Python, RabbitMQ, PostgreSQL) com um único comando

### 2. 🏭 O ponto de partida: produtor de dados
- **Arquivo**: `produtor_de_precos.py`
- **O que faz**: Simula um robô que descobre novos preços de voos a cada poucos segundos, funcionando como a fonte primária de informações do sistema

### 3. 🐰 O coração da comunicação: RabbitMQ
- **O que é**: Middleware Orientado a Mensagens (MOM)
- **O que faz**: Atua como um "carteiro" central, recebendo mensagens do produtor e distribuindo-as para todos os consumidores interessados através do tópico `price_update_topic`

### 4. 💾 A memória do sistema: arquivador e PostgreSQL
- **Arquivo**: `arquivador_historico.py`
- **O que faz**: 
  - Assina o tópico de preços no RabbitMQ
  - Captura mensagens de novos preços
  - Conecta ao PostgreSQL e salva permanentemente na tabela `historico_precos`

### 5. 🌐 A vitrine para o mundo: API Gateway
- **Arquivo**: `api_gateway.py` 
- **O que faz**: Expõe uma API REST (FastAPI) que permite consultar os preços mais recentes através do endpoint `http://localhost:5000/api/v1/voos/recentes`

## 🔄 Fluxo de dados

```
[Produtor] → publica no → [RabbitMQ] → entrega para → [Arquivador] → salva no → [PostgreSQL]
                                ↓
[Usuário] → acessa a → [API Gateway] → lê do → [PostgreSQL]
```

## 🚀 Como executar o sistema

### Pré-requisitos
- Docker e Docker Compose instalados
- VS Code com extensão Dev Containers (recomendado)

### Passos para execução

1. **Clone o repositório**:
   ```bash
   git clone https://www.github.com/lucas-pinheiro-costa/tarefa-MOM.git
   cd tarefa-MOM
   ```

2. **Inicie o ambiente com Dev Container**:
   - Abra o projeto no VS Code
   - Aceite abrir no Dev Container quando solicitado
   - Ou use: `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute os componentes do sistema**:

   **Terminal 1 - Inicie o Produtor**:
   ```bash
   python produtor_de_precos.py
   ```

   **Terminal 2 - Inicie o Arquivador**:
   ```bash
   python arquivador_historico.py
   ```

   **Terminal 3 - Inicie a API Gateway**:
   ```bash
   python api_gateway.py
   ```

## 🧪 Como testar o sistema

### 1. Verificar se o Produtor está funcionando
- Observe no terminal do produtor as mensagens: `[✈️] Preço enviado: {...}`
- Os preços devem ser gerados automaticamente a cada 1-5 segundos

### 2. Verificar se o Arquivador está consumindo
- Observe no terminal do arquivador as mensagens sendo processadas
- Verifique se os dados estão sendo salvos no PostgreSQL

### 3. Testar a API Gateway
- Acesse no navegador: `http://localhost:5000/api/v1/voos/recentes`
- Ou use curl:
  ```bash
  curl http://localhost:5000/api/v1/voos/recentes
  ```
- Você deve ver um JSON com os preços mais recentes

### 4. Verificar a Conexão com RabbitMQ
- Execute o teste de conexão:
  ```bash
  python ArquivosTemporarios/teste_conexao_rabbitmq.py
  ```

## 🛠️ Tecnologias Utilizadas

- **Python 3**: Linguagem principal
- **RabbitMQ**: Middleware de mensageria
- **PostgreSQL**: Banco de dados relacional
- **FastAPI**: Framework para API REST
- **Pika**: Cliente Python para RabbitMQ
- **Docker & Docker Compose**: Containerização
- **VS Code Dev Containers**: Ambiente de desenvolvimento

## 📂 Estrutura do Projeto

```
tarefa-MOM/
├── produtor_de_precos.py          # Produtor de dados de preços
├── arquivador_historico.py        # Consumidor que armazena no BD
├── api_gateway.py                  # API REST para consultas
├── consumidor_simples.py           # Consumidor básico para testes
├── requirements.txt                # Dependências Python
├── README.md                      # Este arquivo
└── ArquivosTemporarios/
    └── teste_conexao_rabbitmq.py  # Teste de conectividade
```

## 🎯 Objetivos de Aprendizado

Este projeto demonstra:
- ✅ Implementação de arquitetura orientada a mensagens
- ✅ Desacoplamento de componentes usando RabbitMQ
- ✅ Pipeline de dados assíncrono e escalável
- ✅ Integração entre múltiplas tecnologias
- ✅ Containerização com Docker
- ✅ APIs REST com FastAPI
- ✅ Persistência de dados com PostgreSQL
