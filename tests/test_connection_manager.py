
import unittest
from unittest.mock import MagicMock, patch, call
import threading
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.connection_manager import ConnectionManager

# To run tests in a deterministic way, we will mock threading and time
class TestConnectionManager(unittest.TestCase):

    def setUp(self):
        """Set up mocks for API, callbacks, and threading."""
        self.mock_api = MagicMock()
        self.mock_log_callback = MagicMock()
        self.mock_status_callback = MagicMock()

        # Make the test synchronous by not actually starting threads
        self.patcher_thread = patch('threading.Thread', side_effect=self.thread_side_effect)
        self.mock_thread_class = self.patcher_thread.start()
        self.threads = []

        self.patcher_lock = patch('threading.Lock', MagicMock())
        self.mock_lock_class = self.patcher_lock.start()

        self.patcher_event = patch('threading.Event')
        self.mock_event_class = self.patcher_event.start()
        self.mock_stop_event = self.mock_event_class.return_value
        self.mock_stop_event.is_set.return_value = False # Not stopped by default

        self.cm = ConnectionManager(
            api_instance=self.mock_api,
            log_callback=self.mock_log_callback,
            status_callback=self.mock_status_callback
        )

    def tearDown(self):
        """Stop patchers."""
        self.patcher_thread.stop()
        self.patcher_lock.stop()
        self.patcher_event.stop()

    def thread_side_effect(self, target, daemon=True):
        """A side effect to capture thread targets to run them manually."""
        thread = MagicMock()
        thread.daemon = daemon
        thread.target = target
        thread.start = lambda: target()
        thread.join = MagicMock()
        self.threads.append(thread)
        return thread

    def test_start_and_stop(self):
        """Test the start and stop methods."""
        self.cm.start()
        self.mock_log_callback.assert_called_with("Gerenciador de Conexão iniciado.", "INFO")
        self.assertEqual(len(self.threads), 1)
        self.assertEqual(self.threads[0].target, self.cm._health_check_loop)

        self.cm.stop()
        self.mock_stop_event.set.assert_called_once()
        self.threads[0].join.assert_called_once()
        self.mock_log_callback.assert_called_with("Gerenciador de Conexão parado.", "INFO")

    def test_health_check_connection_is_healthy(self):
        """Test the health check loop when the connection is stable."""
        self.mock_api.check_connect.return_value = True
        self.mock_api.get_server_timestamp.return_value = time.time()
        self.cm.is_connected = False

        # Run one loop iteration
        self.cm._health_check_loop()

        self.assertTrue(self.cm.is_connected)
        self.mock_status_callback.assert_called_with("IQ", "CONECTADO", "Online")
        self.mock_log_callback.assert_called_with("Conexão com a IQ Option está saudável.", "INFO")
        self.assertEqual(self.cm.reconnect_attempts, 0)

    def test_health_check_connection_lost(self):
        """Test the health check loop when connection is lost."""
        self.cm.is_connected = True
        self.mock_api.check_connect.return_value = False

        # Run one loop iteration
        self.cm._health_check_loop()

        self.assertFalse(self.cm.is_connected)
        self.mock_log_callback.assert_called_with("Conexão com a IQ Option perdida.", "AVISO")
        # Check if reconnection was triggered (a new thread would be created)
        self.assertEqual(len(self.threads), 1)
        self.assertEqual(self.threads[0].target, self.cm._reconnect_with_backoff)

    @patch('bot.connection_manager.ConnectionManager._reconnect_with_backoff')
    def test_health_check_api_exception(self, mock_reconnect):
        """Test health check when get_server_timestamp raises an exception."""
        self.cm.is_connected = True
        self.mock_api.check_connect.return_value = True
        self.mock_api.get_server_timestamp.side_effect = Exception("Network error")

        self.cm._health_check_loop()

        self.assertFalse(self.cm.is_connected)
        self.mock_log_callback.assert_called_with(
            "Health Check falhou, mesmo com check_connect() True. Erro: Network error", "AVISO"
        )
        mock_reconnect.assert_called_once()

    def test_reconnect_flow_succeeds(self):
        """Test the full reconnection logic with success on the first attempt."""
        self.mock_stop_event.wait.return_value = None # Don't actually wait
        self.mock_api.connect.return_value = (True, 'Success')

        self.cm._reconnect_with_backoff()

        self.mock_log_callback.assert_any_call("Tentando reconectar em 5 segundos... (Tentativa 1/5)", "AVISO")
        self.mock_api.connect.assert_called_once()
        self.mock_log_callback.assert_any_call("Reconectado com sucesso à IQ Option!", "INFO")
        self.assertTrue(self.cm.is_connected)
        self.assertEqual(self.cm.reconnect_attempts, 0)

    def test_reconnect_flow_fails_critically(self):
        """Test the reconnection logic when it fails all attempts."""
        self.mock_stop_event.wait.return_value = None
        self.mock_api.connect.return_value = (False, 'Failed')

        # Run the reconnect logic enough times to trigger critical failure
        for i in range(self.cm.max_reconnect_attempts):
            self.cm._reconnect_with_backoff()

        self.mock_log_callback.assert_called_with(
            "FALHA CRÍTICA DE CONEXÃO. VERIFIQUE SUA INTERNET E REINICIE O ROBÔ.", "ERRO"
        )
        self.mock_status_callback.assert_called_with("IQ", "ERRO", "Falha Crítica")
        self.mock_stop_event.set.assert_called_once() # Should stop the manager

if __name__ == '__main__':
    unittest.main()
