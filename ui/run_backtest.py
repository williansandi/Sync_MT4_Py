from PyQt5.QtWidgets import QApplication
import sys
from backtest_frame import BacktestFrame

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BacktestFrame()
    window.show()
    sys.exit(app.exec_())
