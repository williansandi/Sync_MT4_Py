from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt

class BacktestFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()

        # Título
        title = QLabel('Backtest de Estratégias e Gerenciamento')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        layout.addWidget(title)

        # Seleção de estratégia
        strat_layout = QHBoxLayout()
        strat_label = QLabel('Estratégia:')
        self.strat_combo = QComboBox()
        self.strat_combo.addItems(['MHI', 'MT4', 'Signal List'])  # Exemplo, pode ser dinâmico
        strat_layout.addWidget(strat_label)
        strat_layout.addWidget(self.strat_combo)
        layout.addLayout(strat_layout)

        # Seleção de gerenciamento
        mgmt_layout = QHBoxLayout()
        mgmt_label = QLabel('Gerenciamento:')
        self.mgmt_combo = QComboBox()
        self.mgmt_combo.addItems(['Ciclos', 'Masaniello'])
        mgmt_layout.addWidget(mgmt_label)
        mgmt_layout.addWidget(self.mgmt_combo)
        layout.addLayout(mgmt_layout)

        # Botão para carregar histórico
        file_layout = QHBoxLayout()
        self.file_label = QLabel('Nenhum arquivo selecionado')
        self.file_btn = QPushButton('Carregar Histórico')
        self.file_btn.clicked.connect(self.load_file)
        file_layout.addWidget(self.file_btn)
        file_layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        # Botão para iniciar backtest
        self.start_btn = QPushButton('Iniciar Backtest')
        self.start_btn.clicked.connect(self.run_backtest)
        layout.addWidget(self.start_btn)

        # Área de resultados
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

        # Tabela de operações (opcional)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Data', 'Sinal', 'Entrada', 'Resultado'])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.setWindowTitle('Backtest')
        self.resize(700, 600)
        self.setWindowTitle('Backtest')
        self.resize(700, 600)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Selecionar arquivo de histórico', '', 'CSV Files (*.csv);;All Files (*)')
        if file_path:
            self.file_label.setText(file_path)
            self.loaded_file = file_path
        else:
            self.file_label.setText('Nenhum arquivo selecionado')
            self.loaded_file = None

    def run_backtest(self):
        import csv
        from bot.management.cycle_manager import CycleManager
        from bot.management.masaniello_manager import MasanielloManager
        import os

        self.result_text.clear()
        self.table.setRowCount(0)

        if not hasattr(self, 'loaded_file') or not self.loaded_file or not os.path.exists(self.loaded_file):
            self.result_text.setText('Selecione um arquivo de histórico válido.')
            return

        estrategia = self.strat_combo.currentText()
        gerenciamento = self.mgmt_combo.currentText()

        # Configuração de exemplo para gerenciamento
        config = {
            'valor_entrada': 10,
            'niveis_martingale': 2,
            'fator_martingale': 2.3,
            'max_ciclos': 3,
            'payout_recuperacao': 87,
        }

        # Inicializa o gerenciamento
        if gerenciamento == 'Ciclos':
            manager = CycleManager(config, lambda msg, lvl: None)
        else:
            # Parâmetros fictícios para Masaniello
            manager = MasanielloManager(1000, 20, 10, 87)

        resultados = []
        lucro_total = 0

        with open(self.loaded_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Espera-se colunas: data, sinal, resultado (1=win, 0=loss), payout
                data = row.get('data', '')
                sinal = row.get('sinal', '')
                payout = float(row.get('payout', 87)) / 100.0
                resultado = int(row.get('resultado', 0))

                entry_value = manager.get_next_entry_value()
                if entry_value <= 0:
                    break
                profit = entry_value * payout if resultado == 1 else -entry_value
                lucro_total += profit
                manager.record_trade(profit, entry_value)

                resultados.append((data, sinal, f'{entry_value:.2f}', f'{"WIN" if resultado == 1 else "LOSS"}'))

        # Exibe resultados
        self.result_text.append(f'Estratégia: {estrategia}')
        self.result_text.append(f'Gerenciamento: {gerenciamento}')
        self.result_text.append(f'Lucro Total: R$ {lucro_total:.2f}')
        self.result_text.append(f'Operações simuladas: {len(resultados)}')

        self.table.setRowCount(len(resultados))
        for i, (data, sinal, entrada, res) in enumerate(resultados):
            self.table.setItem(i, 0, QTableWidgetItem(data))
            self.table.setItem(i, 1, QTableWidgetItem(sinal))
            self.table.setItem(i, 2, QTableWidgetItem(entrada))
            self.table.setItem(i, 3, QTableWidgetItem(res))
