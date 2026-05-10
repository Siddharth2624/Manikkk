"""Custom exception classes for authorization and validation."""

class AuthorizationError(Exception):
    """
    Raised when service-layer authorization fails.
    ALWAYS raise this instead of silent failures or empty results.
    """
    def __init__(self, message: str, code: str = "FORBIDDEN"):
        self.message = message
        self.code = code
        super().__init__(message)

class ResourceNotFoundError(Exception):
    """Raised when a requested resource doesn't exist."""
    def __init__(self, resource_type: str, identifier: str):
        self.message = f"{resource_type} '{identifier}' not found"
        self.code = "NOT_FOUND"
        super().__init__(self.message)

class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        self.code = "VALIDATION_ERROR"
        super().__init__(message)

class FeasibilityError(ValueError):
    """Raised when feasibility analysis detects impossible state."""

    def __init__(self, message: str, report):
        """
        Args:
            message: Human-readable error message
            report: FeasibilityReport with full analysis details
        """
        self.message = message
        self.report = report
        super().__init__(message)
