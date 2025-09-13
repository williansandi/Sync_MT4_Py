# tests/test_mhi_strategy.py

import unittest
from unittest.mock import MagicMock
from bot.strategies.mhi_strategy import MHIStrategy
import logging

class TestMHIStrategy(unittest.TestCase):

    def setUp(self):
        """Configura um ambiente de teste antes de cada teste."""
        # Criamos um "mock" (simulador) para o bot_core
        # Isso nos permite testar a estratégia de forma isolada, sem precisar
        # de uma conexão real com a IQ Option.
        self.mock_bot_core = MagicMock()
        self.mock_bot_core.log = MagicMock()
        self.mock_bot_core.api.get_server_timestamp.return_value = 1678886400 # Timestamp de exemplo
        self.ativo = "EURUSD-TEST"

        # Instanciamos a estratégia com o bot simulado
        self.strategy = MHIStrategy(self.mock_bot_core, self.ativo)

    def test_instanciacao(self):
        """Testa se a estratégia MHI é instanciada corretamente."""
        # Verificamos se a estratégia foi criada e se os atributos
        # principais foram definidos corretamente.
        self.assertIsNotNone(self.strategy)
        self.assertEqual(self.strategy.ativo, self.ativo)
        self.assertEqual(self.strategy.bot_core, self.mock_bot_core)
        logging.info("\nTeste de instanciação da MHIStrategy passou com sucesso!")

    def test_analisar_e_operar_com_sinal_de_put(self):
        """Testa a lógica de análise quando o resultado é PUT (venda)."""
        # Simulamos o retorno da API com 3 velas: 2 verdes e 1 vermelha
        self.mock_bot_core.api.get_candles.return_value = [
            {'open': 1, 'close': 2},  # Verde
            {'open': 1, 'close': 2},  # Verde
            {'open': 2, 'close': 1}   # Vermelha
        ]

        # Executamos o método de análise
        self.strategy._analisar_e_operar()

        # Verificamos se o método de trade foi chamado com a direção correta ('put')
        self.mock_bot_core.executar_trade.assert_called_with(self.ativo, 'put', 1)
        logging.info("Teste de análise com sinal de PUT passou com sucesso!")

    def test_analisar_e_operar_com_sinal_de_call(self):
        """Testa a lógica de análise quando o resultado é CALL (compra)."""
        # Simulamos o retorno da API com 3 velas: 2 vermelhas e 1 verde
        self.mock_bot_core.api.get_candles.return_value = [
            {'open': 2, 'close': 1},  # Vermelha
            {'open': 2, 'close': 1},  # Vermelha
            {'open': 1, 'close': 2}   # Verde
        ]

        self.strategy._analisar_e_operar()

        self.mock_bot_core.executar_trade.assert_called_with(self.ativo, 'call', 1)
        logging.info("Teste de análise com sinal de CALL passou com sucesso!")

    def test_analisar_e_operar_com_doji(self):
        """Testa se a análise é abortada quando uma vela Doji é encontrada."""
        # Simulamos o retorno da API com uma vela Doji
        self.mock_bot_core.api.get_candles.return_value = [
            {'open': 1, 'close': 2},  # Verde
            {'open': 1, 'close': 1},  # Doji
            {'open': 2, 'close': 1}   # Vermelha
        ]

        self.strategy._analisar_e_operar()

        # Verificamos que o método de trade NÃO foi chamado
        self.mock_bot_core.executar_trade.assert_not_called()
        logging.info("Teste de análise com Doji passou com sucesso!")

if __name__ == '__main__':
    unittest.main()

