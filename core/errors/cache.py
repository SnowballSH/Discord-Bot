from core.errors import CommandError, EventError, InvalidArgument
from typing import Union, List


class Cache(object):
    """Cache for use in interactive error handling"""

    def __init__(self, limit: int):
        self.__cache = {}

        self.__limit = limit

    @property
    def limit(self):
        return self.__limit

    @limit.setter
    def limit(self, value: Union[int, None]):
        if value is not None and not isinstance(value, int):
            raise InvalidArgument("Excepted Union[int, None], got {}".format(value))

        if isinstance(value, int):
            if value < 0:
                self.__limit = None
            elif value == 0:
                raise InvalidArgument(
                    f"Cache limit must be positive or (None / -1) for no limit."
                )
            else:
                self.__limit = value

        else:
            self.__limit = None

    def __ensure_limit(self) -> None:
        """Make sure the cache is below `self.limit` objects."""
        if self.__limit is not None:
            while len(self.__cache) > self.limit:
                obj = min(self.__cache, key=lambda e: e.time)
                del self.__cache[obj.id]

    def append(self, error: Union[CommandError, EventError]) -> None:
        if not isinstance(error, (CommandError, EventError)):
            raise InvalidArgument(
                f"Expected `Union[CommandError, EventError]`, got {type(error).__name__}"
            )

        self.__cache[error.id] = error
        self.__ensure_limit()

    def get(
        self, *, id: str = None, key=None
    ) -> Union[
        Union[CommandError, EventError], List[Union[CommandError, EventError]], None
    ]:
        """Returns a list of objects where `id` and `key` match.
        If neither a id or key is provided remove the latest error.
        If only a id is provided, return the object with the matching id.
            If there is no error with that id, return None.
        If no errors are present, return None.
        """
        if len(self.__cache) == 0:
            return None

        if (id, key) == (None, None):
            return max(self.__cache, key=lambda e: e.time)

        elif (id, key) == (None, not None):
            return [e for e in self.__cache.values() if key(e)]

        elif (id, key) == (not None, None):
            return self.__cache.get(id, None)

        else:
            raise InvalidArgument(
                "Only one argument should be provided for this method."
            )

    @property
    def all(self) -> List[Union[CommandError, EventError]]:
        return list(self.__cache.items())

    def __len__(self):
        return len(self.__cache)

    def __repr__(self):
        return "<ErrorCache limit={limit} size={size}>".format(
            limit=self.limit, size=len(self)
        )
