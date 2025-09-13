
import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Classes to be tested are imported after patching
from bot.app_controller import AppController

# Mock the classes before they are imported by the controller
# This is a common pattern for testing controllers or orchestrators
mock_bot_core_class = MagicMock()
mock_mt4_strategy_class = MagicMock()
mock_mhi_strategy_class = MagicMock()
mock_signal_list_strategy_class = MagicMock()
mock_masaniello_manager_class = MagicMock()

# Apply patches at the module level
@patch('bot.app_controller.IQBotCore', mock_bot_core_class)
@patch('bot.app_controller.MT4Strategy', mock_mt4_strategy_class)
@patch('bot.app_controller.MHIStrategy', mock_mhi_strategy_class)
@patch('bot.app_controller.SignalListStrategy', mock_signal_list_strategy_class)
@patch('bot.app_controller.MasanielloManager', mock_masaniello_manager_class)
class TestAppController(unittest.TestCase):

    def setUp(self):
        """Set up a mock environment for the AppController."""
        # Reset mocks for each test to ensure isolation
        mock_bot_core_class.reset_mock()
        mock_mt4_strategy_class.reset_mock()
        mock_signal_list_strategy_class.reset_mock()

        self.mock_config_manager = MagicMock()
        self.mock_trade_logger = MagicMock()
        self.credentials = {'email': 'test@test.com', 'senha': '123'}

        self.controller = AppController(
            credentials=self.credentials,
            config_manager=self.mock_config_manager,
            trade_logger=self.mock_trade_logger
        )

        # Mock the UI callbacks
        self.mock_ui_callbacks = {
            'log_message': MagicMock(),
            'on_trade_result': MagicMock(),
            'update_metric_cards': MagicMock(),
            'update_robot_status': MagicMock(),
            'show_popup': MagicMock()
        }
        self.controller.set_ui_callbacks(self.mock_ui_callbacks)

        # Simulate a connected bot_core for most tests
        self.mock_bot_core_instance = mock_bot_core_class.return_value
        self.controller.bot_core = self.mock_bot_core_instance
        self.controller.bot_core.is_connected = True

    def test_start_bot_with_mt4_strategy(self):
        """Test starting the bot with the MT4 strategy."""
        self.controller.start_bot(strategy_name="Sinal MT4", selected_pair=None, signals=[])

        # Verify bot_core worker is started
        self.mock_bot_core_instance.start_background_worker.assert_called_once()

        # Verify MT4Strategy was instantiated and started
        mock_mt4_strategy_class.assert_called_once_with(
            self.mock_bot_core_instance, self.controller.zmq_context, self.controller._handle_status_update
        )
        self.assertEqual(self.controller.strategy, mock_mt4_strategy_class.return_value)
        self.controller.strategy.start.assert_called_once()

        # Verify UI status update
        self.mock_ui_callbacks['update_robot_status'].assert_called_with(True, False)

    def test_start_bot_with_signal_list_strategy(self):
        """Test starting the bot with the Signal List strategy."""
        signals = [{'id': 1, 'time': '10:30'}]
        self.controller.start_bot(strategy_name="Lista de Sinais", selected_pair=None, signals=signals)

        mock_signal_list_strategy_class.assert_called_once_with(
            self.mock_bot_core_instance, signals, self.controller._handle_status_update
        )
        self.controller.strategy.start.assert_called_once()

    def test_start_bot_fails_if_signal_list_is_empty(self):
        """Test that the bot does not start if the signal list is required and empty."""
        self.controller.start_bot(strategy_name="Lista de Sinais", selected_pair=None, signals=[])

        # Assert strategy was NOT created and a popup was shown
        mock_signal_list_strategy_class.assert_not_called()
        self.mock_ui_callbacks['show_popup'].assert_called_with("Erro", "Nenhum arquivo de sinais foi carregado.")

    def test_stop_bot_stops_strategy_and_workers(self):
        """Test the stop_bot functionality."""
        # Simulate a running strategy
        mock_strategy_instance = mock_mt4_strategy_class.return_value
        self.controller.strategy = mock_strategy_instance

        self.controller.stop_bot()

        # Verify strategy and bot_core methods were called
        mock_strategy_instance.stop.assert_called_once()
        self.mock_bot_core_instance.stop_background_worker.assert_called_once()
        self.assertIsNone(self.controller.strategy)

        # Verify UI update
        self.mock_ui_callbacks['update_robot_status'].assert_called_with(False, False)

    def test_handle_trade_result_updates_stats(self):
        """Test if a trade result callback correctly updates robot statistics."""
        # Initial state
        self.controller.robot_stats = {'today_profit': 10.0, 'wins': 1, 'losses': 0}

        # Result from a winning trade
        result_info = {'profit': 1.74, 'foi_executado': True, 'entry_value': 2.0}

        self.controller._handle_trade_result(result_info)

        # Check updated stats
        self.assertAlmostEqual(self.controller.robot_stats['today_profit'], 11.74)
        self.assertEqual(self.controller.robot_stats['wins'], 2)
        self.assertEqual(self.controller.robot_stats['losses'], 0)

        # Check that UI callbacks were triggered
        self.mock_ui_callbacks['on_trade_result'].assert_called_once()
        self.mock_ui_callbacks['update_metric_cards'].assert_called_once()

if __name__ == '__main__':
    unittest.main()
