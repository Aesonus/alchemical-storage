"""Test the alchemical_storage package."""

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from pathlib import Path

from alchemical_storage import __version__


def test_version_matches_pyproject_toml():
    """Test that the version matches the pyproject.toml version"""
    pyproject_toml = tomllib.loads(
        Path('pyproject.toml').read_text(encoding='utf-8'))

    assert __version__ == pyproject_toml['tool']['poetry']['version']
