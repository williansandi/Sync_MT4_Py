# SyncMT4: Trading Robot with IQ Option & MetaTrader Integration

[![Status do Projeto](https://img.shields.io/badge/status-em%20desenvolvimento-yellowgreen.svg)](https://shields.io/)
[![Licença](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)

A robust Python-based trading robot designed for seamless integration with IQ Option and MetaTrader platforms. Features include advanced UI for monitoring, secure credential management, and optimized trading strategies.

## 📖 Sobre o Projeto

O **SyncMT4** é uma solução robusta para traders que desejam automatizar ou espelhar suas operações entre o MetaTrader e a IQ Option. Utilizando a velocidade e a confiabilidade da biblioteca de mensageria ZeroMQ, este projeto permite uma comunicação de baixa latência entre um Expert Advisor (EA) ou script rodando no MQL e uma aplicação Python que interage com a API da IQ Option.

**Principais Funcionalidades:**
*   **Interface Gráfica Moderna (CustomTkinter):** Navegação fluida e monitoramento em tempo real de operações, estatísticas e logs.
*   **Integração com MetaTrader (via ZeroMQ):** Recebimento de sinais e execução de operações baseadas em estratégias do MT4.
*   **Gerenciamento de Credenciais Seguro:** Armazenamento de senhas criptografadas (Base64) para maior proteção.
*   **Robustez de Caminhos:** Localização automática de arquivos essenciais (config.db, fontes, etc.) independentemente do diretório de execução.
*   **Estratégias de Gerenciamento:** Suporte a ciclos de Martingale otimizados e gerenciamento de banca (Masaniello).
*   **Notícias Financeiras:** Integração para busca e exibição de notícias relevantes.
*   **Exportação de Pares:** Funcionalidade para exportar listas de pares de moedas para o MT4.

### 🛠️ Construído Com

*   [Python](https://www.python.org/)
*   [CustomTkinter](https://customtkinter.tomschimansky.com/)
*   [IQ Option API](https://github.com/iqoptionapi/iqoptionapi)
*   [ZeroMQ](https://zeromq.org/)
*   [mql-zmq](https://github.com/dingmaotu/mql-zmq) - Binding ZeroMQ para MQL

---

## 🚀 Começando

Siga estas instruções para ter uma cópia do projeto rodando na sua máquina local para desenvolvimento e testes.

### ✅ Pré-requisitos

Para que o projeto funcione, você precisará ter os seguintes softwares instalados:

*   **Python 3.8+**
*   **MetaTrader 4 ou 5**
*   **Biblioteca ZeroMQ para MT4**: As DLLs pré-compiladas (`libsodium.dll` e `libzmq.dll`) devem ser colocadas no diretório `Libraries` do seu terminal MetaTrader. Consulte a documentação do [mql-zmq](https://github.com/dingmaotu/mql-zmq) para mais detalhes sobre a instalação no MT4.

### ⚙️ Instalação

1.  **Clone o repositório:**
    ```sh
    git clone https://github.com/williansandi/Sync_MT4_Py.git
    cd Sync_MT4_Py
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

4.  **Configure o lado do MetaTrader (MQL):**
    Certifique-se de que seu Expert Advisor (EA) ou script MQL está configurado para se comunicar via ZeroMQ. Copie os arquivos MQL relevantes (ex: `SyncMT4.mq4` e includes do `mql-zmq`) para as pastas apropriadas do seu terminal MetaTrader (`MQL4/Experts`, `MQL4/Include`, etc.) e compile-os.

---

## 📈 Uso

Para iniciar o robô e a interface gráfica, siga os passos:

1.  **Inicie o Expert Advisor no MetaTrader:**
    Anexe o EA a um gráfico de sua preferência. Certifique-se de que o "AutoTrading" está habilitado no terminal.

2.  **Execute a Aplicação Python:**
    Abra um terminal, ative o ambiente virtual e execute o script principal:
    ```sh
    python main.py
    ```
    A interface gráfica será iniciada. Insira suas credenciais da IQ Option na tela de login. As credenciais serão salvas de forma segura para futuros acessos.

---

## 🗺️ Roadmap

*   [x] Criar uma interface gráfica simples para monitoramento.
*   [ ] Implementar gerenciamento de risco "Sorosgale".
*   [ ] Adicionar suporte a múltiplos pares de moedas simultaneamente.

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

Willian Sandi - williansandi@gmail.com

Link do Projeto: https://github.com/williansandi/Sync_MT4_Py.git