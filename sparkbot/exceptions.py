"""Exceptions thrown by sparkbot"""

class SparkBotError(Exception):
    """Generic exception"""

class CommandNotFound(SparkBotError):
    """Raised when a command is not found for the given request"""

class CommandSetupError(SparkBotError):
    """Raised when it is impossible to add the specified command for some reason.
    
    For example, this is raised when:
    
    * Attempting to add more than one fallback command
    * Attempting to add a non-fallback command with no command strings
    """