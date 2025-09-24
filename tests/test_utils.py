#!/usr/bin/env python3
"""Test utilities for tmux-window-name tests."""

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


@contextmanager
def create_test_directories(paths: Optional[list[str]] = None) -> Iterator[Path]:
    """
    Context manager that creates temporary test directories.

    Args:
        paths: List of relative paths to create. If None, creates default test paths.

    Yields:
        Path: The temporary base directory containing all test directories.

    Example:
        with create_test_directories(['a/dir', 'b/dir']) as base_dir:
            assert (base_dir / 'a' / 'dir').exists()
            assert (base_dir / 'b' / 'dir').exists()
    """
    # Default paths from the original shell script
    default_paths = [
        'test_intersect/dir',
        'test_intersect/a/b/dir',
        'test_intersect/b/a/dir',
        'test_intersect/a/dir',
        'test_intersect/b/dir',
        'test_intersect/a/b/2',
        'test_intersect/a/b/3',
        'test_intersect/a/b/c',
        'test_intersect/e/a/b/c',
    ]

    paths_to_create = paths if paths is not None else default_paths

    with tempfile.TemporaryDirectory(prefix='tmux_window_name_test_') as temp_dir:
        base_path = Path(temp_dir)

        # Create all requested directories
        for path in paths_to_create:
            dir_path = base_path / path
            dir_path.mkdir(parents=True, exist_ok=True)

        yield base_path


def create_test_directory_structure(base_path: Path, paths: list[str]) -> None:
    """
    Create a directory structure for testing.

    Args:
        base_path: Base directory where to create the structure.
        paths: List of relative paths to create.
    """
    for path in paths:
        dir_path = base_path / path
        dir_path.mkdir(parents=True, exist_ok=True)


@contextmanager
def directory_fixture(structure: dict) -> Iterator[Path]:
    """
    Context manager that creates a test directory structure from a dictionary.

    Args:
        structure: Dictionary describing the directory structure.
                  Keys are directory names, values are either None for leaf dirs
                  or nested dictionaries for subdirectories.

    Yields:
        Path: The temporary base directory.

    Example:
        structure = {
            'a': {
                'dir': None,
                'b': {
                    'dir': None,
                    '2': None,
                    '3': None,
                    'c': None
                }
            },
            'b': {
                'dir': None,
                'a': {
                    'dir': None
                }
            },
            'e': {
                'a': {
                    'b': {
                        'c': None
                    }
                }
            }
        }

        with directory_fixture(structure) as base_dir:
            assert (base_dir / 'a' / 'dir').exists()
            assert (base_dir / 'a' / 'b' / 'c').exists()
    """
    with tempfile.TemporaryDirectory(prefix='tmux_window_name_test_') as temp_dir:
        base_path = Path(temp_dir)

        def create_structure(parent: Path, struct: dict) -> None:
            for name, substructure in struct.items():
                path = parent / name
                path.mkdir(exist_ok=True)
                if isinstance(substructure, dict):
                    create_structure(path, substructure)

        if structure:
            create_structure(base_path, structure)

        yield base_path


def assert_paths_exist(base_path: Path, paths: list[str]) -> None:
    """
    Assert that all specified paths exist under the base path.

    Args:
        base_path: Base directory to check under.
        paths: List of relative paths that should exist.

    Raises:
        AssertionError: If any path doesn't exist.
    """
    for path in paths:
        full_path = base_path / path
        assert full_path.exists(), f'Path {full_path} does not exist'
