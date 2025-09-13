# tests/test_cycle_manager.py

import unittest
from unittest.mock import MagicMock
from bot.management.cycle_manager import CycleManager
import logging

class TestCycleManager(unittest.TestCase):

    def setUp(self):
        """Configura um ambiente de teste antes de cada teste."""
        self.mock_log_callback = MagicMock()
        self.base_config = {
            'management_type': 'agressivo',
            'valor_entrada': 10.0,
            'niveis_martingale': 2,
            'fator_martingale': 2.0,
            'max_ciclos': 3,
            'payout_recuperacao': 87.0
        }
        self.manager = CycleManager(self.base_config, self.mock_log_callback)

    def test_inicializacao_carrega_configuracoes_corretamente(self):
        """Verifica se o gerenciador é inicializado com os valores corretos da configuração."""
        self.assertEqual(self.manager.management_type, 'agressivo')
        self.assertEqual(self.manager.initial_entry_value, 10.0)
        self.assertEqual(self.manager.martingale_levels, 2)
        self.assertEqual(self.manager.martingale_factor, 2.0)
        self.assertEqual(self.manager.max_cycles, 3)
        self.assertAlmostEqual(self.manager.payout_for_recovery, 0.87)
        logging.info("Teste de inicialização do CycleManager passou!")

    def test_reset_restaura_estado_inicial(self):
        """Verifica se o método reset restaura os atributos para o padrão."""
        # Modificamos alguns valores para simular um estado de operação
        self.manager.current_cycle = 2
        self.manager.current_martingale_level = 1
        self.manager.total_loss_to_recover = 100
        self.manager.is_active = False

        # Chamamos o reset
        self.manager.reset()

        # Verificamos se os valores foram restaurados
        self.assertEqual(self.manager.current_cycle, 1)
        self.assertEqual(self.manager.current_martingale_level, 0)
        self.assertEqual(self.manager.total_loss_to_recover, 0.0)
        self.assertTrue(self.manager.is_active)
        logging.info("Teste do método reset() passou!")

    def test_get_next_entry_value_primeiro_ciclo_entrada_inicial(self):
        """Testa o valor de entrada inicial no primeiro ciclo."""
        self.assertEqual(self.manager.get_next_entry_value(), 10.0)
        logging.info("Teste de valor de entrada inicial passou!")

    def test_get_next_entry_value_primeiro_ciclo_primeiro_martingale(self):
        """Testa o valor de entrada após uma perda (1º Martingale)."""
        # Simulamos uma perda na entrada inicial
        self.manager.record_trade(profit=-10, entry_value=10.0)
        
        # O próximo valor deve ser o valor inicial * fator martingale
        self.assertEqual(self.manager.get_next_entry_value(), 20.0) # 10 * 2.0
        logging.info("Teste de valor do 1º Martingale passou!")

    def test_record_trade_win_reseta_o_ciclo(self):
        """Testa se um WIN reseta o nível de martingale e o ciclo."""
        # Simulamos uma perda e depois um ganho
        self.manager.record_trade(profit=-10, entry_value=10.0) # Loss
        self.manager.record_trade(profit=17.4, entry_value=20.0) # Win

        self.assertEqual(self.manager.current_martingale_level, 0)
        self.assertEqual(self.manager.current_cycle, 1)
        self.assertEqual(self.manager.accumulated_loss_cycle, 0.0)
        logging.info("Teste de reset após um WIN passou!")

    def test_ciclo_agressivo_passa_para_ciclo_de_recuperacao(self):
        """Testa a transição para um ciclo de recuperação após exceder os níveis de gale."""
        # Simulamos perdas em todos os níveis de martingale
        self.manager.record_trade(-10, 10) # Entrada inicial -> Loss
        self.manager.record_trade(-20, 20) # Gale 1 -> Loss
        self.manager.record_trade(-40, 40) # Gale 2 -> Loss (limite do config)

        # Verificamos se o gerenciador avançou para o próximo ciclo
        self.assertEqual(self.manager.current_cycle, 2)
        self.assertEqual(self.manager.current_martingale_level, 0)
        # A perda total a ser recuperada deve ser a soma das entradas do ciclo anterior
        self.assertEqual(self.manager.total_loss_to_recover, 70) # 10 + 20 + 40
        logging.info("Teste de transição para ciclo de recuperação passou!")

    def test_get_next_entry_value_em_ciclo_de_recuperacao(self):
        """Testa o cálculo do valor de entrada no início de um ciclo de recuperação."""
        # Simulamos a transição para o ciclo 2
        self.test_ciclo_agressivo_passa_para_ciclo_de_recuperacao()

        # Calculamos o valor esperado para a recuperação
        valor_recuperacao = 70 / 0.87 # total_loss_to_recover / payout
        self.assertAlmostEqual(self.manager.get_next_entry_value(), valor_recuperacao)
        logging.info("Teste de valor de entrada em ciclo de recuperação passou!")

    def test_atingir_maximo_de_ciclos_pausa_o_gerenciamento(self):
        """Testa se o gerenciamento é pausado ao atingir o número máximo de ciclos."""
        self.manager.current_cycle = 3
        self.manager.total_loss_to_recover = 100 # Apenas para simular
        
        # Simulamos uma perda no último nível do último ciclo
        self.manager.current_martingale_level = 3 # Excedendo os 2 níveis
        self.manager.record_trade(-10, 10) # Uma perda qualquer para acionar a lógica

        self.assertFalse(self.manager.is_active)
        logging.info("Teste de pausa após atingir máximo de ciclos passou!")

if __name__ == '__main__':
    unittest.main()
