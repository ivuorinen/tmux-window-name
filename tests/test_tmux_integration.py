#!/usr/bin/env python3

import pytest

from scripts.rename_session_windows import (
    IconStyle,
    Options,
    get_option,
    get_window_option,
    rename_window,
    set_option,
    set_window_tmux_option,
    tmux_guard,
)

pytestmark = pytest.mark.usefixtures('clear_env')


def test_set_option_roundtrip(tmux_session):
    server = tmux_session.server
    set_option(server, 'integration_option', '123')
    assert get_option(server, 'integration_option', 0) == 123


def test_set_window_tmux_option_roundtrip(tmux_session):
    server = tmux_session.server
    window = tmux_session.new_window(window_name='integration-window', attach=False)
    try:
        set_window_tmux_option(server, window.window_id, '@tmux_window_name_enabled', '0')
        assert get_window_option(server, window.window_id, 'enabled', 1) == 0
    finally:
        tmux_session.cmd('kill-window', '-t', window.window_id)


def test_tmux_guard_sets_running_flag(tmux_session):
    server = tmux_session.server
    set_option(server, 'running', '0')
    with tmux_guard(server) as already_running:
        assert already_running is False
        assert get_option(server, 'running', 0) == 1
    assert get_option(server, 'running', 0) == 0


def test_rename_window_updates_tmux(tmux_session):
    server = tmux_session.server
    window = tmux_session.new_window(window_name='integration-start', attach=False)
    try:
        options = Options(icon_style=IconStyle.NAME, max_name_len=32)
        rename_window(server, window.window_id, 'integration-name', options.max_name_len, options)
        window.refresh()
        assert window.name == 'integration-name'
        rename_format = server.cmd(
            'show-option',
            '-wqv',
            '-t',
            window.window_id,
            'automatic-rename-format',
        ).stdout[0]
        assert rename_format == 'integration-name'
        automatic_rename = server.cmd(
            'show-option',
            '-wqv',
            '-t',
            window.window_id,
            'automatic-rename',
        ).stdout[0]
        assert automatic_rename == 'on'
    finally:
        tmux_session.cmd('kill-window', '-t', window.window_id)
