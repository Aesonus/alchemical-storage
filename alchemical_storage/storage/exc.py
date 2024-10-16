"""Exceptions for the ``alchemical_storage.storage`` package."""


class ConflictError(Exception):
    """Raised when putting a value that already exists in the storage."""


class NotFoundError(Exception):
    """Raised when getting a value that does not exist in the storage."""
