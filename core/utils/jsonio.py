from typing import Any
import asyncio
import random
import string
import json
import os


class JsonIO(object):
    """A config manager for local configs stored in `.json` files"""

    def __init__(self, name: str):
        self.name = name

        self.loop = asyncio.get_event_loop()
        self.lock = asyncio.Lock()
        self.__data = {}

        self.loop.create_task(self.load())

    async def load(self) -> None:
        """Load the config stored in """
        async with self.lock:
            try:
                with open(self.name, "r") as f:
                    self.__data = json.load(f, encoding="utf-8")
            except FileNotFoundError:
                pass

    @staticmethod
    def _temp_name() -> str:
        """Generate a random string"""
        return "".join(random.choice(string.ascii_lowercase) for _ in range(10))

    async def save(self) -> None:
        """Save the cached config -> `self.__data`,
        Create a temporary file first to avoid files not completely writing."""

        async with self.lock:
            temp_name = f"{self.name}-{self._temp_name()}.tmp"
            with open(temp_name, "w", encoding="utf-8") as tmp:
                json.dump(self.__data.copy(), tmp, ensure_ascii=True, indent=4)

            os.replace(temp_name, self.name)

    def get(self, key, *args) -> Any:
        """Retrieve a item from the config"""
        return self.__data.get(str(key), *args)

    async def put(self, key, value) -> None:
        """Edit or input a config item."""
        self.__data[str(key)] = value
        await self.save()

    async def remove(self, key) -> None:
        """Remove an item from the config"""
        del self.__data[str(key)]
        await self.save()

    def __contains__(self, item) -> bool:
        return str(item) in self.__data

    def __getitem__(self, item):
        return self.__data.__getitem__(item)

    def __len__(self) -> int:
        return len(self.__data)

    @property
    def all(self) -> dict:
        return self.__data
