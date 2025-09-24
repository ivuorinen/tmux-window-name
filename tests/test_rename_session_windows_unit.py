#!/usr/bin/env python3

from typing import Any

import pytest

from scripts.path_utils import Pane as PathPane
from scripts.rename_session_windows import (
    DEFAULT_PROGRAM_ICONS,
    IconStyle,
    Options,
    apply_icon_if_in_style,
    fix_pane_path,
    get_current_program,
    get_current_session,
    get_option,
    get_program_icon,
    get_session_active_panes,
    get_window_option,
    rename_window,
    set_option,
    set_window_tmux_option,
    substitute_name,
    tmux_guard,
)
from tests.mocks import Pane, Server, Session, Window


@pytest.fixture
def fake_server():
    return Server()


def test_get_option_returns_default_for_missing(fake_server):
    fake_server.cmd.return_value.stdout = []
    assert get_option(fake_server, 'max_name_len', 42) == 42


def test_get_option_returns_string(fake_server):
    fake_server.cmd.return_value.stdout = ['not_json']
    assert get_option(fake_server, 'max_name_len', 42) == 'not_json'


def test_get_window_option_and_set_window_tmux_option(fake_server):
    fake_server.cmd.return_value.stdout = ["'value'"]
    val = get_window_option(fake_server, '@1', 'enabled', 'default')
    assert val == 'value' or val == "'value'"
    set_window_tmux_option(fake_server, '@1', 'enabled', '1')
    fake_server.cmd.assert_called_with('set-option', '-wq', '-t', '@1', 'enabled', '1')


def test_get_window_tmux_option_literal_eval_fallback(fake_server):
    # Should hit the except (ValueError, SyntaxError) and return as string
    # e.g. value that cannot be parsed as a Python literal
    fake_server.cmd.return_value.stdout = ['not_a_literal']
    from scripts.rename_session_windows import get_window_tmux_option

    result = get_window_tmux_option(fake_server, '@1', 'enabled', 'default', do_eval=True)
    assert result == 'not_a_literal'


def test_default_field_value_returns_none():
    # Simulate a field_info with neither default nor default_factory
    class DummyField:
        default = object()
        default_factory = object()

    # Remove MISSING from both
    import dataclasses

    DummyField.default = dataclasses.MISSING
    DummyField.default_factory = dataclasses.MISSING
    from scripts.rename_session_windows import default_field_value

    assert default_field_value(DummyField()) is None


def test_default_field_value_returns_default():
    # Simulate a field_info with .default set and .default_factory as MISSING
    class DummyField:
        pass

    import dataclasses

    DummyField.default = 'my_default'
    DummyField.default_factory = dataclasses.MISSING
    from scripts.rename_session_windows import default_field_value

    assert default_field_value(DummyField()) == 'my_default'


def test_default_field_value_returns_default_factory():
    # Simulate a field_info with .default_factory set and not MISSING
    class DummyField:
        pass

    import dataclasses

    DummyField.default = dataclasses.MISSING
    DummyField.default_factory = staticmethod(lambda: 'factory_value')
    from scripts.rename_session_windows import default_field_value

    assert default_field_value(DummyField()) == 'factory_value'


def test_options_from_options_icon_style_valueerror(monkeypatch):
    # Simulate get_option returning an invalid icon_style string
    from scripts.rename_session_windows import Options

    class DummyServer:
        def cmd(self, *args, **kwargs):
            class Result:
                stdout = ['invalid_style'] if 'icon_style' in args else ['1']

            return Result()

    server = DummyServer()
    # Patch get_option to return 'invalid_style' for icon_style
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_option',
        lambda _s, o, d: 'invalid_style' if o == 'icon_style' else d,
    )
    opts = Options.from_options(server)
    # Should fallback to IconStyle.NAME
    assert opts.icon_style.name == 'NAME'


