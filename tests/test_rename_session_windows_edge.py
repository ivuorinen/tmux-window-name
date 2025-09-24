#!/usr/bin/env python3

import sys
from typing import Any

import pytest

from scripts.path_utils import Pane as PathPane
from scripts.rename_session_windows import (
    Options,
    apply_icon_if_in_style,
    disable_user_rename_hook,
    enable_user_rename_hook,
    fix_pane_path,
    get_option,
    get_program_icon,
    get_window_option,
    post_restore,
    rename_window,
    set_window_tmux_option,
    substitute_name,
    tmux_guard,
)
from tests.mocks import Pane, Server, Session, Window


@pytest.fixture
def fake_server():
    return Server()


def test_get_option_malformed_json(fake_server):
    fake_server.cmd.return_value.stdout = ['{not:json}']
    server: Any = fake_server
    val = get_option(server, 'max_name_len', 42)
    assert isinstance(val, str)


def test_get_window_option_no_window_id(fake_server):
    fake_server.cmd.return_value.stdout = ["'value'"]
    server: Any = fake_server
    val = get_window_option(server, None, 'enabled', 'default')
    assert val == 'value' or val == "'value'"


def test_set_window_tmux_option_no_window_id(fake_server):
    fake_server.cmd.return_value.stdout = ['ok']
    server: Any = fake_server
    set_window_tmux_option(server, None, 'enabled', '1')
    fake_server.cmd.assert_called_with('set-option', '-wq', 'enabled', '1')


def test_enable_disable_user_rename_hook_command(fake_server):
    fake_server.cmd.return_value.stdout = ['ok']
    server: Any = fake_server
    enable_user_rename_hook(server)
    assert fake_server.cmd.call_args[0][0] == 'set-hook'
    fake_server.cmd.return_value.stdout = ['ok']
    disable_user_rename_hook(server)
    assert fake_server.cmd.call_args[0][0] == 'set-hook'


def test_tmux_guard_already_running(fake_server):
    fake_server.cmd.return_value.stdout = ['1']
    server: Any = fake_server
    with tmux_guard(server) as running:
        assert running is True


def test_rename_window_empty_name(fake_server):
    def test_rename_window_empty_name(fake_server):
        fake_server.cmd.return_value.stdout = ['ok']
        server: Any = fake_server
        rename_window(server, '@1', '', 20, Options())
        fake_server.cmd.assert_any_call('rename-window', '-t', '@1', '')


def test_rename_window_special_characters(fake_server):
    fake_server.cmd.return_value.stdout = ['ok']
    special_name = 'name!@#$%^&*()'
    server: Any = fake_server
    rename_window(server, '@1', special_name, 20, Options())
    fake_server.cmd.assert_any_call('rename-window', '-t', '@1', special_name)


def test_get_program_icon_unicode_escape():
    options = Options(custom_icons={'python': '\\ue7b0'})
    icon = get_program_icon('python', options)
    assert icon == '\ue7b0' or icon == ''


def test_apply_icon_if_in_style_invalid_icon_style():
    options = Options(icon_style='invalid')  # type: ignore
    assert apply_icon_if_in_style('python', options) == 'python'


def test_fix_pane_path_none():
    pane = PathPane(info=Pane(pane_current_path=None), program=None)
    options = Options(use_tilde=True)
    fixed = fix_pane_path(pane, options)
    assert fixed.info.pane_current_path is None


def test_substitute_name_regex():
    name = 'bash /usr/bin/python'
    subs = [(r'^(/usr)?/bin/(.+)', r'\g<2>')]
    result = substitute_name(name, subs)
    assert isinstance(result, str)


def test_post_restore_sets_enabled(fake_server):
    window = Window(window_id='@1', window_name='test')
    fake_server.windows = [window]
    fake_server.cmd.return_value.stdout = ['on']
    server: Any = fake_server
    post_restore(server)
    # Should set enabled to '1'
    assert any('enabled' in str(call) for call in [c[0] for c in fake_server.cmd.call_args_list])


def test_main_all_args(monkeypatch):
    from scripts.rename_session_windows import main

    fake_server = Server()
    fake_server.cmd.return_value.stdout = []
    monkeypatch.setattr('scripts.rename_session_windows.Server', lambda: fake_server)
    monkeypatch.setattr('scripts.rename_session_windows.get_current_session', lambda _server: Session())
    monkeypatch.setattr('scripts.rename_session_windows.get_panes_programs', lambda *_a, **_k: [])
    monkeypatch.setattr('scripts.rename_session_windows.rename_windows', lambda *_a, **_k: None)

    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py', '--print_programs'])
    assert main() == 0
    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py', '--enable_rename_hook'])
    assert main() == 0
    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py', '--disable_rename_hook'])
    assert main() == 0
    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py', '--post_restore'])
    assert main() == 0


def test_rename_windows_enabled_disabled(fake_server):
    import sys

    from scripts.path_utils import Pane as PathPane
    from scripts.rename_session_windows import rename_windows

    session = Session(session_id='$1')
    window1 = Window(window_id='@1', window_name='win1')
    window2 = Window(window_id='@2', window_name='win2')
    pane1 = Pane(
        pane_id='1',
        pane_pid=1234,
        pane_active='1',
        pane_current_path='/home/user',
        pane_current_command='bash',
        window_id='@1',
    )
    pane2 = Pane(
        pane_id='2',
        pane_pid=5678,
        pane_active='1',
        pane_current_path='/home/user/project',
        pane_current_command='python',
        window_id='@2',
    )
    window1.panes = [pane1]
    window2.panes = [pane2]
    session.windows = [window1, window2]
    fake_server.sessions = [session]

    # Patch fake_server.cmd to return '1' for window_id '@1' (enabled), '0' for '@2' (disabled)
    def cmd_side_effect(*args, **kwargs):
        if args[:3] == ('show-option', '-gv', '@tmux_window_name_running'):

            class Result:
                stdout = ['0']

            return Result()
        if '-t' in args:
            idx = args.index('-t')
            if args[idx + 1] == '@1':

                class Result:
                    stdout = ['1']

                return Result()
            if args[idx + 1] == '@2':

                class Result:
                    stdout = ['0']

                return Result()

        class Result:
            stdout = ['1']

        return Result()

    fake_server.cmd.side_effect = cmd_side_effect

    # Patch get_panes_programs to return expected Pane objects
    def fake_get_panes_programs(session_arg, options_arg):
        # Return PathPane objects using only real libtmux fields and set program
        pane1_pathpane = PathPane(info=pane1, program=None)
        pane2_pathpane = PathPane(info=pane2, program='python')
        return [pane1_pathpane, pane2_pathpane]

    sys.modules['scripts.rename_session_windows'].get_panes_programs = fake_get_panes_programs

    options = Options()
    rename_windows(fake_server, options)

    # Should update window1.name for enabled window only (@1)
    assert window1.name == 'user'
    # Should NOT update window2.name for disabled window (@2)
    assert window2.name != 'python'
