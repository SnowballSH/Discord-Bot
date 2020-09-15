class Error(Exception):
    """The bot custom base exception
    Ideally speaking, this could be caught to handle any exceptions thrown from this library.
    """

    def __init__(self, message: str):
        self.message = message


class InvalidArgument(Error):
    """Exception that's thrown when an argument to a function
    is invalid some way (e.g. wrong value or wrong type)."""

    def __init__(self, message: str):
        self.message = message


class CannotEmbed(Error):
    """Exception that's thrown when the bot is missing permissions
    to send embeds somewhere."""

    def __init__(self, message: str):
        self.message = message


class ToBeIgnored(Error):
    """Exception that's thrown just to exit a "something" """

    pass
