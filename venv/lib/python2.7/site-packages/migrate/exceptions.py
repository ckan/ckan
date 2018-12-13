"""
   Provide exception classes for :mod:`migrate`
"""


class Error(Exception):
    """Error base class."""


class ApiError(Error):
    """Base class for API errors."""


class KnownError(ApiError):
    """A known error condition."""


class UsageError(ApiError):
    """A known error condition where help should be displayed."""


class ControlledSchemaError(Error):
    """Base class for controlled schema errors."""


class InvalidVersionError(ControlledSchemaError):
    """Invalid version number."""


class DatabaseNotControlledError(ControlledSchemaError):
    """Database should be under version control, but it's not."""


class DatabaseAlreadyControlledError(ControlledSchemaError):
    """Database shouldn't be under version control, but it is"""


class WrongRepositoryError(ControlledSchemaError):
    """This database is under version control by another repository."""


class NoSuchTableError(ControlledSchemaError):
    """The table does not exist."""


class PathError(Error):
    """Base class for path errors."""


class PathNotFoundError(PathError):
    """A path with no file was required; found a file."""


class PathFoundError(PathError):
    """A path with a file was required; found no file."""


class RepositoryError(Error):
    """Base class for repository errors."""


class InvalidRepositoryError(RepositoryError):
    """Invalid repository error."""


class ScriptError(Error):
    """Base class for script errors."""


class InvalidScriptError(ScriptError):
    """Invalid script error."""


class InvalidVersionError(Error):
    """Invalid version error."""

# migrate.changeset

class NotSupportedError(Error):
    """Not supported error"""


class InvalidConstraintError(Error):
    """Invalid constraint error"""

class MigrateDeprecationWarning(DeprecationWarning):
    """Warning for deprecated features in Migrate"""
