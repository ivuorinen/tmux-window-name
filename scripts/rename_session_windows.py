#!/usr/bin/env python3

__all__ = [
    # ...other exports...
    'default_field_value',
]

import ast
import dataclasses
import json
import logging
import logging.config
import re
import subprocess
import tempfile
from argparse import ArgumentParser
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, cast

from libtmux.pane import Pane as TmuxPane
from libtmux.server import Server
from libtmux.session import Session

from scripts.path_utils import Pane, get_exclusive_paths

OPTIONS_PREFIX = '@tmux_window_name_'
HOOK_INDEX = 8921
HOME_DIR = str(Path.home())
USR_BIN_REMOVER = (r'^(/usr)?/bin/(.+)', r'\g<2>')

# Nerd font icons for common programs
# Source for icons: https://www.nerdfonts.com/cheat-sheet
DEFAULT_PROGRAM_ICONS = {
    'nvim': '',  # nf-dev-vim
    'vim': '',  # nf-dev-vim
    'vi': '',  # nf-dev-vim
    'git': '',  # nf-dev-git
    'python': '',  # nf-dev-python
    'node': '',  # nf-dev-nodejs
    'npm': '',  # nf-dev-nodejs
    'yarn': '',  # nf-dev-nodejs
    'docker': '',  # nf-dev-docker
    'kubectl': '',  # nf-dev-kubernetes
    'go': '',  # nf-dev-go
    'rust': '',  # nf-dev-rust
    'cargo': '',  # nf-dev-rust
    'php': '',  # nf-dev-php
    'ruby': '',  # nf-dev-ruby
    'java': '',  # nf-dev-java
    'mvn': '',  # nf-dev-java
    'gradle': '',  # nf-dev-java
    'bash': '',  # nf-dev-terminal
    'zsh': '',  # nf-dev-terminal
    'fish': '',  # nf-dev-terminal
    'sh': '',  # nf-dev-terminal
}


def get_option(server: Server, option: str, default: Any) -> Any:
    out = server.cmd('show-option', '-gv', f'{OPTIONS_PREFIX}{option}').stdout
    if len(out) == 0:
        return default

    value = out[0]

    # Special handling for icon_style - it's a plain string
    if option == 'icon_style':
        return value

    # Try to parse as JSON first (safer than eval)
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try ast.literal_eval for Python literals (safe eval)
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        pass

    # Return as string if all parsing fails
    return value


def set_option(server: Server, option: str, val: str):
    server.cmd('set-option', '-g', f'{OPTIONS_PREFIX}{option}', val)


def get_window_option(server: Server, window_id: Optional[str], option: str, default: Any) -> Any:
    return get_window_tmux_option(server, window_id, f'{OPTIONS_PREFIX}{option}', default, do_eval=True)


def get_window_tmux_option(
    server: Server, window_id: Optional[str], option: str, default: Any, do_eval: bool = False
) -> Any:
    arguments = ['show-option', '-wqv']

    if window_id is not None:
        arguments.append('-t')
        arguments.append(window_id)

    arguments.append(option)
    out = server.cmd(*arguments).stdout

    if len(out) == 0:
        return default

    if do_eval:
        value = out[0]
        # Use ast.literal_eval for safe evaluation
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            # Return as string if parsing fails
            return value

    return out[0]


def set_window_tmux_option(server: Server, window_id: Optional[str], option: str, value: str) -> Any:
    arguments = ['set-option', '-wq']
    if window_id is not None:
        arguments.append('-t')
        arguments.append(window_id)

    arguments.append(option)
    arguments.append(value)

    server.cmd(*arguments)


def post_restore(server: Server):
    # Re enable tmux-window-name if `automatic-rename` is on
    for window in server.windows:
        if get_window_tmux_option(server, window.window_id, 'automatic-rename', 'on') == 'on':
            set_window_tmux_option(server, window.window_id, f'{OPTIONS_PREFIX}enabled', '1')
        else:
            set_window_tmux_option(server, window.window_id, f'{OPTIONS_PREFIX}enabled', '0')

    # Enable rename hook to enable tmux-window-name on later windows
    enable_user_rename_hook(server)


def enable_user_rename_hook(server: Server):
    """
    The hook:
        if window has name:
            set @tmux_window_name_enabled to 1
        else:
            set @tmux_window_name_enabled to 0

    @tmux_window_name_enabled (window option):
        Indicator if we should rename the window or not
    """
    current_file = str(Path(__file__).absolute())
    # Escape single quotes in the file path to prevent command injection
    current_file_escaped = current_file.replace("'", "'\\''")
    server.cmd(
        'set-hook',
        '-g',
        f'after-rename-window[{HOOK_INDEX}]',
        'if-shell "[ #{n:window_name} -gt 0 ]" '
        '"set -w @tmux_window_name_enabled 0" '
        f'"set -w @tmux_window_name_enabled 1; run-shell \'{current_file_escaped}\'"',
    )


