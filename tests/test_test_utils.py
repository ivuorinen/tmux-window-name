#!/usr/bin/env python3
"""Tests for test utilities."""

from .test_utils import (
    assert_paths_exist,
    create_test_directories,
    create_test_directory_structure,
    directory_fixture,
)


def test_create_test_directories_default():
    """Test creating default test directories."""
    with create_test_directories() as base_dir:
        # Check that base directory exists
        assert base_dir.exists()
        assert base_dir.is_dir()

        # Check some of the default paths
        assert (base_dir / 'test_intersect' / 'dir').exists()
        assert (base_dir / 'test_intersect' / 'a' / 'b' / 'dir').exists()
        assert (base_dir / 'test_intersect' / 'b' / 'a' / 'dir').exists()
        assert (base_dir / 'test_intersect' / 'e' / 'a' / 'b' / 'c').exists()

    # Verify cleanup - directory should not exist after context
    assert not base_dir.exists()


def test_create_test_directories_custom():
    """Test creating custom test directories."""
    custom_paths = [
        'custom/path/one',
        'custom/path/two',
        'another/deep/nested/dir',
    ]

    with create_test_directories(custom_paths) as base_dir:
        for path in custom_paths:
            assert (base_dir / path).exists()
            assert (base_dir / path).is_dir()

    # Verify cleanup
    assert not base_dir.exists()


def test_create_test_directory_structure():
    """Test creating directory structure from list."""
    with create_test_directories([]) as base_dir:
        paths = ['foo/bar', 'foo/baz', 'qux']
        create_test_directory_structure(base_dir, paths)

        for path in paths:
            assert (base_dir / path).exists()


def test_directory_fixture_function():
    """Test creating directory structure from dictionary."""
    structure = {
        'project': {
            'src': {
                'main.py': None,
                'utils': None,
            },
            'tests': {
                'test_main.py': None,
                'test_utils.py': None,
            },
            'docs': None,
        }
    }

    with directory_fixture(structure) as base_dir:
        assert (base_dir / 'project' / 'src').exists()
        assert (base_dir / 'project' / 'src' / 'main.py').exists()
        assert (base_dir / 'project' / 'src' / 'utils').exists()
        assert (base_dir / 'project' / 'tests').exists()
        assert (base_dir / 'project' / 'tests' / 'test_main.py').exists()
        assert (base_dir / 'project' / 'docs').exists()

    # Verify cleanup
    assert not base_dir.exists()


def test_assert_paths_exist():
    """Test path existence assertion utility."""
    import pytest

    with create_test_directories(['a/b/c', 'd/e/f']) as base_dir:
        # Should pass for existing paths
        assert_paths_exist(base_dir, ['a/b/c', 'd/e/f'])

        # Should raise for non-existing paths
        with pytest.raises(AssertionError, match='does not exist'):
            assert_paths_exist(base_dir, ['non/existent/path'])
