"""Exceptions related to storage operations."""


class ConflictError(Exception):
    """Raised when putting a resource that already exists in the storage."""


class NotFoundError(Exception):
    """Raised when getting a resource that does not exist in the storage."""
