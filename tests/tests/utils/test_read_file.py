import unittest
from unittest.mock import mock_open, patch

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return "File not found!"

class TestReadFile(unittest.TestCase):
    
    @patch('builtins.open', new_callable=mock_open, read_data='file content')
    def test_read_existing_file(self, mock_file):
        self.assertEqual(read_file('existing_file.txt'), 'file content')
        mock_file.assert_called_once_with('existing_file.txt', 'r')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_read_non_existing_file(self, mock_file):
        self.assertEqual(read_file('non_existing_file.txt'), 'File not found!')
        mock_file.assert_called_once_with('non_existing_file.txt', 'r')

    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_read_empty_file(self, mock_file):
        self.assertEqual(read_file('empty_file.txt'), '')
        mock_file.assert_called_once_with('empty_file.txt', 'r')

if __name__ == '__main__':
    unittest.main()