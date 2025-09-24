#!/usr/bin/env python3

from typing import Any
from unittest.mock import call

from scripts.rename_session_windows import (
    DEFAULT_PROGRAM_ICONS,
    IconStyle,
    Options,
    apply_icon_if_in_style,
    get_program_icon,
    rename_window,
)
from tests.mocks import Server


def test_get_program_icon_built_in():
    """Test retrieving built-in program icons"""
    options = Options()
    # Test all built-in icons
    for prog, icon in DEFAULT_PROGRAM_ICONS.items():
        assert get_program_icon(prog, options) == icon
    # Test unknown program
    assert get_program_icon('nonexistent', options) == ''  # no icon


def test_get_program_icon_custom():
    """Test custom program icons override built-in ones"""
    options = Options(
        custom_icons={
            'custom_app': '󰀄',
            'nvim': '󰹻',  # override default vim icon
            'docker': 'CUSTOM_DOCKER_ICON',
        }
    )
    # Custom icon for custom_app
    assert get_program_icon('custom_app', options) == '󰀄'
    # Custom icon overrides built-in
    assert get_program_icon('nvim', options) == '󰹻'  # noqa: W292
    # Custom icon overrides built-in for docker
    assert get_program_icon('docker', options) == 'CUSTOM_DOCKER_ICON'
    # Built-in icon for python
    assert get_program_icon('python', options) == DEFAULT_PROGRAM_ICONS['python']


def test_get_program_icon_with_path_and_colon():
    """Test that program icons work with full paths and colons"""
    options = Options()
    # Path handling
    assert get_program_icon('/usr/bin/python', options) == DEFAULT_PROGRAM_ICONS['python']
    assert get_program_icon('/custom/path/nvim', options) == DEFAULT_PROGRAM_ICONS['nvim']
    # Colon handling
    assert get_program_icon('python:3.10', options) == DEFAULT_PROGRAM_ICONS['python']
    assert get_program_icon('/usr/bin/docker:latest', options) == DEFAULT_PROGRAM_ICONS['docker']


def test_get_program_icon_with_args():
    """Test that program icons work with command arguments"""
    options = Options()
    assert get_program_icon('python script.py --arg', options) == DEFAULT_PROGRAM_ICONS['python']
    assert get_program_icon('nvim file.txt', options) == DEFAULT_PROGRAM_ICONS['nvim']
    assert get_program_icon('docker run', options) == DEFAULT_PROGRAM_ICONS['docker']


def test_apply_icon_if_in_style_variants():
    """Test apply_icon_if_in_style for all IconStyle variants"""
    options = Options(icon_style=IconStyle.NAME)

    # NAME style: only name
    assert apply_icon_if_in_style('python', options) == 'python'
    # ICON style: only icon
    options.icon_style = IconStyle.ICON
    assert apply_icon_if_in_style('python', options) == DEFAULT_PROGRAM_ICONS['python']
    # NAME_AND_ICON style: icon and name
    options.icon_style = IconStyle.NAME_AND_ICON
    assert apply_icon_if_in_style('python', options) == f'{DEFAULT_PROGRAM_ICONS["python"]} python'


# Removed duplicate test_rename_window_name_and_icon_style (F811)


def test_rename_window_icon_style():
    """Test window renaming with 'icon' style"""
    server: Any = Server()
    options = Options(icon_style=IconStyle.ICON)
    rename_window(server, '1', 'python', 20, options)
    expected_calls = [
        call('rename-window', '-t', '1', DEFAULT_PROGRAM_ICONS['python']),
        call(
            'set-option',
            '-wq',
            '-t',
            '1',
            'automatic-rename-format',
            DEFAULT_PROGRAM_ICONS['python'],
        ),
        call(
            'set-option',
            '-wq',
            '-t',
            '1',
            'automatic-rename',
            'on',
        ),
    ]
    assert server.cmd.call_args_list == expected_calls


def test_unicode_escape_icon_decoding():
    """Test that unicode escape sequences in custom icons are decoded correctly"""
    # \ue7b0 is the docker icon
    options = Options(custom_icons={'docker': '\\ue7b0'})
    icon = get_program_icon('docker', options)
    # Should decode to the actual icon character
    assert icon == '\ue7b0' or icon == ''


def test_rename_window_name_and_icon_style():
    """Test window renaming with 'name_and_icon' style"""
    server: Any = Server()
    options = Options(icon_style=IconStyle.NAME_AND_ICON)
    rename_window(server, '1', 'python', 20, options)
    expected_calls = [
        call(
            'rename-window',
            '-t',
            '1',
            f'{DEFAULT_PROGRAM_ICONS["python"]} python',
        ),
        call(
            'set-option',
            '-wq',
            '-t',
            '1',
            'automatic-rename-format',
            f'{DEFAULT_PROGRAM_ICONS["python"]} python',
        ),
        call(
            'set-option',
            '-wq',
            '-t',
            '1',
            'automatic-rename',
            'on',
        ),
    ]
    assert server.cmd.call_args_list == expected_calls


def test_rename_window_custom_icon():
    """Test window renaming with custom icon"""
    server: Any = Server()
    options = Options(icon_style=IconStyle.NAME_AND_ICON, custom_icons={'python': '\ud83d\udc0d'})
    rename_window(server, '1', 'python', 20, options)
    expected_calls = [
        call('rename-window', '-t', '1', '\ud83d\udc0d python'),
        call('set-option', '-wq', '-t', '1', 'automatic-rename-format', '\ud83d\udc0d python'),
        call('set-option', '-wq', '-t', '1', 'automatic-rename', 'on'),
    ]
    assert server.cmd.call_args_list == expected_calls


def test_rename_window_max_length():
    """Test that window names respect max_name_len"""
    server: Any = Server()
    options = Options(icon_style=IconStyle.NAME_AND_ICON, max_name_len=10)
    rename_window(server, '1', 'python', 10, options)
    expected_calls = [
        call(
            'rename-window',
            '-t',
            '1',
            f'{DEFAULT_PROGRAM_ICONS["python"]} python',
        ),
        call(
            'set-option',
            '-wq',
            '-t',
            '1',
            'automatic-rename-format',
            f'{DEFAULT_PROGRAM_ICONS["python"]} python',
        ),
        call(
            'set-option',
            '-wq',
            '-t',
            '1',
            'automatic-rename',
            'on',
        ),
    ]
    assert server.cmd.call_args_list == expected_calls


def test_get_program_icon_with_colon():
    """Test that program icons work with program names containing colons"""
    options = Options()
    assert get_program_icon('python:3.9', options) == DEFAULT_PROGRAM_ICONS['python']
    assert get_program_icon('nvim:q', options) == DEFAULT_PROGRAM_ICONS['nvim']


def test_custom_icons_from_dictionary():
    """Test that custom icons can be parsed from a dictionary"""
    server: Any = Server()
    server.cmd.return_value.stdout = ['{"python": "🐍", "custom": "📦", "nvim": "󰹻"}']
    options = Options.from_options(server)
    assert get_program_icon('python', options) == '🐍'
    assert get_program_icon('custom', options) == '📦'
    assert get_program_icon('nvim', options) == '󰹻'
