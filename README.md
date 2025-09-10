# SyncMT4: Trading Robot with IQ Option & MetaTrader Integration

[![Project Status](https://img.shields.io/badge/status-in%20development-yellowgreen.svg)](https://shields.io/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)

A robust Python-based trading robot designed for seamless integration with IQ Option and MetaTrader platforms. Features include an advanced UI for monitoring, secure credential management, and optimized trading strategies.

## 📖 About The Project

**SyncMT4** is a robust solution for traders looking to automate or mirror their operations between MetaTrader and IQ Option. Leveraging the speed and reliability of the ZeroMQ messaging library, this project enables low-latency communication between an Expert Advisor (EA) or script running in MQL and a Python application that interacts with the IQ Option API.

**Key Features:**
*   **Modern Graphical Interface (CustomTkinter):** Fluid navigation and real-time monitoring of operations, statistics, and logs.
*   **MetaTrader Integration (via ZeroMQ):** Receive signals and execute trades based on MT4 strategies.
*   **Secure Credential Management:** Encrypted password storage (Base64) for enhanced protection.
*   **Robust Path Handling:** Automatic location of essential files (config.db, fonts, etc.) regardless of the execution directory.
*   **Strategy Management:** Support for optimized Martingale cycles and money management (Masaniello).
*   **Financial News:** Integration for fetching and displaying relevant news.
*   **Pair Export:** Functionality to export currency pair lists to MT4.

### 🛠️ Built With

*   [Python](https://www.python.org/)
*   [CustomTkinter](https://customtkinter.tomschimansky.com/)
*   [IQ Option API](https://github.com/iqoptionapi/iqoptionapi)
*   [ZeroMQ](https://zeromq.org/)
*   [mql-zmq](https://github.com/dingmaotu/mql-zmq) - ZeroMQ Binding for MQL

---

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### ✅ Prerequisites

To run the project, you will need the following software installed:

*   **Python 3.8+**
*   **MetaTrader 4 or 5**
*   **ZeroMQ Library for MT4**: Pre-compiled DLLs (`libsodium.dll` and `libzmq.dll`) must be placed in the `Libraries` directory of your MetaTrader terminal. Refer to the [mql-zmq](https://github.com/dingmaotu/mql-zmq) documentation for more details on MT4 installation.

### ⚙️ Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/williansandi/Sync_MT4_Py.git
    cd Sync_MT4_Py
    ```

2.  **Create and activate a virtual environment (Recommended):**
    ```sh
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux / macOS
    source venv/bin/activate
    ```

3.  **Install Python dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Configure the MetaTrader side (MQL):**
    Ensure your Expert Advisor (EA) or MQL script is configured to communicate via ZeroMQ. Copy the relevant MQL files (e.g., `SyncMT4.mq4` and `mql-zmq` includes) to the appropriate folders in your MetaTrader terminal (`MQL4/Experts`, `MQL4/Include`, etc.) and compile them.

---

## 📈 Usage

To start the robot and the graphical interface, follow these steps:

1.  **Start the Expert Advisor in MetaTrader:**
    Attach the EA to a chart of your choice. Ensure "AutoTrading" is enabled in the terminal.

2.  **Execute the Python Application:**
    Open a terminal, activate the virtual environment, and run the main script:
    ```sh
    python main.py
    ```
    The graphical interface will start. Enter your IQ Option credentials on the login screen. Credentials will be securely saved for future access.

---

## 🗺️ Roadmap

*   [x] Create a simple graphical interface for monitoring.
*   [ ] Implement "Sorosgale" risk management.
*   [ ] Add support for multiple currency pairs simultaneously.

See the open issues for a full list of proposed features (and known bugs).

---

## 🤝 Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📧 Contact

Willian Sandi - willianmarinhos@gmail.com
Instagram: [instagram.com/Williansandi](https://instagram.com/Williansandi)

Project Link: https://github.com/williansandi/Sync_MT4_Py.git
