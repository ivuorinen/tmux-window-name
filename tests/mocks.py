#!/usr/bin/env python3

from unittest.mock import Mock


class Pane:
    """
    1:1 mock of libtmux.Pane
    """

    def __init__(
        self,
        pane_id='1',
        pane_pid=1234,
        pane_active='1',
        pane_current_path='/home/user',
        pane_current_command='bash',
        window_id='@1',
        window=None,
        session=None,
        index=0,
    ):
        self.pane_id = pane_id
        self.pane_pid = pane_pid
        self.pane_active = pane_active
        self.pane_current_path = pane_current_path
        self.pane_current_command = pane_current_command
        self.window_id = window_id
        self.window = window
        self.session = session
        self.index = index

    def __getitem__(self, key):
        # libtmux allows dict-like access for some attributes
        return getattr(self, key)

    def __repr__(self):
        return f'<Pane id={self.pane_id} pid={self.pane_pid} active={self.pane_active} path={self.pane_current_path}>'


class Window:
    """
    1:1 mock of libtmux.Window
    """

    def __init__(self, window_id='@1', window_name='test', session=None, index=0):
        self.window_id = window_id
        self.name = window_name
        self.panes = []
        self.session = session
        self.index = index

    def rename_window(self, name):
        self.name = name

    def select_window(self):
        pass

    def __getitem__(self, key):
        # libtmux allows dict-like access for some attributes
        if key == 'window_id':
            return self.window_id
        if key == 'window_name':
            return self.name
        return getattr(self, key)

    def __iter__(self):
        return iter(self.panes)

    def __repr__(self):
        return f'<Window id={self.window_id} name={self.name}>'


class Session:
    """
    1:1 mock of libtmux.Session
    """

    def __init__(self, session_id='$1', session_name='test_session', index=0):
        self.session_id = session_id
        self.name = session_name
        self.windows = []
        self.index = index

    def __getitem__(self, key):
        if key == 'session_id':
            return self.session_id
        if key == 'session_name':
            return self.name
        return getattr(self, key)

    def __iter__(self):
        return iter(self.windows)

    @property
    def attached_pane(self):
        for window in self.windows:
            for pane in window.panes:
                if pane.pane_active == '1':
                    return pane
        return None

    def __repr__(self):
        return f'<Session id={self.session_id} name={self.name}>'


class Server:
    """
    1:1 mock of libtmux.Server
    """

    def __init__(self):
        self.cmd = Mock()
        self.sessions = []
        self.windows = []
        self._options = {}

    def list_sessions(self):
        return self.sessions

    def list_windows(self):
        return self.windows

    @property
    def attached_sessions(self):
        return self.sessions

    def __getitem__(self, key):
        return getattr(self, key)

    @property
    def socket_name(self):
        # Mimic libtmux.Server attribute for compatibility in tests
        # Use tempfile.mkstemp to avoid Ruff S306 warning
        import os
        import tempfile

        fd, path = tempfile.mkstemp(prefix='tmux-mock-socket-')
        os.close(fd)
        return path

    def __repr__(self):
        return '<Server>'
