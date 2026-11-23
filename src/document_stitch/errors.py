"""Exception types raised by the document_stitch library."""


class DocumentStitchError(Exception):
    """Base class for all errors raised by document_stitch."""


class OptionsError(DocumentStitchError):
    """Raised when options are invalid or inconsistent."""


class ConfigError(DocumentStitchError):
    """Raised when a configuration file cannot be read or is invalid."""


class PropertiesError(DocumentStitchError):
    """Raised when a properties file does not provide required information."""


class OrderingError(DocumentStitchError):
    """Raised when the order of the pages cannot be determined."""


class StitchError(DocumentStitchError):
    """Raised when creating the output document fails."""


class PreflightError(DocumentStitchError):
    """Raised when pre-flight checks fail, before any document is stitched.

    Attributes:
        messages: Individual problems that were found.
    """

    def __init__(self, messages: list[str]) -> None:
        """Creates the error.

        Args:
            messages: Individual problems that were found.
        """
        super().__init__("; ".join(messages))
        self.messages = list(messages)