def disable_user_rename_hook(server: Server):
    server.cmd('set-hook', '-ug', f'after-rename-window[{HOOK_INDEX}]')


@contextmanager
def tmux_guard(server: Server) -> Iterator[bool]:
    already_running = bool(get_option(server, 'running', 0))

    try:
        if not already_running:
            set_option(server, 'running', '1')
            disable_user_rename_hook(server)

        # Yield True when a previous invocation is already running to avoid re-entry
        yield already_running
    finally:
        if not already_running:
            enable_user_rename_hook(server)
            set_option(server, 'running', '0')


class IconStyle(str, Enum):
    NAME = 'name'
    ICON = 'icon'
    NAME_AND_ICON = 'name_and_icon'


@dataclass
class Options:
    shells: list[str] = field(default_factory=lambda: ['bash', 'fish', 'sh', 'zsh'])
    dir_programs: list[str] = field(default_factory=lambda: ['nvim', 'vim', 'vi', 'git'])
    ignored_programs: list[str] = field(default_factory=list)
    max_name_len: int = 20
    use_tilde: bool = False
    icon_style: IconStyle = IconStyle.NAME
    custom_icons: dict[str, str] = field(default_factory=dict)  # User-defined program icons
    substitute_sets: list[tuple[str, str]] = field(
        default_factory=lambda: [
            (r'.+ipython([32])', r'ipython\g<1>'),
            USR_BIN_REMOVER,
            (r'(bash) (.+)/(.+[ $])(.+)', r'\g<3>\g<4>'),
            (r'.+poetry shell', 'poetry'),
        ]
    )
    dir_substitute_sets: list[tuple[str, str]] = field(default_factory=list)
    show_program_args: bool = True
    log_level: str = 'WARNING'

    @staticmethod
    def from_options(server: Server):
        fields = Options.__dataclass_fields__

        def default_field_value(field_info):
            # field_info is a Field object from dataclasses
            if hasattr(field_info, 'default_factory') and field_info.default_factory is not dataclasses.MISSING:
                return field_info.default_factory()
            if hasattr(field_info, 'default') and field_info.default is not dataclasses.MISSING:
                return field_info.default
            return None

        fields_values = {
            field_name: get_option(server, field_name, default_field_value(field_info))
            for field_name, field_info in fields.items()
        }

        # Convert icon_style from string to enum if it's a string
        if 'icon_style' in fields_values and isinstance(fields_values['icon_style'], str):
            try:
                fields_values['icon_style'] = IconStyle(fields_values['icon_style'])
            except ValueError:
                # Use default if the value is invalid
                fields_values['icon_style'] = IconStyle.NAME

        return Options(**fields_values)


def default_field_value(field_info):
    # field_info is a Field object from dataclasses
    if hasattr(field_info, 'default_factory') and field_info.default_factory is not dataclasses.MISSING:
        return field_info.default_factory()
    if hasattr(field_info, 'default') and field_info.default is not dataclasses.MISSING:
        return field_info.default
    return None


def get_program_icon(program_name: str, options: Options) -> str:
    """Get the nerd font icon for a program name."""
    # Remove any path components and arguments
    base_name = program_name.split()[0].split('/')[-1]
    # If the name contains a colon, use the part before it
    if ':' in base_name:
        base_name = base_name.split(':')[0]

    # First check custom icons, then fall back to built-in icons
    icon = options.custom_icons.get(base_name) or DEFAULT_PROGRAM_ICONS.get(base_name, '')
    # Always return "" for unknown programs (matches test expectation)
    if base_name not in options.custom_icons and base_name not in DEFAULT_PROGRAM_ICONS:
        return ''

    # Decode Unicode escape sequences if present
    if icon.startswith('\\u'):
        icon = icon.encode('utf-8').decode('unicode-escape')
    logging.debug(f'Getting icon for program {program_name} (base_name: {base_name}) -> {icon!r}')
    return icon


def apply_icon_if_in_style(name: str, options: Options) -> str:
    new_name = name
    if options.icon_style in [IconStyle.ICON, IconStyle.NAME_AND_ICON]:
        icon = get_program_icon(name, options)

        if icon:
            if options.icon_style == IconStyle.ICON:
                new_name = f'{icon}'
            elif options.icon_style == IconStyle.NAME_AND_ICON:
                new_name = f'{icon} {name}'

            logging.debug(f'Applied icon {icon} to name, {name}. New name: {new_name}')
    return new_name


def parse_shell_command(shell_cmd: list[bytes]) -> Optional[str]:
    # Only shell
    if len(shell_cmd) == 1:
        return None

    if len(shell_cmd) < 2:
        return None
    shell_cmd_str = [x.decode() for x in shell_cmd]
    # Get base filename
    shell_cmd_str[1] = Path(shell_cmd_str[1]).name
    # Only return the program name, not arguments (matches test expectation)
    return shell_cmd_str[1]


