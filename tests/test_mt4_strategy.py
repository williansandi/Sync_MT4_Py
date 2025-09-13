
import unittest
from unittest.mock import MagicMock, patch, call
import threading
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.strategies.mt4_strategy import MT4Strategy

class TestMT4Strategy(unittest.TestCase):

    def setUp(self):
        """Set up mocks for bot_core, ZMQ context, and threading."""
        self.mock_bot_core = MagicMock()
        self.mock_zmq_context = MagicMock()
        self.mock_socket = MagicMock()
        self.mock_status_callback = MagicMock()

        # Mock the ZMQ context and socket creation
        self.mock_zmq_context.socket.return_value = self.mock_socket

        # Mock threading to control the listener thread
        self.patcher_thread = patch('threading.Thread', side_effect=self.thread_side_effect)
        self.mock_thread_class = self.patcher_thread.start()
        self.threads = []

        self.patcher_event = patch('threading.Event')
        self.mock_event_class = self.patcher_event.start()
        self.mock_stop_event = self.mock_event_class.return_value
        self.mock_stop_event.is_set.return_value = False

        self.strategy = MT4Strategy(
            bot_core=self.mock_bot_core,
            context=self.mock_zmq_context,
            status_callback=self.mock_status_callback
        )

    def tearDown(self):
        self.patcher_thread.stop()
        self.patcher_event.stop()

    def thread_side_effect(self, target, daemon=True):
        thread = MagicMock()
        thread.daemon = daemon
        thread.target = target
        thread.start = lambda: target()
        thread.join = MagicMock()
        self.threads.append(thread)
        return thread

    def test_start_and_stop(self):
        """Test the start and stop methods of the strategy."""
        self.strategy.start()
        self.mock_bot_core.log_callback.assert_called_with("Estratégia MT4 iniciada. Aguardando sinais...", "STRATEGY")
        self.assertEqual(len(self.threads), 1)
        self.assertEqual(self.threads[0].target, self.strategy._listen_for_signals)

        self.strategy.stop()
        self.mock_stop_event.set.assert_called_once()
        self.threads[0].join.assert_called_once()
        self.mock_bot_core.log_callback.assert_called_with("Estratégia MT4 parada.", "STRATEGY")

    def test_process_valid_trade_signal(self):
        """Test processing a valid trade signal string."""
        signal = "EUR/USD SUPER COMPRA M15"
        self.strategy._process_trade_signal(signal)
        self.mock_bot_core.executar_trade.assert_called_once_with('EUR/USD', 'call', 15)

    def test_process_valid_put_signal(self):
        signal = "AUD/CAD SUPER VENDA M1"
        self.strategy._process_trade_signal(signal)
        self.mock_bot_core.executar_trade.assert_called_once_with('AUD/CAD', 'put', 1)

    def test_process_invalid_signals(self):
        """Test that invalid signals are ignored."""
        invalid_signals = [
            "EUR/USD POSSÍVEL COMPRA M1",  # Contains "POSSÍVEL"
            "GBP/JPY COMPRA M5",          # Missing "SUPER"
            "INVALID",                    # Too short
            ""
        ]
        for signal in invalid_signals:
            self.strategy._process_trade_signal(signal)
            # Ensure trade execution is never called for invalid signals
            self.mock_bot_core.executar_trade.assert_not_called()
            self.mock_bot_core.executar_trade.reset_mock()

    @patch('time.time')
    def test_listener_heartbeat_timeout(self, mock_time):
        """Test the heartbeat timeout logic in the listener."""
        # Setup: No message received
        self.mock_socket.poll.return_value = False
        
        # First run, time is 100
        mock_time.return_value = 100
        self.strategy._listen_for_signals() # This will set last_heartbeat_time

        # Second run, time is 120 (20s later), should trigger timeout
        mock_time.return_value = 120
        self.strategy._listen_for_signals()

        self.mock_status_callback.assert_called_with("MT4", "DESCONECTADO", "Sem sinal do EA!")

    def test_listener_receives_and_processes_signal(self):
        """Test the full loop from receiving a message to processing it."""
        # Setup: A valid trade signal is received
        self.mock_socket.poll.return_value = True
        self.mock_socket.recv_string.return_value = "GBPJPY SUPER VENDA M1"

        # Stop the loop after one iteration
        self.mock_stop_event.is_set.side_effect = [False, True]
        
        self.strategy._listen_for_signals()

        # Verify that the signal was processed and trade was executed
        self.mock_bot_core.executar_trade.assert_called_once_with('GBPJPY', 'put', 1)

if __name__ == '__main__':
    unittest.main()
