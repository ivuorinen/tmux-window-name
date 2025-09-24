#!/usr/bin/env python3

from typing import Optional

from scripts.path_utils import Pane as PathPane
from scripts.path_utils import get_exclusive_paths
from tests.mocks import Pane as MockPane


def _fake_pane(path: str, program: Optional[str]) -> PathPane:
    # Use the wrapper Pane from path_utils, with a mock Pane as info
    return PathPane(
        info=MockPane(pane_current_path=path, pane_current_command='', pane_pid=1234, pane_active='1'), program=program
    )


def _check(expected: list[tuple[str, Optional[str], str]]):
    """check expected displayed paths

    Args:
        expected (List[Tuple[str, Optional[str], str]]): list of (full_path, program, expected_display)
    E.g:
        _check([
            ('a/dir', 'p1', 'dir'), # Program p1 in a/dir will display dir (will be formated to p1:dir)
            ('b/dir', None, 'b/dir'), # Shell in b/dir will display b/dir
            ('c/dir', None', 'c/dir'), # Shell in c/dir will display c/dir
        ])
    """
    panes = [_fake_pane(full, program) for full, program, _ in expected]
    exclusive_panes = get_exclusive_paths(panes)
    for (_full, _, expected_display), (_, display) in zip(expected, exclusive_panes):
        assert str(display) == expected_display


def test_not_intersect():
    _check(
        [
            ('a/a_dir', None, 'a_dir'),
            ('b/b_dir', None, 'b_dir'),
        ]
    )

    _check(
        [
            ('a', None, 'a'),
            ('b', None, 'b'),
        ]
    )

    _check(
        [
            ('a', None, 'a'),
            ('b', None, 'b'),
            ('c', None, 'c'),
        ]
    )


def test_basic_intersect():
    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
        ]
    )


def test_not_same_length():
    _check(
        [
            ('a/b/dir', None, 'a/b/dir'),
            ('b/dir', None, 'b/dir'),
        ]
    )


def test_deeply_nested_directories():
    _check(
        [
            ('/a/b/c/d/e', None, 'e'),
            ('/a/b/c/d/f', None, 'f'),
            ('/a/b/c/g/h', None, 'h'),
        ]
    )


def test_overlapping_paths():
    _check(
        [
            ('/home/user/project', None, 'project'),
            ('/home/user/project2', None, 'project2'),
            ('/home/user/project/subdir', None, 'subdir'),
        ]
    )


def test_common_prefixes():
    _check(
        [
            ('/src/app', None, 'app'),
            ('/src/api', None, 'api'),
            ('/src/assets', None, 'assets'),
        ]
    )


def test_edge_cases():
    # Empty path list
    panes = []
    exclusive_panes = get_exclusive_paths(panes)
    assert exclusive_panes == []

    # Single path
    _check(
        [
            ('/only/path', None, 'path'),
        ]
    )

    # All identical paths
    _check(
        [
            ('/same/path', None, 'path'),
            ('/same/path', None, 'path'),
            ('/same/path', None, 'path'),
        ]
    )


def test_get_uncommon_path_indexerror_branch():
    # This covers the branch where IndexError is raised in get_uncommon_path
    from pathlib import Path

    from scripts.path_utils import get_uncommon_path

    # a shorter than b, so IndexError will be triggered
    a = Path('a')
    b = Path('a/b/c')
    uncommon_a, uncommon_b = get_uncommon_path(a, b)
    assert uncommon_a == Path('a')
    assert uncommon_b == Path('c')


def test_mixed_programs_and_shells():
    _check(
        [
            ('/projects/app', 'python', 'app'),
            ('/projects/app', None, 'app'),
            ('/projects/api', 'node', 'api'),
            ('/projects/api', None, 'api'),
        ]
    )


def test_overlap_same_leaf():
    _check(
        [
            ('/a/test', None, 'a/test'),
            ('/b/test', None, 'b/test'),
        ]
    )


def test_reacurring_dir():
    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
            ('c/dir', None, 'c/dir'),
        ]
    )


def test_same_path_twice_dir():
    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
        ]
    )

    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
            ('a/dir', None, 'a/dir'),
        ]
    )

    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
            ('b/dir', None, 'b/dir'),
            ('a/dir', None, 'a/dir'),
        ]
    )

    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
        ]
    )

    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
            ('c/dir', None, 'c/dir'),
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
            ('c/dir', None, 'c/dir'),
        ]
    )


def test_mixed_basic():
    _check(
        [
            ('a/dir', None, 'a/dir'),
            ('b/dir', None, 'b/dir'),
            ('c/c_dir', None, 'c_dir'),
        ]
    )

    _check(
        [
            ('a/b/c/d', None, 'a/b/c/d'),
            ('b/c/d', None, 'b/c/d'),
            ('dirrr', None, 'dirrr'),
        ]
    )


def test_program_basic():
    _check(
        [
            ('a/dir', 'p1', 'dir'),
            ('b/dir', None, 'dir'),
        ]
    )

    _check(
        [
            ('a/dir', 'p1', 'dir'),
            ('b/dir', 'p2', 'dir'),
        ]
    )

    _check(
        [
            ('a/dir', 'p1', 'a/dir'),
            ('b/dir', 'p1', 'b/dir'),
        ]
    )

    _check(
        [
            ('a/dir', 'p1', 'dir'),
            ('b/dir', 'p2', 'dir'),
        ]
    )


def test_program_mixed():
    _check(
        [
            ('a/dir', 'p1', 'dir'),
            ('b/dir', None, 'dir'),
            ('c/dir', 'p2', 'dir'),
        ]
    )

    _check(
        [
            ('a/dir', 'p1', 'dir'),
            ('b/dir', None, 'dir'),
            ('a/dir', 'p1', 'dir'),
            ('c/dir', 'p2', 'dir'),
        ]
    )

    _check(
        [
            ('a/dir', 'p1', 'a/dir'),
            ('b/dir', 'p1', 'b/dir'),
            ('a/dir', 'p1', 'a/dir'),
            ('c/dir', 'p2', 'dir'),
        ]
    )
