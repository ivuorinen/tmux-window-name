#!/usr/bin/env python3

import os
import sys
from unittest.mock import patch

import pytest

from scripts import rename_session_windows

pytestmark = pytest.mark.usefixtures('_reset_sys_argv')


@pytest.fixture
def _reset_sys_argv():
    orig_argv = sys.argv[:]
    yield
    sys.argv = orig_argv


def test_main_default_behavior():
    """Test main script with no arguments (default behavior)."""
    sys.argv = ['rename_session_windows.py']
    # Patch Server and rename_windows to avoid real tmux calls
    with (
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.rename_windows') as mock_rename_windows,
    ):
        mock_rename_windows.return_value = None
        result = rename_session_windows.main()
        assert result == 0
        mock_rename_windows.assert_called_once()


def test_main_print_programs(capsys):
    """Test main script with --print_programs argument."""
    sys.argv = ['rename_session_windows.py', '--print_programs']
    with (
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.print_programs') as mock_print_programs,
    ):
        mock_print_programs.return_value = None
        result = rename_session_windows.main()
        assert result == 0
        mock_print_programs.assert_called_once()


def test_main_enable_rename_hook():
    """Test main script with --enable_rename_hook argument."""
    sys.argv = ['rename_session_windows.py', '--enable_rename_hook']
    with (
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.enable_user_rename_hook') as mock_enable_hook,
    ):
        mock_enable_hook.return_value = None
        result = rename_session_windows.main()
        assert result == 0
        mock_enable_hook.assert_called_once()


def test_main_disable_rename_hook():
    """Test main script with --disable_rename_hook argument."""
    sys.argv = ['rename_session_windows.py', '--disable_rename_hook']
    with (
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.disable_user_rename_hook') as mock_disable_hook,
    ):
        mock_disable_hook.return_value = None
        result = rename_session_windows.main()
        assert result == 0
        mock_disable_hook.assert_called_once()


def test_main_post_restore():
    """Test main script with --post_restore argument."""
    sys.argv = ['rename_session_windows.py', '--post_restore']
    with (
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.post_restore') as mock_post_restore,
    ):
        mock_post_restore.return_value = None
        result = rename_session_windows.main()
        assert result == 0
        mock_post_restore.assert_called_once()


def test_main_invalid_argument():
    """Test main script with invalid argument."""
    sys.argv = ['rename_session_windows.py', '--invalid_arg']
    # Patch argparse to raise SystemExit for invalid argument
    with pytest.raises(SystemExit):
        rename_session_windows.main()


def test_main_server_exception():
    """Test main script raises exception if Server init fails."""
    sys.argv = ['rename_session_windows.py']
    msg = 'Server error'
    with (
        patch('scripts.rename_session_windows.Server', side_effect=Exception(msg)),
        pytest.raises(Exception, match=msg),
    ):
        rename_session_windows.main()


def test_main_hook_exception():
    """Test main script returns error code if hook fails."""
    sys.argv = ['rename_session_windows.py', '--enable_rename_hook']
    msg = 'Hook error'
    with (
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.enable_user_rename_hook', side_effect=Exception(msg)),
    ):
        result = rename_session_windows.main()
        assert result == 1


def test_main_print_programs_output(capsys):
    """Test main script prints output for --print_programs."""
    sys.argv = ['rename_session_windows.py', '--print_programs']
    with (
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.print_programs') as mock_print_programs,
    ):

        def fake_print_programs(server, options):
            print('Program: python')

        mock_print_programs.side_effect = fake_print_programs
        result = rename_session_windows.main()
        assert result == 0
        captured = capsys.readouterr()
        assert 'Program: python' in captured.out


def test_main_with_env_var():
    """Test main script with TMUX_PANE environment variable set."""
    sys.argv = ['rename_session_windows.py']
    with (
        patch.dict(os.environ, {'TMUX_PANE': '%1'}),
        patch('scripts.rename_session_windows.Server'),
        patch('scripts.rename_session_windows.rename_windows') as mock_rename_windows,
    ):
        mock_rename_windows.return_value = None
        result = rename_session_windows.main()
        assert result == 0
        mock_rename_windows.assert_called_once()
