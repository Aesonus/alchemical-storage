"""The **alchemical_storage** package."""

import importlib
from types import ModuleType

__version__ = "1.1.0-rc.1"


def get_module(import_from: str | ModuleType) -> ModuleType:
    """Get the module from a string or a module.

    Arguments:
        import_from (str | ModuleType): The module to import

    Returns:
        ModuleType: The imported module

    """
    return (
        importlib.import_module(import_from)
        if isinstance(import_from, str)
        else import_from
    )
