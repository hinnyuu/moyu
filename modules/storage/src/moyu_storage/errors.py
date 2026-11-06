"""Storage errors."""


class StorageError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }