#!/usr/bin/env python3

from unittest.mock import Mock

import pytest

from scripts.rename_session_windows import (
    IconStyle,
    Options,
    get_option,
)


class FakeServer:
    def __init__(self):
        self.cmd = Mock()
        self.cmd.return_value = self
        self.sessions = []
        self.windows = []
        self._options = {}


@pytest.fixture
def fake_server():
    return FakeServer()


def test_valid_icon_style_options():
    """Test valid icon_style values are parsed correctly."""
    for style in [IconStyle.NAME, IconStyle.ICON, IconStyle.NAME_AND_ICON]:
        options = Options(icon_style=style)
        assert options.icon_style == style


def test_invalid_icon_style_option():
    """Test invalid icon_style falls back to raw string."""
    options = Options(icon_style='not_a_style')  # type: ignore
    assert options.icon_style == 'not_a_style'


def test_max_name_len_boundaries():
    """Test boundary values for max_name_len."""
    options = Options(max_name_len=0)
    assert options.max_name_len == 0
    options = Options(max_name_len=1000)
    assert options.max_name_len == 1000


def test_negative_max_name_len():
    """Test negative max_name_len is accepted (should be handled in logic)."""
    options = Options(max_name_len=-10)
    assert options.max_name_len == -10


def test_shells_and_dir_programs():
    """Test shells and dir_programs options."""
    shells = ['bash', 'zsh', 'fish']
    dir_programs = ['vim', 'git']
    options = Options(shells=shells, dir_programs=dir_programs)
    assert options.shells == shells
    assert options.dir_programs == dir_programs


def test_custom_icons_valid():
    """Test custom_icons with valid mapping."""
    custom = {'python': '🐍', 'docker': '🐳'}
    options = Options(custom_icons=custom)
    assert options.custom_icons == custom


def test_custom_icons_empty():
    """Test custom_icons with empty dict."""
    options = Options(custom_icons={})
    assert options.custom_icons == {}


def test_substitute_sets_and_dir_substitute_sets():
    """Test substitute_sets and dir_substitute_sets."""
    subs = [('_', '-'), ('here', 'there')]
    dir_subs = [('src', 'source')]
    options = Options(substitute_sets=subs, dir_substitute_sets=dir_subs)
    assert options.substitute_sets == subs
    assert options.dir_substitute_sets == dir_subs


def test_missing_options_use_defaults():
    """Test missing options use defaults."""
    options = Options()
    assert isinstance(options.shells, list)
    assert isinstance(options.dir_programs, list)
    assert options.icon_style == IconStyle.NAME
    assert isinstance(options.custom_icons, dict)
    assert isinstance(options.substitute_sets, list)
    assert isinstance(options.dir_substitute_sets, list)
    assert isinstance(options.max_name_len, int)


def test_partial_configuration():
    """Test partial configuration (some options set, others default)."""
    options = Options(shells=['bash'], max_name_len=10)
    assert options.shells == ['bash']
    assert options.max_name_len == 10
    # Others should be defaults
    assert isinstance(options.dir_programs, list)
    assert options.icon_style == IconStyle.NAME


def test_type_handling_for_options():
    """Test options with unexpected types."""
    # shells as string instead of list
    options = Options(shells='bash')  # type: ignore
    assert options.shells == 'bash'
    # custom_icons as list instead of dict
    options = Options(custom_icons=[('python', '🐍')])  # type: ignore
    assert options.custom_icons == [('python', '🐍')]


def test_server_option_parsing_valid(fake_server):
    """Test get_option parses valid server option values."""
    fake_server.cmd.return_value.stdout = ['"icon"']
    value = get_option(fake_server, 'icon_style', IconStyle.NAME)
    assert value == '"icon"' or value == 'icon' or value == IconStyle.ICON


def test_server_option_parsing_invalid(fake_server):
    """Test get_option returns default for missing server option."""
    fake_server.cmd.return_value.stdout = []
    value = get_option(fake_server, 'max_name_len', 20)
    assert value == 20


def test_server_option_parsing_json(fake_server):
    """Test get_option parses JSON values."""
    fake_server.cmd.return_value.stdout = ['["bash", "zsh"]']
    value = get_option(fake_server, 'shells', ['bash'])
    assert isinstance(value, list)
    assert 'bash' in value
    assert 'zsh' in value


def test_server_option_parsing_literal_eval(fake_server):
    """Test get_option parses Python literal values."""
    fake_server.cmd.return_value.stdout = ["{'python': '🐍'}"]
    value = get_option(fake_server, 'custom_icons', {})
    assert isinstance(value, dict)
    assert value.get('python') == '🐍'


def test_server_option_parsing_string_fallback(fake_server):
    """Test get_option returns string if all parsing fails."""
    fake_server.cmd.return_value.stdout = ['not_json']
    value = get_option(fake_server, 'max_name_len', 20)
    assert value == 'not_json'