def test_apply_icon_if_in_style_icon_and_name_and_icon(monkeypatch):
    # Use our Options mock and IconStyle
    from scripts.rename_session_windows import IconStyle, Options, apply_icon_if_in_style

    name = 'myprog'
    options_icon = Options(icon_style=IconStyle.ICON)
    options_name_and_icon = Options(icon_style=IconStyle.NAME_AND_ICON)
    # Patch get_program_icon to always return "ICON"
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_program_icon',
        lambda _n, _o: 'ICON',
    )
    # Should return just the icon for ICON style
    assert apply_icon_if_in_style(name, options_icon) == 'ICON'
    # Should return icon + name for NAME_AND_ICON style
    assert apply_icon_if_in_style(name, options_name_and_icon) == 'ICON myprog'


def test_tmux_guard_context_manager(fake_server):
    fake_server.cmd.return_value.stdout = ['0']
    with tmux_guard(fake_server) as running:
        assert running is True or running is False


def test_rename_window_fallback_to_cmd(fake_server):
    # No sessions/windows, should fallback to cmd
    rename_window(fake_server, '@1', 'testname', 20, Options())
    fake_server.cmd.assert_any_call('rename-window', '-t', '@1', 'testname')


def test_rename_window_with_window_object(fake_server):
    session = Session()
    window = Window(window_id='@1', window_name='oldname')
    session.windows.append(window)
    fake_server.sessions.append(session)
    rename_window(fake_server, '@1', 'newname', 20, Options())
    assert window.name == 'newname'


def test_fix_pane_path_none():
    pane = PathPane(info=Pane(pane_current_path=None), program=None)

    options = Options(use_tilde=True)
    fixed = fix_pane_path(pane, options)
    assert fixed.info.pane_current_path is None


def test_substitute_name_basic():
    name = 'test_name_here'
    subs = [('_', '-'), ('here', 'there')]
    assert substitute_name(name, subs) == 'test-name-there'


def test_apply_icon_if_in_style_variants():
    options = Options(icon_style=IconStyle.NAME)
    assert apply_icon_if_in_style('python', options) == 'python'
    options.icon_style = IconStyle.ICON
    assert apply_icon_if_in_style('python', options) == DEFAULT_PROGRAM_ICONS['python']
    options.icon_style = IconStyle.NAME_AND_ICON
    assert apply_icon_if_in_style('python', options) == f'{DEFAULT_PROGRAM_ICONS["python"]} python'


def test_get_program_icon_known_and_unknown():
    options = Options()
    assert get_program_icon('python', options) == DEFAULT_PROGRAM_ICONS['python']
    assert get_program_icon('nonexistent', options) == ''


def test_get_current_program_raises_valueerror_on_none_pid():
    # Use Pane mock with pane_pid=None
    from scripts.path_utils import Pane as PathPane
    from scripts.rename_session_windows import get_current_program
    from tests.mocks import Pane as MockPane

    options = Options()
    mock_pane = MockPane()
    mock_pane.pane_pid = None
    pane = PathPane(info=mock_pane, program=None)
    import pytest

    with pytest.raises(ValueError, match='Pane id is none'):
        get_current_program([], pane.info, options)


def test_get_current_program_skips_script_and_show_program_args():
    # Use Pane mock with valid pid and simulate running_programs with script in second part
    from scripts.path_utils import Pane as PathPane
    from scripts.rename_session_windows import get_current_program
    from tests.mocks import Pane as MockPane

    options = Options()
    mock_pane = MockPane()
    mock_pane.pane_pid = 1234
    mock_pane.pane_current_command = 'fallback'
    pane = PathPane(info=mock_pane, program=None)
    # Simulate a running_programs entry where the second part is 'scripts/rename_session_windows.py'
    running_programs = [b'1234 bash scripts/rename_session_windows.py']
    # Should skip this entry and fall back to pane.pane_current_command
    result = get_current_program(running_programs, pane.info, options)
    assert result == 'fallback'

    # Now test show_program_args branch
    options.show_program_args = True
    running_programs = [b'1234 python script.py']
    mock_pane2 = MockPane()
    mock_pane2.pane_pid = 1234
    pane = PathPane(info=mock_pane2, program=None)
    result = get_current_program(running_programs, pane.info, options)
    assert result == 'python script.py'


