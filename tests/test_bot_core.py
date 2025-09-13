
import unittest
from unittest.mock import MagicMock, patch, call
import queue
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.bot_core import IQBotCore

class TestBotCore(unittest.TestCase):

    @patch('bot.bot_core.CycleManager')
    @patch('bot.bot_core.MasanielloManager')
    @patch('bot.bot_core.IQ_Option')
    def setUp(self, MockIQOption, MockMasaniello, MockCycle):
        """Set up a mock-heavy environment for testing IQBotCore."""
        self.credentials = {'email': 'test@test.com', 'senha': '123', 'conta': 'PRACTICE'}
        self.config = {
            'stop_win': '100', 'stop_loss': '100', 'valor_entrada': '2',
            'usar_ciclos': 'S', 'fator_martingale': '2.0'
        }
        self.mock_log = MagicMock()
        self.mock_trade_result = MagicMock()
        self.mock_trade_logger = MagicMock()

        # Mock external dependencies
        self.mock_api = MockIQOption.return_value
        self.mock_cycle_manager = MockCycle.return_value
        self.mock_masaniello_manager = MockMasaniello.return_value

        # Mock threading and queues to run synchronously
        self.patcher_thread = patch('threading.Thread', side_effect=self.thread_side_effect)
        self.patcher_queue = patch('queue.Queue', side_effect=queue.Queue)
        self.mock_thread_class = self.patcher_thread.start()
        self.mock_queue_class = self.patcher_queue.start()
        self.threads = []

        self.bot = IQBotCore(
            credentials=self.credentials,
            config=self.config,
            log_callback=self.mock_log,
            trade_result_callback=self.mock_trade_result,
            pair_list_callback=MagicMock(),
            status_callback=MagicMock(),
            trade_logger=self.mock_trade_logger
        )
        self.bot.is_connected = True # Assume connected for most tests
        self.bot.api = self.mock_api

    def tearDown(self):
        self.patcher_thread.stop()
        self.patcher_queue.stop()

    def thread_side_effect(self, target, daemon=True):
        thread = MagicMock(target=target, daemon=daemon)
        thread.start = target # Run synchronously
        self.threads.append(thread)
        return thread

    def test_executar_trade_adds_to_queue(self):
        """Test if executing a trade correctly adds it to the queue."""
        self.bot.is_running = True
        self.bot.executar_trade('EURUSD', 'call', 1, {'id': 1})
        self.mock_log.assert_any_call("Sinal para EURUSD (CALL) adicionado à fila de execução.", "INFO")
        
        # Check if the item was put in the queue
        self.assertFalse(self.bot.trade_queue.empty())
        item = self.bot.trade_queue.get_nowait()
        self.assertEqual(item, ('EURUSD', 'call', 1, {'id': 1}))

    @patch('time.sleep', return_value=None) # Prevent sleeping
    def test_trade_executor_loop_happy_path(self, mock_sleep):
        """Test the full processing of a single successful trade from the queue."""
        # --- MOCK SETUP ---
        self.bot.is_running = True
        self.bot.is_paused = False
        self.bot.operacoes_em_andamento = {}
        self.bot.open_assets_cache = {'binary': {'EURUSD-op': {}}}

        # Mock managers and API calls
        self.mock_cycle_manager.get_next_entry_value.return_value = (2.0, "Ciclos", True)
        self.mock_api.buy.return_value = (True, 'order_123')
        self.mock_api.check_win_v4.return_value = (True, 1.74) # Win

        # --- ACTION ---
        # Put a trade in the queue
        self.bot.trade_queue.put(('EURUSD', 'call', 1, {}))
        
        # Run the loop (it will run once and exit due to queue being empty)
        self.bot._trade_executor_loop()

        # --- ASSERTIONS ---
        # 1. Order was sent
        self.mock_api.buy.assert_called_once_with(2.0, 'EURUSD-op', 'call', 1)
        self.mock_log.assert_any_call("Ordem ACEITA pela corretora. ID da Ordem: order_123", 'SUCCESS')

        # 2. Result was checked
        self.mock_api.check_win_v4.assert_called_once_with('order_123')

        # 3. Result was recorded by the manager
        self.mock_cycle_manager.record_trade.assert_called_once_with(1.74, 2.0)

        # 4. UI was updated
        self.mock_trade_result.assert_called_once()
        self.assertEqual(self.bot.lucro_total, 1.74)

        # 5. Stop conditions were checked
        self.mock_log.assert_not_called("STOP WIN ATINGIDO", "STOP")
        self.mock_log.assert_not_called("STOP LOSS ATINGIDO", "STOP")

    def test_stop_win_hit(self):
        """Test if the bot stops when stop win is reached."""
        self.bot.is_running = True
        self.bot.stop_win = 100.0
        self.bot.lucro_total = 99.0
        
        # Simulate a winning trade result
        self.bot._aguardar_e_processar_resultado('order_win', 1)
        # Manually set the profit for the mock
        self.mock_api.check_win_v4.return_value = (True, 2.0)
        lucro = self.bot._aguardar_e_processar_resultado('order_win', 1)
        
        self.bot.check_stop()

        self.assertFalse(self.bot.is_running)
        self.mock_log.assert_called_with('STOP WIN ATINGIDO: $101.00', "STOP")

    def test_stop_loss_hit(self):
        """Test if the bot stops when stop loss is reached."""
        self.bot.is_running = True
        self.bot.stop_loss = 100.0
        self.bot.lucro_total = -99.0
        
        # Simulate a losing trade result
        self.mock_api.check_win_v4.return_value = (True, -2.0)
        lucro = self.bot._aguardar_e_processar_resultado('order_loss', 1)

        self.bot.check_stop()

        self.assertFalse(self.bot.is_running)
        self.mock_log.assert_called_with('STOP LOSS ATINGIDO: $-101.00', "STOP")

if __name__ == '__main__':
    unittest.main()
