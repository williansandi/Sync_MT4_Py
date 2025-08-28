
# Prompt para Análise de Código do Projeto SyncMT4 V3.1 com Gemini

**Contexto:** Você é um assistente de programação sênior. Abaixo está a descrição completa de um projeto de software. Seu objetivo é entender profundamente a arquitetura, as tecnologias e o fluxo de dados para responder a perguntas específicas sobre o código, sugerir melhorias, refatorar, ou adicionar novas funcionalidades de forma coesa e assertiva.

---

## 1. Visão Geral do Projeto

O **SyncMT4 V3.1** é uma aplicação de desktop desenvolvida em Python que funciona como um bot de trading para a plataforma IQ Option. Seu principal diferencial é a capacidade de sincronizar com a plataforma MetaTrader 4 (MT4). A aplicação permite que os usuários executem estratégias de trading automatizadas baseadas em sinais gerados por Expert Advisors (EAs) no MT4, além de outras estratégias pré-definidas (MHI, Lista de Sinais).

A aplicação possui uma interface gráfica (GUI) para que o usuário possa fazer login na IQ Option, gerenciar configurações, selecionar a estratégia, iniciar/parar o bot e acompanhar o desempenho financeiro em um dashboard.

## 2. Tecnologias Utilizadas

- **Linguagem Principal:** Python 3.10
- **Interface Gráfica (UI):** Provavelmente CustomTkinter ou uma biblioteca similar, construída sobre o Tkinter.
- **Comunicação Inter-Processos (IPC):** ZeroMQ (via `mql-zmq-master`) para a comunicação em tempo real entre o Expert Advisor no MT4 e o bot em Python.
- **Integração com MT4:** Uma DLL (`AlertSpy.dll`) escrita em C++ que "espia" os alertas do MT4 e os envia para o bot Python através do ZeroMQ.
- **API da Corretora:** Uma biblioteca Python (`iqoptionapi`) para se comunicar com a API da IQ Option (realizar login, obter dados de mercado, executar ordens, etc.).
- **Banco de Dados:** SQLite (`config.db`) para armazenar configurações persistentes.
- **Logging:** Arquivos de log de texto (`historico_operacoes.log`, `bot_activity.log`) para registrar atividades.

## 3. Diagrama de Arquitetura e Fluxo de Dados

O diagrama abaixo ilustra a interação entre os componentes do sistema.

```mermaid
graph TD
    subgraph "Usuário"
        U[Usuário]
    end

    subgraph "Aplicação Python (SyncMT4)"
        subgraph "Interface Gráfica (UI)"
            UI_Main[ui/app.py]
            UI_Login[ui/login_frame.py]
            UI_Dashboard[ui/dashboard_frame.py]
            UI_Settings[ui/settings_frame.py]
        end

        subgraph "Core do Bot"
            BotCore[bot/bot_core.py]
            StrategyMT4[bot/strategies/mt4_strategy.py]
            StrategyMHI[bot/strategies/mhi_strategy.py]
            Management[bot/management/*]
        end

        subgraph "Comunicação e Utilitários"
            IQ_API[iqoptionapi]
            ZMQ_Listener[ZeroMQ Subscriber]
            Logger[utils/logger.py]
            Config[utils/config_manager.py]
            DB[config.db]
        end
    end

    subgraph "MetaTrader 4 (Plataforma Externa)"
        MT4_EA[Expert Advisor (EA)]
        AlertSpy[Lib/AlertSpy.dll]
        ZMQ_Publisher[ZeroMQ Publisher]
    end

    subgraph "IQ Option (Plataforma Externa)"
        IQ_Platform[Servidores IQ Option]
    end

    %% Fluxo de Interação
    U -- Interage com --> UI_Main
    UI_Main -- Gerencia --> UI_Login & UI_Dashboard & UI_Settings

    UI_Dashboard -- Inicia/Para Bot --> BotCore
    BotCore -- Executa --> StrategyMT4
    BotCore -- Usa --> Management
    BotCore -- Loga em --> Logger
    BotCore -- Lê/Grava --> Config -- Acessa --> DB

    StrategyMT4 -- Escuta --> ZMQ_Listener
    BotCore -- Envia Ordens via --> IQ_API
    IQ_API -- Comunica com --> IQ_Platform

    %% Fluxo de Sinal do MT4
    MT4_EA -- Gera Alerta --> AlertSpy
    AlertSpy -- Captura e Publica via --> ZMQ_Publisher
    ZMQ_Publisher -- Envia Sinal --> ZMQ_Listener
```

## 4. Fluxo de Operação (Estratégia MT4)