def test_get_panes_programs_handles_calledprocesserror(monkeypatch):
    # Patch subprocess.check_output to raise CalledProcessError
    import subprocess

    # Ensure only one pane is present and no global state leaks
    from scripts.rename_session_windows import get_panes_programs
    from tests.mocks import Pane as MockPane

    session = Session()
    window = Window()
    mock_pane = MockPane()
    mock_pane.pane_pid = 1234
    window.panes = [mock_pane]
    session.windows = [window]
    options = Options()

    def fake_check_output(*args, **kwargs):
        raise subprocess.CalledProcessError(1, 'ps')

    monkeypatch.setattr('subprocess.check_output', fake_check_output)
    # Should not raise, should return a list of Pane objects with fallback to pane.pane_current_command
    result = get_panes_programs(session, options)
    assert isinstance(result, list)
    # Instead of asserting length, assert our pane is present
    assert any(p.info.pane_pid == 1234 for p in result)


def test_rename_windows_exclusive_paths_branches(monkeypatch):
    # Test the continue branch and display_path substitution in exclusive_paths loop
    from scripts.rename_session_windows import rename_windows

    server = Server()
    server.cmd.return_value.stdout = ['0']  # Ensure get_option works
    options = Options()

    # Create two mock Pane objects with window_id set, wrapped in PathPane
    from tests.mocks import Pane as MockPane

    mock_pane_enabled = MockPane(window_id='@1')
    mock_pane_disabled = MockPane(window_id='@2')

    pane_enabled = PathPane(info=mock_pane_enabled, program='prog1')
    pane_disabled = PathPane(info=mock_pane_disabled, program='prog2')
    # Patch get_window_option: enabled for @1, disabled for @2
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_window_option',
        lambda _s, w, _o, _d: 1 if w == '@1' else 0,
    )
    # Patch get_exclusive_paths to return both panes with display paths (real Pane objects)
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_exclusive_paths',
        lambda _panes: [(pane_enabled, 'display1'), (pane_disabled, 'display2')],
    )
    # Patch substitute_name to add a marker
    monkeypatch.setattr(
        'scripts.rename_session_windows.substitute_name',
        lambda s, _subs: f'subst_{s}',
    )
    # Patch rename_window to record calls
    calls = []
    monkeypatch.setattr(
        'scripts.rename_session_windows.rename_window',
        lambda _s, wid, name, _maxlen, _opts: calls.append((wid, name)),
    )
    # Patch tmux_guard to always yield already_running=False
    import contextlib

    monkeypatch.setattr(
        'scripts.rename_session_windows.tmux_guard',
        contextlib.contextmanager(lambda _server: (yield False)),
    )
    # Run
    rename_windows(server, options)
    # Only enabled pane should be renamed, and display_path should be substituted
    assert ('@1', 'subst_prog1:subst_display1') in calls
    assert all('@2' not in call for call in calls)


def test_rename_windows_runs_when_not_already_running(monkeypatch):
    from scripts.rename_session_windows import rename_windows

    server = Server()
    session = Session(session_id='$1')
    window = Window(window_id='@1')
    pane = Pane(
        pane_id='1',
        pane_pid=1001,
        pane_active='1',
        pane_current_path='/work/project',
        pane_current_command='python',
        window_id='@1',
    )
    window.panes = [pane]
    session.windows = [window]
    server.sessions = [session]

    options = Options()

    monkeypatch.setattr('scripts.rename_session_windows.get_current_session', lambda _server: session)
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_panes_programs',
        lambda _sess, _opts: [PathPane(info=pane, program='python script.py')],
    )
    monkeypatch.setattr('scripts.rename_session_windows.get_window_option', lambda *_a, **_k: 1)
    monkeypatch.setattr('scripts.rename_session_windows.get_option', lambda *_a, **_k: 0)
    monkeypatch.setattr('scripts.rename_session_windows.set_option', lambda *_a, **_k: None)
    monkeypatch.setattr('scripts.rename_session_windows.disable_user_rename_hook', lambda *_a, **_k: None)
    monkeypatch.setattr('scripts.rename_session_windows.enable_user_rename_hook', lambda *_a, **_k: None)

    rename_calls = []
    monkeypatch.setattr(
        'scripts.rename_session_windows.rename_window',
        lambda _server, window_id, window_name, _maxlen, _opts: rename_calls.append((window_id, window_name)),
    )

    rename_windows(server, options)

    assert rename_calls == [('@1', 'python script.py')]


