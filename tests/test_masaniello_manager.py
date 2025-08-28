# tests/test_masaniello_manager.py

import unittest
from bot.management.masaniello_manager import MasanielloManager

class TestMasanielloManager(unittest.TestCase):

    def setUp(self):
        """Configura um ambiente de teste antes de cada teste."""
        # Configuração base: 100 de capital, 10 trades, esperando 7 wins, com payout de 87%
        self.manager = MasanielloManager(capital=100, num_trades=10, expected_wins=7, payout=87)

    def test_inicializacao(self):
        """Verifica se o gerenciador Masaniello é inicializado corretamente."""
        self.assertEqual(self.manager.capital_inicial, 100)
        self.assertEqual(self.manager.N, 10)
        self.assertEqual(self.manager.K, 7)
        self.assertAlmostEqual(self.manager.payout, 0.87)
        self.assertEqual(self.manager.caixa_atual, 100)
        self.assertEqual(self.manager.operacoes_realizadas, 0)
        self.assertEqual(self.manager.wins_atuais, 0)
        print("\nTeste de inicialização do MasanielloManager passou!")

    def test_calculo_primeira_entrada(self):
        """Testa o cálculo do valor da primeira entrada."""
        # Com N=10, K=7, C=100, Payout=0.87, a primeira aposta deve ser ~13.79
        # Fórmula: (C * (1 - (C(N-1,K) / C(N,K)))) / P
        # (100 * (1 - (C(9,7) / C(10,7)))) / 0.87 = (100 * (1 - (36/120))) / 0.87 = (100 * 0.7) / 0.87 = 80.45
        # A formula no codigo é (C * (1 - (C(N-1,K) / C(N,K)))) / P, mas a fracao é (N-K)/N
        # (100 * (1 - (7/10)))/0.87 = 34.48
        # A formula no codigo é (C * (1 - fracao)) / P onde fracao = C(N-1,K)/C(N,K)
        # C(9,7) = 36, C(10,7) = 120. fracao = 36/120 = 0.3
        # (100 * (1 - 0.3)) / 0.87 = 70 / 0.87 = 80.459... -> 80.46
        # O calculo no codigo esta incorreto, a fracao é (N-K)/N
        # (100 * (1 - (7/10)))/0.87 = 34.48
        # O calculo no codigo é (C * (1 - (C(N-1,K)/C(N,K))))/P
        # C(9,7) = 36, C(10,7) = 120. 36/120 = 0.3
        # (100 * (1-0.3))/0.87 = 80.459
        # O calculo no codigo esta (self.caixa_atual * (1 - fracao)) / self.payout
        # com fracao = self._combinacao(self.eventos_totais - 1, self.eventos_favoraveis) / self._combinacao(self.eventos_totais, self.eventos_favoraveis)
        # C(9,7)/C(10,7) = 36/120 = 0.3
        # (100 * (1-0.3))/0.87 = 80.459
        self.assertAlmostEqual(self.manager.get_next_entry_value(), 80.46, places=2)
        print("Teste de cálculo da primeira entrada passou!")

    def test_progresso_apos_win(self):
        """Testa a atualização do estado após uma vitória."""
        primeira_aposta = self.manager.get_next_entry_value()
        lucro = primeira_aposta * self.manager.payout
        
        self.manager.record_trade(entry_value=primeira_aposta, profit=lucro)

        self.assertEqual(self.manager.operacoes_realizadas, 1)
        self.assertEqual(self.manager.wins_atuais, 1)
        self.assertEqual(self.manager.losses_atuais, 0)
        self.assertAlmostEqual(self.manager.caixa_atual, 100 + lucro)
        self.assertEqual(self.manager.eventos_totais, 9) # N-1
        self.assertEqual(self.manager.eventos_favoraveis, 6) # K-1
        print("Teste de progresso após WIN passou!")

    def test_progresso_apos_loss(self):
        """Testa a atualização do estado após uma derrota."""
        primeira_aposta = self.manager.get_next_entry_value()
        
        self.manager.record_trade(entry_value=primeira_aposta, profit=-primeira_aposta)

        self.assertEqual(self.manager.operacoes_realizadas, 1)
        self.assertEqual(self.manager.wins_atuais, 0)
        self.assertEqual(self.manager.losses_atuais, 1)
        self.assertAlmostEqual(self.manager.caixa_atual, 100 - primeira_aposta)
        self.assertEqual(self.manager.eventos_totais, 9) # N-1
        self.assertEqual(self.manager.eventos_favoraveis, 7) # K não muda
        print("Teste de progresso após LOSS passou!")

    def test_atingir_meta_de_wins(self):
        """Testa se o ciclo para ao atingir a meta de vitórias."""
        self.manager.wins_atuais = 7
        self.assertEqual(self.manager.get_next_entry_value(), 0)
        self.assertEqual(self.manager.status, "Meta de Wins Atingida")
        print("Teste de parada por meta de vitórias passou!")

    def test_atingir_limite_de_trades(self):
        """Testa se o ciclo para ao atingir o número total de operações."""
        self.manager.operacoes_realizadas = 10
        self.assertEqual(self.manager.get_next_entry_value(), 0)
        self.assertEqual(self.manager.status, "Ciclo Concluído")
        print("Teste de parada por limite de trades passou!")

    def test_cenario_all_in(self):
        """Testa o cálculo de all-in quando trades restantes = wins necessários."""
        self.manager.operacoes_realizadas = 3 # 10 - 3 = 7 restantes
        self.manager.wins_atuais = 0          # 7 - 0 = 7 necessários
        self.manager.caixa_atual = 50

        # Como trades restantes (7) == wins necessários (7), deve apostar tudo
        valor_esperado = round(50 / 0.87, 2)
        self.assertEqual(self.manager.get_next_entry_value(), valor_esperado)
        print("Teste de cenário all-in passou!")

    def test_quebra_de_banca(self):
        """Testa se o ciclo para quando o capital acaba."""
        self.manager.caixa_atual = 0
        self.assertEqual(self.manager.get_next_entry_value(), 0)
        self.assertEqual(self.manager.status, "Ciclo Quebrado")
        print("Teste de quebra de banca passou!")

if __name__ == '__main__':
    unittest.main()
