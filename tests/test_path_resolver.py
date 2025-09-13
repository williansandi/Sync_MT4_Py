
import unittest
from unittest.mock import patch
import sys
import os

# Add project root to the path to import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.path_resolver import resource_path

class TestPathResolver(unittest.TestCase):

    def test_resource_path_normal_env(self):
        """Test resource_path in a standard (non-PyInstaller) environment."""
        # Ensure _MEIPASS is not set
        if hasattr(sys, '_MEIPASS'):
            del sys._MEIPASS

        relative = 'assets/some_icon.ico'
        result_path = resource_path(relative)

        # Construct the expected path
        # The function goes up one level from utils/, so the project root is the parent dir
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        expected_path = os.path.join(project_root, relative)

        self.assertEqual(result_path, expected_path)

    @patch.dict(sys.__dict__, {'_MEIPASS': '/tmp/_MEIPASS'}, clear=True)
    def test_resource_path_pyinstaller_env(self):
        """Test resource_path in a simulated PyInstaller environment."""
        relative = 'data/config.json'
        result_path = resource_path(relative)

        # In PyInstaller, the path should be relative to _MEIPASS
        expected_path = os.path.join('/tmp/_MEIPASS', relative)

        self.assertEqual(result_path, expected_path)

    def test_resource_path_with_empty_relative_path(self):
        """Test resource_path with an empty relative path."""
        if hasattr(sys, '_MEIPASS'):
            del sys._MEIPASS
            
        result_path = resource_path('')
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.assertEqual(result_path, project_root)

if __name__ == '__main__':
    unittest.main()
