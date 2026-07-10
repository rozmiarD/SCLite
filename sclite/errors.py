from __future__ import annotations


class SCLiteError(ValueError):
    """Base class for expected SCLite input and verification failures."""

    default_code = 'sclite_error'

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or self.default_code


class SCLiteValidationError(SCLiteError):
    """Base class for invalid caller-controlled data."""

    default_code = 'validation_failed'


class SCLiteSchemaValidationError(SCLiteValidationError):
    """Raised when an artifact does not satisfy its selected schema."""

    default_code = 'schema_validation_failed'
