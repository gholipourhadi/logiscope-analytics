"""Typed exceptions raised at LogiScope service boundaries."""


class LogiScopeError(Exception):
    """Base class for expected platform errors."""


class DatasetValidationError(LogiScopeError):
    """Raised when shipment data violates the canonical contract."""


class InsufficientDataError(LogiScopeError):
    """Raised when an analytical model cannot be fitted responsibly."""


class InvalidScenarioError(LogiScopeError):
    """Raised for impossible or unsafe planning assumptions."""
