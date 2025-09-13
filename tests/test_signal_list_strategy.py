
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
import threading
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.strategies.signal_list_strategy import SignalListStrategy

class TestSignalListStrategy(unittest.TestCase):

    def setUp(self):
        """Set up mocks for bot_core, callbacks, and threading."""
        self.mock_bot_core = MagicMock()
        self.mock_status_callback = MagicMock()

        # The strategy takes the signal list directly
        self.signals = [
            {'id': 1, 'asset': 'EURUSD', 'time': '10:30', 'action': 'call', 'timeframe': 1, 'status': 'pending'},
            {'id': 2, 'asset': 'AUDCAD', 'time': '10:35', 'action': 'put', 'timeframe': 5, 'status': 'pending'}
        ]

        # Mock threading to control the loop
        self.patcher_thread = patch('threading.Thread', side_effect=self.thread_side_effect)
        self.mock_thread_class = self.patcher_thread.start()
        self.threads = []

        self.patcher_event = patch('threading.Event')
        self.mock_event_class = self.patcher_event.start()
        self.mock_stop_event = self.mock_event_class.return_value
        self.mock_stop_event.is_set.return_value = False
        
        self.patcher_sleep = patch('time.sleep', return_value=None)
        self.mock_sleep = self.patcher_sleep.start()

        self.strategy = SignalListStrategy(
            bot_core=self.mock_bot_core,
            signals=self.signals,
            status_callback=self.mock_status_callback
        )

    def tearDown(self):
        self.patcher_thread.stop()
        self.patcher_event.stop()
        self.patcher_sleep.stop()

    def thread_side_effect(self, target, daemon=True):
        thread = MagicMock()
        thread.daemon = daemon
        thread.target = target
        # Run the target synchronously when start() is called
        thread.start = lambda: target()
        thread.join = MagicMock()
        self.threads.append(thread)
        return thread

    @patch('bot.strategies.signal_list_strategy.datetime')
    def test_execute_timely_signal(self, mock_datetime):
        """Test executing a signal that is on time (<= 3 seconds)."""
        # Set current time to 10:30:02
        mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 30, 2)
        
        # Stop the loop after one iteration
        self.mock_stop_event.is_set.side_effect = [False, True]
        self.strategy._run_loop()

        # Verify trade was executed
        self.mock_bot_core.executar_trade.assert_called_once_with(
            'EURUSD', 'call', 1, {"signal_id": 1}
        )
        # Verify status was updated
        self.assertEqual(self.signals[0]['status'], 'executing')

    @patch('bot.strategies.signal_list_strategy.datetime')
    def test_skip_expired_signal(self, mock_datetime):
        """Test skipping a signal that is late (> 3 seconds)."""
        # Set current time to 10:30:04
        mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 30, 4)

        self.mock_stop_event.is_set.side_effect = [False, True]
        self.strategy._run_loop()

        # Verify trade was NOT executed
        self.mock_bot_core.executar_trade.assert_not_called()
        # Verify log message for expiration
        self.mock_bot_core.log_callback.assert_called_with(
            "Sinal EURUSD às 10:30 expirou (vela virou).", "AVISO"
        )
        # Verify status was updated
        self.assertEqual(self.signals[0]['status'], 'expired')

    @patch('bot.strategies.signal_list_strategy.datetime')
    def test_no_action_if_no_pending_signal_for_current_time(self, mock_datetime):
        """Test that nothing happens if no signal matches the current time."""
        # Set current time to 10:31:01
        mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 31, 1)

        self.mock_stop_event.is_set.side_effect = [False, True]
        self.strategy._run_loop()

        self.mock_bot_core.executar_trade.assert_not_called()

    @patch('bot.strategies.signal_list_strategy.datetime')
    def test_no_action_if_signal_is_not_pending(self, mock_datetime):
        """Test that it ignores signals with status other than 'pending'."""
        self.signals[0]['status'] = 'executed'
        # Set current time to 10:30:01
        mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 30, 1)

        self.mock_stop_event.is_set.side_effect = [False, True]
        self.strategy._run_loop()

        self.mock_bot_core.executar_trade.assert_not_called()

if __name__ == '__main__':
    unittest.main()