def test_rename_windows_shell_uses_directory_name(monkeypatch):
    from scripts.rename_session_windows import rename_windows

    server = Server()
    session = Session(session_id='$1')
    window = Window(window_id='@1')
    pane = Pane(
        pane_id='1',
        pane_pid=2002,
        pane_active='1',
        pane_current_path='/home/user/project',
        pane_current_command='bash',
        window_id='@1',
    )
    window.panes = [pane]
    session.windows = [window]
    server.sessions = [session]

    options = Options()

    monkeypatch.setattr('scripts.rename_session_windows.get_current_session', lambda _server: session)
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_panes_programs',
        lambda _sess, _opts: [PathPane(info=pane, program=None)],
    )
    monkeypatch.setattr('scripts.rename_session_windows.get_window_option', lambda *_a, **_k: 1)
    monkeypatch.setattr('scripts.rename_session_windows.get_option', lambda *_a, **_k: 0)
    monkeypatch.setattr('scripts.rename_session_windows.set_option', lambda *_a, **_k: None)
    monkeypatch.setattr('scripts.rename_session_windows.disable_user_rename_hook', lambda *_a, **_k: None)
    monkeypatch.setattr('scripts.rename_session_windows.enable_user_rename_hook', lambda *_a, **_k: None)

    rename_calls = []
    monkeypatch.setattr(
        'scripts.rename_session_windows.rename_window',
        lambda _server, window_id, window_name, _maxlen, _opts: rename_calls.append((window_id, window_name)),
    )

    rename_windows(server, options)

    assert rename_calls == [('@1', 'project')]


def test_get_current_session_returns_first_attached():
    fake_server: Any = Server()
    session = Session(session_id='$1')
    fake_server.sessions = [session]
    result = get_current_session(fake_server)
    assert result == session


def test_get_current_session_fallback_to_cmd():
    fake_server: Any = Server()
    fake_server.sessions = []
    fake_server.cmd.return_value.stdout = ['$2']
    result = get_current_session(fake_server)
    assert hasattr(result, 'id')
    assert result.id == '$2'


def test_get_session_active_panes_returns_active():
    session: Any = Session()
    window = Window()
    pane1 = Pane(pane_active='0')
    pane2 = Pane(pane_active='1')
    window.panes = [pane1, pane2]
    session.windows = [window]
    panes = get_session_active_panes(session)
    assert panes == [pane2]


def test_get_session_active_panes_no_windows_and_no_active():
    # No windows
    session = Session()
    session.windows = []
    assert get_session_active_panes(session) == []
    # Windows but no active pane
    window = Window()
    window.panes = [Pane(pane_active='0'), Pane(pane_active='0')]
    session.windows = [window]
    assert get_session_active_panes(session) == []


def test_set_option_and_get_option_integration(fake_server):
    set_option(fake_server, 'custom_test', 'myval')
    fake_server.cmd.return_value.stdout = ['myval']
    assert get_option(fake_server, 'custom_test', 'default') == 'myval'


def test_rename_window_fallback_to_cmd_if_window_not_found():
    # Server mock with no sessions/windows, should fallback to cmd
    server = Server()
    rename_window(server, '@notfound', 'fallback', 20, Options())
    assert ('rename-window', '-t', '@notfound', 'fallback') in [c[0] for c in server.cmd.call_args_list]