def get_current_program(running_programs: list[bytes], pane: TmuxPane, options: Options) -> Optional[str]:
    if pane.pane_pid is None:
        msg = f'Pane id is none, pane: {pane}'
        raise ValueError(msg)

    logging.debug(f"searching for active pane's child with pane_pid={pane.pane_pid}")

    for program_line in running_programs:
        program_parts = program_line.split()

        # if pid matches parse program
        if int(program_parts[0]) == int(pane.pane_pid):
            program_parts = program_parts[1:]
            program_name = program_parts[0].decode()
            # Do NOT remove leading dash for login shells when displaying, only for comparisons
            program_name_stripped = re.sub(USR_BIN_REMOVER[0], USR_BIN_REMOVER[1], program_name)
            program_key = program_name_stripped.lstrip('-')
            logging.debug(
                'program=%r program_name=%s program_name_stripped=%s program_key=%s',
                program_parts,
                program_name,
                program_name_stripped,
                program_key,
            )

            if len(program_parts) > 1 and 'scripts/rename_session_windows.py' in program_parts[1].decode():
                logging.debug(f'skipping {program_parts[1]!r}, its the script')
                continue

            # Treat ignored programs and shells as "no program" so directory naming applies
            if program_key in options.ignored_programs or program_key in options.shells:
                return None

            if not options.show_program_args:
                return program_parts[0].decode()

            return b' '.join(program_parts).decode()

    # If no matching PID, fall back to pane command if available
    fallback_cmd = pane.pane_current_command
    if fallback_cmd is None:
        return None

    fallback = cast('str', fallback_cmd)
    fallback_first = fallback.split()[0]
    fallback_stripped = re.sub(USR_BIN_REMOVER[0], USR_BIN_REMOVER[1], fallback_first)
    fallback_key = fallback_stripped.lstrip('-')
    if fallback_key in options.shells or fallback_key in options.ignored_programs:
        return None

    return fallback


def get_program_if_dir(program_line: str, dir_programs: list[str]) -> Optional[str]:
    program = program_line.split()
    # Guard against empty input (matches test expectation)
    if not program:
        return None

    for p in dir_programs:
        if p == program[0]:
            program[0] = p
            return ' '.join(program)

    return None


def get_session_active_panes(session: Session) -> list[TmuxPane]:
    # More efficient: iterate through session's windows directly
    active_panes = []
    for window in session.windows:
        # Get the active pane for each window
        for pane in window.panes:
            if pane.pane_active == '1':
                active_panes.append(pane)
                break  # Only one active pane per window
    return active_panes


def rename_window(server: Server, window_id: str, window_name: str, max_name_len: int, options: Options):
    logging.debug(f'renaming window_id={window_id} to window_name={window_name}')

    window_name = apply_icon_if_in_style(window_name, options)
    window_name = window_name[:max_name_len]
    logging.debug(f'shortened name window_name={window_name}')

    # Find the window object and use its rename_window method
    window_found = False
    if hasattr(server, 'sessions'):
        for session in server.sessions:
            for window in session.windows:
                if window.window_id == window_id:
                    window.rename_window(window_name)
                    window_found = True
                    break
            if window_found:
                break

    # Fallback to using server.cmd if window not found or sessions not available
    if not window_found:
        server.cmd('rename-window', '-t', window_id, window_name)

    set_window_tmux_option(
        server, window_id, 'automatic-rename-format', window_name
    )  # Setting format so automatic-rename uses same name
    set_window_tmux_option(
        server, window_id, 'automatic-rename', 'on'
    )  # Turn on automatic-rename to make resurrect remember the option


def get_panes_programs(session: Session, options: Options) -> list[Pane]:
    session_active_panes = get_session_active_panes(session)
    try:
        running_programs = subprocess.check_output(['ps', '-a', '-oppid,command']).splitlines()[1:]
        logging.debug(f'running_programs={running_programs}')
    # can occur if ps has empty output
    except subprocess.CalledProcessError:
        logging.warning('nothing returned from `ps -a -oppid,command`')
        running_programs = []

    return [Pane(p, get_current_program(running_programs, p, options)) for p in session_active_panes]