1.  **Inicialização:** O usuário executa `main.py`, que inicia a aplicação de UI (`ui/app.py`).
2.  **Login:** A `login_frame.py` é exibida. O usuário insere suas credenciais da IQ Option. A aplicação usa a `iqoptionapi` para autenticar o usuário.
3.  **Dashboard:** Após o login, a `dashboard_frame.py` é exibida, mostrando informações da conta.
4.  **Configuração:** O usuário navega para as configurações (`settings_frame.py`), seleciona a estratégia "MT4" e define parâmetros como valor de entrada, stop loss, etc. As configurações são salvas via `config_manager.py` no `config.db`.
5.  **Início do Bot:** O usuário inicia o bot a partir do dashboard.
6.  **Ativação da Estratégia:** O `bot_core.py` é instanciado e carrega a `mt4_strategy.py`.
7.  **Escuta de Sinais:** A `mt4_strategy.py` inicializa um *subscriber* ZeroMQ que fica escutando por mensagens em uma porta TCP específica (ex: `tcp://localhost:5555`).
8.  **Geração do Sinal no MT4:** Em uma instância separada do MetaTrader 4, um Expert Advisor (EA) está rodando. Quando as condições de mercado para uma operação são atendidas, o EA gera um alerta no MT4.
9.  **Captura e Envio do Sinal:** A DLL `AlertSpy.dll`, previamente injetada no MT4, intercepta este alerta. A DLL então usa sua lógica de *publisher* ZeroMQ para enviar uma mensagem contendo os detalhes do sinal (par, direção, etc.) para o mesmo endereço TCP que o bot Python está escutando.
10. **Recebimento e Processamento do Sinal:** O bot Python recebe a mensagem ZeroMQ. A `mt4_strategy.py` decodifica a mensagem e a valida.
11. **Execução da Ordem:** Se o sinal for válido, o `bot_core.py` utiliza a `iqoptionapi` para executar a operação de compra ou venda na plataforma IQ Option.
12. **Feedback e Logging:** O resultado da operação é logado no `historico_operacoes.log` e a interface do usuário é atualizada com o novo status financeiro.

## 5. Estrutura de Diretórios e Arquivos

-   `main.py`: Ponto de entrada da aplicação. Inicia a interface gráfica.
-   `requirements.txt`: Lista de dependências Python do projeto.
-   `config.db`: Banco de dados SQLite para configurações.
-   `historico_operacoes.log`: Arquivo de log com o histórico de todas as operações realizadas.
-   `mt4_pares.txt`: Provavelmente uma lista de pares de moedas a serem considerados na estratégia MT4.
-   `/ui/`: Contém todos os arquivos relacionados à interface gráfica.
    -   `app.py`: O arquivo principal da UI, que cria a janela e gerencia os frames.
    -   `*_frame.py`: Cada arquivo define uma tela ou seção da UI (Login, Dashboard, Configurações, etc.).
    -   `/components/`: Widgets reutilizáveis da UI (cartões de métricas, histórico, etc.).
-   `/bot/`: Contém a lógica de negócio do bot.
    -   `bot_core.py`: O cérebro do bot. Gerencia o estado (rodando/parado), o capital, e executa a estratégia selecionada.
    -   `/strategies/`: Módulos de estratégias de trading. Cada arquivo implementa uma lógica diferente.
        -   `mt4_strategy.py`: Implementa a lógica para operar com base nos sinais do MT4 via ZeroMQ.
    -   `/management/`: Módulos para gerenciamento de risco e ciclos de trading (Martingale, Soros, etc.).
        -   `cycle_manager.py`: Gerencia ciclos de Martingale.
        -   `masaniello_manager.py`: Implementa a gestão de banca Masaniello.
-   `/iqoptionapi/`: Biblioteca de terceiros para interagir com a API da IQ Option.
-   `/Lib/`: Bibliotecas externas e código que não é Python.
    -   `AlertSpy.dll`: A biblioteca C++ compilada que é injetada no MT4.
    -   `/AlertSpy.cpp/`: O código-fonte da `AlertSpy.dll`.
    -   `/mql-zmq-master/`: Código de exemplo e includes para usar ZeroMQ com a linguagem MQL4/5 do MetaTrader.
-   `/utils/`: Módulos de utilidade.
    -   `config_manager.py`: Classe para ler e escrever no `config.db`.
    -   `logger.py`: Classe para configurar e gerenciar os logs da aplicação.

---

## 6. Minha Pergunta

**[ADICIONE SUA PERGUNTA ESPECÍFICA AQUI]**

*Exemplo 1: "Analise o arquivo `bot/management/cycle_manager.py` e sugira uma refatoração para tornar o controle de ciclos mais robusto e fácil de testar."*
*Exemplo 2: "Quero adicionar uma nova estratégia baseada em notícias econômicas. Quais arquivos eu precisaria criar e modificar? Forneça um esqueleto do código para a nova classe de estratégia."*
*Exemplo 3: "O `bot_core.py` parece muito complexo. Explique a sua principal responsabilidade e como ele interage com as estratégias. Há alguma forma de simplificá-lo?"*