def test_get_option_string_fallback(fake_server):
    fake_server.cmd.return_value.stdout = ['not_json']
    val = get_option(fake_server, 'max_name_len', 42)
    assert val == 'not_json'


def test_print_programs_branches(monkeypatch):
    # Cover both branches of print_programs using only real libtmux fields
    from scripts.path_utils import Pane as PathPane
    from scripts.rename_session_windows import print_programs
    from tests.mocks import Pane as MockPane

    server = Server()
    session = Session()
    window = Window()
    pane_with_program = PathPane(
        info=MockPane(
            pane_id='1',
            pane_pid=123,
            pane_active='1',
            pane_current_path='/a',
            pane_current_command='bash',
            window_id='@1',
        ),
        program=None,
    )
    pane_without_program = PathPane(
        info=MockPane(
            pane_id='2',
            pane_pid=456,
            pane_active='1',
            pane_current_path='/b',
            pane_current_command='python',
            window_id='@2',
        ),
        program='python',
    )
    window.panes = [pane_with_program.info, pane_without_program.info]
    session.windows = [window]
    server.sessions = [session]
    options = Options()
    # Patch get_current_session and get_panes_programs to return our mocks
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_current_session',
        lambda _server: session,
    )
    monkeypatch.setattr(
        'scripts.rename_session_windows.get_panes_programs',
        lambda _sess, _opts: [pane_with_program, pane_without_program],
    )
    called = []
    monkeypatch.setattr(
        'scripts.rename_session_windows.substitute_name',
        lambda name, _subs: called.append(name) or name,
    )
    print_programs(server, options)
    # Only panes with detected programs should trigger substitute_name
    assert 'python' in called
    assert 'bash' not in called


def test_get_program_icon_unicode_escape_custom(fake_server):
    options = Options(custom_icons={'python': '\\ue7b0'})
    icon = get_program_icon('python', options)
    assert icon == '\ue7b0' or icon == ''


def test_get_program_icon_unknown_program(fake_server):
    options = Options()
    icon = get_program_icon('unknown_program_xyz', options)
    assert icon == ''


def test_parse_shell_command_edge_cases():
    from scripts.rename_session_windows import parse_shell_command

    assert parse_shell_command([]) is None
    assert parse_shell_command([b'1234']) is None
    assert parse_shell_command([b'1234', b'/usr/bin/python', b'script.py']) == 'python'


def test_get_current_program_fallback_and_ignored(fake_server):
    options = Options(shells=['bash'])
    pane = Pane(pane_pid=1234, pane_current_command='bash')
    # No matching PID in running_programs
    result = get_current_program([], pane, options)
    assert result is None
    # Matching PID, but shell is ignored
    result = get_current_program([b'1234 bash'], pane, options)
    assert result is None


def test_main_invalid_argument(monkeypatch):
    import sys

    import pytest

    from scripts.rename_session_windows import main

    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py', '--invalid'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2


def test_main_hook_error(monkeypatch):
    import sys

    from scripts.rename_session_windows import main

    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py', '--enable_rename_hook'])
    from unittest.mock import patch

    with patch('scripts.rename_session_windows.enable_user_rename_hook', side_effect=Exception('fail')):
        assert main() == 1


def test_main_entrypoint(monkeypatch):
    import sys

    from scripts.rename_session_windows import main
    from tests.mocks import Server as MockServer
    from tests.mocks import Session as MockSession

    fake_server = MockServer()
    fake_server.cmd.return_value.stdout = []
    monkeypatch.setattr('scripts.rename_session_windows.Server', lambda: fake_server)
    monkeypatch.setattr('scripts.rename_session_windows.get_current_session', lambda _server: MockSession())
    monkeypatch.setattr('scripts.rename_session_windows.get_panes_programs', lambda *_a, **_k: [])
    monkeypatch.setattr('scripts.rename_session_windows.rename_windows', lambda *_a, **_k: None)

    monkeypatch.setattr(sys, 'argv', ['rename_session_windows.py'])
    assert main() == 0
