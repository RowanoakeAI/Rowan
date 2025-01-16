import pytest
from unittest.mock import Mock, patch
import sys
import io
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from main import main
from core.rowan_assistant import RowanAssistant

@pytest.fixture
def mock_assistant():
    with patch('main.RowanAssistant') as mock:
        assistant = Mock()
        mock.return_value = assistant
        assistant.chat.return_value = "Mock response"
        yield assistant

@pytest.fixture
def mock_io():
    with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
        with patch('builtins.input') as mock_input:
            yield mock_stdout, mock_input

def test_initialization(mock_io, mock_assistant):
    mock_stdout, mock_input = mock_io
    mock_input.side_effect = ["exit"]
    
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    output = mock_stdout.getvalue()
    assert "Rowan Assistant initialized" in output
    assert mock_assistant.chat.call_count == 0
    assert exc_info.value.code == 0

def test_normal_chat(mock_io, mock_assistant):
    mock_stdout, mock_input = mock_io
    mock_input.side_effect = ["hello", "exit"]
    
    with pytest.raises(SystemExit):
        main()
    
    assert mock_assistant.chat.call_count == 1
    mock_assistant.chat.assert_called_with("hello")
    output = mock_stdout.getvalue()
    assert "Mock response" in output

def test_exit_command(mock_io, mock_assistant):
    mock_stdout, mock_input = mock_io
    mock_input.side_effect = ["exit"]
    
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    output = mock_stdout.getvalue()
    assert "Goodbye!" in output
    assert exc_info.value.code == 0

def test_quit_command(mock_io, mock_assistant):
    mock_stdout, mock_input = mock_io
    mock_input.side_effect = ["quit"]
    
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    assert exc_info.value.code == 0
    output = mock_stdout.getvalue()
    assert "Goodbye!" in output

def test_keyboard_interrupt(mock_io, mock_assistant):
    mock_stdout, mock_input = mock_io
    mock_input.side_effect = KeyboardInterrupt()
    
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    assert exc_info.value.code == 0
    output = mock_stdout.getvalue()
    assert "Exiting gracefully..." in output

def test_general_exception(mock_io, mock_assistant):
    mock_stdout, mock_input = mock_io
    mock_input.side_effect = ["hello", Exception("Test error"), "exit"]
    mock_assistant.chat.side_effect = Exception("Test error")
    
    main()
    
    output = mock_stdout.getvalue()
    assert "Error: Test error" in output
    assert "Continuing..." in output

def test_project_root_in_path():
    project_root = str(Path(__file__).parent)
    assert project_root in sys.path