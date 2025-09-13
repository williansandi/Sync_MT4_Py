
import unittest
import sqlite3
from unittest.mock import patch, MagicMock, call
import sys
import os

# As a test file, we need to add the project root to the path to import the modules
# This is a common practice in testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):

    @patch('utils.config_manager.resource_path')
    @patch('sqlite3.connect')
    def setUp(self, mock_connect, mock_resource_path):
        """Set up a mock database for testing."""
        # Mock resource_path to return a predictable path
        self.db_path = 'test_config.db'
        mock_resource_path.return_value = self.db_path

        # Mock the connection and cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        mock_connect.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Default settings to be returned by fetchall
        self.default_settings = {
            'perfil_de_risco': 'MODERADO', 'conservador_recuperacao': '50',
            'valor_entrada': '5', 'stop_win': '100', 'stop_loss': '100'
        }
        self.mock_cursor.fetchall.return_value = list(self.default_settings.items())

    @patch('utils.config_manager.logging') # Mock logging to suppress output
    def test_initialization_and_setup(self, mock_logging):
        """Test that the database is set up correctly on initialization."""
        # We initialize the class, which should trigger the setup
        cm = ConfigManager(db_path=self.db_path)

        # Verify that resource_path and connect were called correctly
        self.setUp.patches[1].return_value.assert_called_once_with(self.db_path) # resource_path
        self.setUp.patches[0].assert_called_once_with(self.db_path) # sqlite3.connect

        # Check if the CREATE TABLE statement was executed
        self.mock_cursor.execute.assert_any_call(
            '''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        '''
        )

        # Check if at least one default setting is inserted (as a sample)
        self.mock_cursor.execute.assert_any_call(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ('perfil_de_risco', 'MODERADO')
        )
        
        # Check if commit was called
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

    @patch('utils.config_manager.logging')
    def test_get_all_settings(self, mock_logging):
        """Test retrieving all settings."""
        cm = ConfigManager(db_path=self.db_path)
        settings = cm.get_all_settings()

        # Verify the correct SELECT query was executed
        self.mock_cursor.execute.assert_called_with("SELECT key, value FROM settings")
        
        # Verify the returned settings match the mock data
        self.assertEqual(settings, self.default_settings)

    @patch('utils.config_manager.logging')
    def test_save_setting(self, mock_logging):
        """Test saving a single setting."""
        cm = ConfigManager(db_path=self.db_path)
        cm.save_setting('stop_win', '200')

        # Verify the REPLACE query was executed with the correct parameters
        self.mock_cursor.execute.assert_called_with(
            "REPLACE INTO settings (key, value) VALUES (?, ?)",
            ('stop_win', '200')
        )
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

    @patch('utils.config_manager.logging')
    def test_save_settings(self, mock_logging):
        """Test saving a dictionary of settings."""
        cm = ConfigManager(db_path=self.db_path)
        settings_to_save = {'stop_win': '250', 'stop_loss': '150'}
        cm.save_settings(settings_to_save)

        # Verify that execute was called for each setting
        calls = [
            call("REPLACE INTO settings (key, value) VALUES (?, ?)", ('stop_win', '250')),
            call("REPLACE INTO settings (key, value) VALUES (?, ?)", ('stop_loss', '150'))
        ]
        self.mock_cursor.execute.assert_has_calls(calls, any_order=True)
        
        # Verify commit and close were called
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
