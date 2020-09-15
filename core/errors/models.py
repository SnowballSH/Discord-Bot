"""Custom Error objects to use in error handling."""

import traceback
import datetime
import uuid
import sys

from core import utils


class BaseError(object):
    """Class for use in error handling.
    Base class for command / event errors."""

    def __init__(
        self, error: BaseException, time: datetime.datetime = datetime.datetime.utcnow()
    ):
        self.error = error
        self.type = type(error)
        self.traceback = error.__traceback__

        self.time = time

        self.original = getattr(error, "original", error)
        self.id = str(uuid.uuid4()).split("-")[0]

    @property
    def fmt(self):
        return "".join(
            traceback.format_exception(self.type, self.error, self.traceback)
        )

    def fmt_lenght(self, lenght: int) -> str:
        """Returns the formatted error with max length of `length`"""
        return utils.to_pages(self.fmt, max_page_size=lenght, by_lines=True)[0]

    def print(self) -> None:
        traceback.print_exception(
            self.type, self.error, self.traceback, file=sys.stderr
        )


class CommandError(BaseError):
    """A instance of this class is created when a command-error is raised.
    Used in error handling."""

    def __init__(self, ctx, error: BaseException):
        super().__init__(error=error, time=ctx.message.created_at)
        self.ctx = self.context = ctx

    @property
    def fmt(self) -> str:
        return (
            f"Ignored exception in command {self.context.command}:" f"\n{super().fmt}"
        )


class EventError(BaseError):
    """A instance of this class is created when a event-error is raised.
    Used in error handling."""

    def __init__(
        self,
        event: str,
        error: BaseException,
        time: datetime.datetime = datetime.datetime.utcnow(),
        *args,
        **kwargs,
    ):
        super().__init__(error=error, time=time)
        self.event = event
        self.args: tuple = args
        self.kwargs: dict = kwargs

    @property
    def fmt(self) -> str:
        return f"Ignored exception in event {self.event}:" f"\n{super().fmt}"
