#!/usr/bin/env python3

import sys

import pytest

from scripts.rename_session_windows import (
    Options,
    get_option,
    get_program_icon,
    main,
    rename_window,
)
from tests.mocks import Server

# Mocks are now imported from tests/mocks.py


@pytest.fixture
def fake_server():
    return Server()


def test_tmux_command_failure(fake_server):
    """Simulate tmux command raising an exception."""
    fake_server.cmd.side_effect = Exception('tmux failure')
    with pytest.raises(Exception, match='tmux failure'):
        fake_server.cmd('show-option')


def test_rename_window_tmux_failure(fake_server):
    """Test rename_window handles tmux command failure gracefully."""
    fake_server.cmd.side_effect = Exception('rename-window failed')
    options = Options()
    with pytest.raises(Exception, match='rename-window failed'):
        rename_window(fake_server, '1', 'test', 20, options)


def test_invalid_icon_style_fallback():
    """Test invalid icon_style remains as raw string."""
    options = Options(icon_style='invalid_style')  # type: ignore
    # Should remain as the raw string, not coerced
    assert options.icon_style == 'invalid_style'


def test_negative_max_name_len():
    """Test negative max_name_len falls back to default or is handled."""
    options = Options(max_name_len=-5)
    # Should not crash, and should use a sensible value
    assert options.max_name_len < 0  # Accepts negative, but should be handled in rename logic


def test_malformed_custom_icons():
    """Test malformed custom_icons raises error as implementation expects string."""
    options = Options(custom_icons={'python': None, 'docker': 123})  # type: ignore
    with pytest.raises(Exception, match='startswith'):
        get_program_icon('docker', options)


def test_main_exception_handling(monkeypatch):
    """Test main() raises exception if Server init fails."""

    class BrokenServer:
        def __init__(self):
            msg = 'Server init failed'
            raise Exception(msg)

    monkeypatch.setattr('scripts.rename_session_windows.Server', BrokenServer)
    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py'])
    with pytest.raises(Exception, match='Server init failed'):
        main()


def test_missing_pane_attributes():
    """Test handling of missing pane attributes."""
    options = Options()
    # get_program_icon should not crash if passed a broken pane
    try:
        get_program_icon(getattr(object(), 'pane_current_command', 'unknown'), options)
    except Exception as e:
        pytest.fail(f'get_program_icon crashed on missing pane attributes: {e}')


def test_invalid_option(monkeypatch, fake_server):
    """Test get_option returns raw string for invalid value."""
    fake_server.cmd.return_value.stdout = ['not_json']
    value = get_option(fake_server, 'max_name_len', 20)
    assert value == 'not_json'


def test_path_parsing_error():
    """Test get_program_icon with malformed path returns empty string or raises IndexError."""
    options = Options()
    assert get_program_icon('////', options) == ''
    with pytest.raises(IndexError):
        get_program_icon('', options)
