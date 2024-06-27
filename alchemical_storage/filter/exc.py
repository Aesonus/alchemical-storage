"""Define filter and order_by exceptions."""


class OrderByException(Exception):
    """Raised when an order_by query parameter is invalid."""


class NullFilterException(ValueError):
    """Raised when a null filter query parameter is invalid."""
