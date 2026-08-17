"""
ADAPT — Custom Exception Classes

Structured exceptions for clear error handling across the application.
Every exception carries an error code and HTTP status for the API layer.
"""

from typing import Any, Dict, Optional


class ADAPTError(Exception):
    """Base exception for all ADAPT errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# ---- Authentication & Authorization ----

class AuthenticationError(ADAPTError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR", 401)


class AuthorizationError(ADAPTError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "FORBIDDEN", 403)


# ---- Resource Errors ----

class NotFoundError(ADAPTError):
    def __init__(self, resource: str, resource_id: str = ""):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} with id '{resource_id}' not found"
        super().__init__(msg, "NOT_FOUND", 404)


class DuplicateError(ADAPTError):
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            f"{resource} with {field}='{value}' already exists",
            "DUPLICATE",
            409,
        )


# ---- Validation Errors ----

class ValidationError(ADAPTError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", 422, details)


# ---- File Errors ----

class FileUploadError(ADAPTError):
    def __init__(self, message: str = "File upload failed"):
        super().__init__(message, "FILE_UPLOAD_ERROR", 400)


class FileParsingError(ADAPTError):
    def __init__(self, message: str = "Failed to parse file"):
        super().__init__(message, "FILE_PARSING_ERROR", 422)


# ---- AI / LLM Errors ----

class LLMError(ADAPTError):
    def __init__(self, message: str = "LLM request failed"):
        super().__init__(message, "LLM_ERROR", 502)


class LLMOutputError(ADAPTError):
    def __init__(self, message: str = "LLM returned invalid output"):
        super().__init__(message, "LLM_OUTPUT_ERROR", 422)


class EmbeddingError(ADAPTError):
    def __init__(self, message: str = "Embedding generation failed"):
        super().__init__(message, "EMBEDDING_ERROR", 502)


# ---- RAG Errors ----

class RetrievalError(ADAPTError):
    def __init__(self, message: str = "Document retrieval failed"):
        super().__init__(message, "RETRIEVAL_ERROR", 500)


# ---- Document Generation Errors ----

class DocumentGenerationError(ADAPTError):
    def __init__(self, message: str = "Document generation failed"):
        super().__init__(message, "DOCGEN_ERROR", 500)


# ---- Task Errors ----

class TaskError(ADAPTError):
    def __init__(self, message: str = "Background task failed"):
        super().__init__(message, "TASK_ERROR", 500)
