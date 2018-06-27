"""Exceptions thrown by sparkbot"""

class SparkBotError(Exception):
    """Generic exception"""

class CommandNotFound(SparkBotError):
    """Raised when a command is not found for the given request"""