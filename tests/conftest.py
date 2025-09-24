#!/usr/bin/env python3

import contextlib
import uuid
from pathlib import Path

import pytest
from libtmux import exc


@pytest.fixture(scope='session', autouse=True)
def set_tmux_tmpdir():
    """Point tmux at a short, writable socket directory."""
    tmux_tmpdir = Path.cwd() / '.tmux_tmp'
    tmux_tmpdir.mkdir(parents=True, exist_ok=True)
    mp = pytest.MonkeyPatch()
    mp.setenv('TMUX_TMPDIR', str(tmux_tmpdir))
    # tmux also respects XDG_RUNTIME_DIR; keep it short to avoid long socket paths
    mp.setenv('XDG_RUNTIME_DIR', str(tmux_tmpdir))
    try:
        yield str(tmux_tmpdir)
    finally:
        mp.undo()


@pytest.fixture
def tmux_session(server):
    """Provide a temporary tmux session or skip if tmux cannot start."""
    session_name = f'tmuxwn_{uuid.uuid4().hex[:8]}'
    try:
        session = server.new_session(session_name=session_name, attach=False)
    except exc.LibTmuxException as error:
        pytest.skip(f'tmux session unavailable: {error}')
    else:
        try:
            yield session
        finally:
            with contextlib.suppress(exc.LibTmuxException):
                server.kill_session(session_name)


def pytest_configure(config: pytest.Config) -> None:
    pluginmanager = config.pluginmanager
    if not (pluginmanager.has_plugin('libtmux') or pluginmanager.has_plugin('libtmux.pytest_plugin')):
        pluginmanager.import_plugin('libtmux.pytest_plugin')