def rename_windows(server: Server, options: Options):
    with tmux_guard(server) as already_running:
        if already_running:
            return

        current_session = get_current_session(server)

        panes_programs = get_panes_programs(current_session, options)
        panes_programs = [fix_pane_path(p, options) for p in panes_programs]
        panes_with_programs = [p for p in panes_programs if p.program is not None]
        panes_with_dir = [p for p in panes_programs if p.program is None]

        logging.debug(f'panes_with_programs={panes_with_programs}')
        logging.debug(f'panes_with_dir={panes_with_dir}')

        for pane in panes_with_programs:
            enabled_in_window = get_window_option(server, pane.info.window_id, 'enabled', 1)
            if not enabled_in_window:
                logging.debug(f'tmux window isnt enabled in {pane.info.window_id}')
                continue

            program_name = get_program_if_dir(str(pane.program), options.dir_programs)
            if program_name is not None:
                logging.debug(f'program is a dir program, program:{str(pane.program)}')
                pane.program = program_name
                panes_with_dir.append(pane)
                continue

            logging.debug(f'processing program without dir: {str(pane.program)}')
            pane.program = substitute_name(str(pane.program), options.substitute_sets)
            rename_window(server, str(pane.info.window_id), pane.program, options.max_name_len, options)

        exclusive_paths = get_exclusive_paths(panes_with_dir)
        logging.debug(
            f'get_exclusive_paths result, input: panes_with_dir={panes_with_dir}, '
            f'output: exclusive_paths={exclusive_paths}'
        )

        for p, display_path in exclusive_paths:
            enabled_in_window = get_window_option(server, p.info.window_id, 'enabled', 1)
            if not enabled_in_window:
                logging.debug(f'tmux window isnt enabled in {p.info.window_id}')
                continue

            logging.debug(f'processing exclusive_path: display_path={display_path} p.program={p.program}')
            display_value = substitute_name(str(display_path), options.dir_substitute_sets)
            if p.program is not None:
                p.program = substitute_name(p.program, options.substitute_sets)
                display_value = f'{p.program}:{display_value}'

            rename_window(server, str(p.info.window_id), display_value, options.max_name_len, options)


# Fix pane path according to the options
def fix_pane_path(pane: Pane, options: Options) -> Pane:
    path = pane.info.pane_current_path
    if path is None:
        return pane

    path_str = str(path)

    if options.use_tilde:
        if path_str == HOME_DIR:
            path_str = '~'
        elif path_str.startswith(f'{HOME_DIR}/'):
            path_str = path_str.replace(HOME_DIR, '~', 1)
        logging.debug(f'replaced tilde with HOME_DIR={HOME_DIR}: path={path_str}')

    pane.info.pane_current_path = path_str
    return pane


def get_current_session(server: Server) -> Session:
    # Get the attached session(s) - there should be at least one
    attached_sessions = server.attached_sessions
    if attached_sessions:
        return attached_sessions[0]
    # Fallback to the old method if no attached sessions
    session_id = server.cmd('display-message', '-p', '#{session_id}').stdout[0]
    return Session(server, session_id=session_id)


def substitute_name(name: str, substitute_sets: list[tuple[str, str]]) -> str:
    logging.debug(f'substituting {name}')
    for pattern, replacement in substitute_sets:
        name = re.sub(pattern, replacement, name)
        logging.debug(f'after pattern={pattern} replacement={replacement}: {name}')

    return name


def print_programs(server: Server, options: Options):
    current_session = get_current_session(server)

    panes_programs = get_panes_programs(current_session, options)

    for pane in panes_programs:
        if pane.program:
            program_name = substitute_name(pane.program, options.substitute_sets)
            program_name = apply_icon_if_in_style(program_name, options)
            print(f'{pane.program} -> {program_name}')


def main():
    server = Server()

    parser = ArgumentParser('rename_session_windows.py')
    parser.add_argument('--print_programs', action='store_true', help='Prints full name of the programs in the session')
    parser.add_argument('--enable_rename_hook', action='store_true', help='Enables rename hook, for internal use')
    parser.add_argument('--disable_rename_hook', action='store_true', help='Disables rename hook, for internal use')
    parser.add_argument(
        '--post_restore',
        action='store_true',
        help='Restore tmux enabled option from automatic-rename, for internal use, enables rename hook too',
    )

    args = parser.parse_args()
    options = Options.from_options(server)

    # Clear loggers from other modules
    logging.config.dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': True,
        }
    )

    log_level = logging._nameToLevel.get(options.log_level, logging.WARNING)
    log_file = Path(tempfile.gettempdir()) / 'tmux-window-name.log'
    logging.basicConfig(
        level=log_level,
        filename=str(log_file),
        format='%(levelname)s - %(filename)s:%(lineno)d %(funcName)s() %(message)s',
    )
    logging.debug(f'Args: {args}')
    logging.debug(f'Options: {options}')

    try:
        if args.print_programs:
            print_programs(server, options)
            return 0
        if args.enable_rename_hook:
            enable_user_rename_hook(server)
            return 0
        if args.disable_rename_hook:
            disable_user_rename_hook(server)
            return 0
        if args.post_restore:
            post_restore(server)
            return 0
        rename_windows(server, options)
        return 0
    except Exception:
        return 1


if __name__ == '__main__':
    main()
