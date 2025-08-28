# SyncMT4 V3

[![Status do Projeto](https://img.shields.io/badge/status-em%20desenvolvimento-yellowgreen.svg)](https://shields.io/)
[![Licença](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)

Uma breve descrição do seu projeto em uma linha. 
Ex: Ferramenta para sincronizar operações e sinais entre MetaTrader 4/5 e a plataforma IQ Option.

## 📖 Sobre o Projeto

O **SyncMT4** é uma solução robusta para traders que desejam automatizar ou espelhar suas operações entre o MetaTrader e a IQ Option. Utilizando a velocidade e a confiabilidade da biblioteca de mensageria ZeroMQ, este projeto permite uma comunicação de baixa latência entre um Expert Advisor (EA) ou script rodando no MQL e uma aplicação Python que interage com a API da IQ Option.

**Principais Funcionalidades:**
*   [Ex: Recebimento de sinais de um EA no MT4 e execução na IQ Option.]
*   [Ex: Sincronização de estado de ordens entre as duas plataformas.]
*   [Ex: Gerenciamento de risco e configurações personalizáveis.]
*   [Adicione outras funcionalidades importantes aqui.]

### 🛠️ Construído Com

*   [Python](https://www.python.org/)
*   [IQ Option API](https://github.com/iqoptionapi/iqoptionapi)
*   [mql-zmq](https://github.com/dingmaotu/mql-zmq) - Binding ZeroMQ para MQL
*   [ZeroMQ](https://zeromq.org/)

---

## 🚀 Começando

Siga estas instruções para ter uma cópia do projeto rodando na sua máquina local para desenvolvimento e testes.

### ✅ Pré-requisitos

Para que o projeto funcione, você precisará ter os seguintes softwares instalados:

*   **Python 3.8+**
*   **MetaTrader 4 ou 5**
*   **Biblioteca ZeroMQ**: As DLLs pré-compiladas (`libsodium.dll` e `libzmq.dll`) devem ser colocadas no diretório `Libraries` do seu terminal MetaTrader. Consulte a documentação do mql-zmq para mais detalhes.

### ⚙️ Instalação

1.  **Clone o repositório:**
    ```sh
    git clone https://github.com/seu-usuario/SyncMT4.git
    cd SyncMT4
    ```

2.  **Crie e ative um ambiente virtual (Recomendado):**
    ```sh
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux / macOS
    source venv/bin/activate
    ```

3.  **Instale as dependências Python:**
    ```sh
    pip install -r requirements.txt
    ```
    *(Observação: Se você ainda não tem um arquivo `requirements.txt`, posso te ajudar a criar um!)*

4.  **Configure o lado do MetaTrader (MQL):**
    *   Copie os arquivos do Expert Advisor/Script (ex: `SyncMT4.mq4`) para a pasta `MQL4/Experts` (ou `MQL5/Experts`) do seu terminal.
    *   Copie os arquivos de include do `mql-zmq` para a pasta `MQL4/Include`.
    *   Compile o EA no MetaEditor.

---

## 📈 Uso

Para iniciar a sincronização, siga os passos:

1.  **Inicie o Expert Advisor no MetaTrader:**
    Anexe o EA a um gráfico de sua preferência. Certifique-se de que o "AutoTrading" está habilitado no terminal.

2.  **Execute o script Python:**
    Abra um terminal, ative o ambiente virtual e execute o cliente Python.
    ```sh
    python bot/bot_core.py --usuario "seu-email" --senha "sua-senha"
    ```

**Exemplo de configuração:**
[Você pode adicionar aqui uma seção sobre como configurar um arquivo `.env` ou `config.ini` para gerenciar credenciais e outras configurações de forma segura, em vez de passá-las pela linha de comando.]

---

## 🗺️ Roadmap

*   [ ] Implementar gerenciamento de risco "Sorosgale".
*   [ ] Adicionar suporte a múltiplos pares de moedas simultaneamente.
*   [ ] Criar uma interface gráfica simples para monitoramento.

Veja as issues abertas para uma lista completa de funcionalidades propostas (e bugs conhecidos).

---

## 🤝 Contribuição

Contribuições são o que tornam a comunidade de código aberto um lugar incrível para aprender, inspirar e criar. Qualquer contribuição que você fizer será **muito apreciada**.

1.  Faça um Fork do projeto
2.  Crie sua Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Faça o Commit de suas alterações (`git commit -m 'Add some AmazingFeature'`)
4.  Faça o Push para a Branch (`git push origin feature/AmazingFeature`)
5.  Abra um Pull Request

---

## 📄 Licença

Distribuído sob a Licença MIT. Veja `LICENSE` para mais informações.

---

## 📧 Contato

Seu Nome - @seu_twitter - seu.email@exemplo.com

Link do Projeto: https://github.com/seu-usuario/SyncMT4
