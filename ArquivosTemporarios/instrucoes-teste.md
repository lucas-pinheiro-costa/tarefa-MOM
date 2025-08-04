# Siga esses passos

Prepare os Terminais: Deixe três terminais prontos no seu ambiente VS Code.

Execute a Simulação:

Terminal 1: Inicie seu produtor aprimorado: python produtor_de_precos.py

Terminal 2: Inicie seu arquivador aprimorado: python arquivador_historico.py

Observe: Deixe os scripts rodarem. Observe como o produtor agora informa sobre o status da DLQ periodicamente e como o arquivador rejeita a mensagem malformada. Depois de ver algumas mensagens falharem, pare os dois scripts (Ctrl+C).

Use sua Ferramenta de Monitoramento:

Terminal 3: Inicie seu monitor: python dlq_monitor.py

Siga os passos de teste que descrevemos anteriormente:

Opção 1: Verifique o status.

Opção 2: Visualize a mensagem para confirmar a causa do erro.

Simule a correção (comentando a validação no arquivador_historico.py).

Reinicie o arquivador "corrigido" no Terminal 2.

Opção 3: Reprocesse a mensagem a partir do monitor e veja o arquivador processá-la com sucesso.