from discord.ext import commands
import discord

from typing import Union, Optional
import asyncio

from core.utils.converters import BoolConverter
from DataBase import Client
from core.errors import *

CHECK, CROSS = "\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"


class Context(commands.Context):
    """Custom Context object to implement some useful features."""

    async def send(
        self,
        content=None,
        *,
        tts=False,
        embed=None,
        file=None,
        files=None,
        delete_after=None,
        nonce=None,
        allowed_mentions=None,
    ) -> discord.Message:
        """Improved handling of missing permissions."""

        destination = self.channel
        if not self.guild:
            return await destination.send(
                content=content,
                tts=tts,
                embed=embed,
                file=file,
                files=files,
                delete_after=delete_after,
            )

        permissions: discord.Permissions = self.guild.me.permissions_in(self.channel)

        if not permissions.send_messages:
            try:
                destination = self.author
                await destination.send(
                    f"I do not have permission to send messages in {self.channel.mention}."
                )
            except discord.Forbidden:
                raise

        if not permissions.embed_links and embed is not None:
            raise CannotEmbed(
                f"I do not have permission to send embeds in this channel."
            )

        if not permissions.attach_files and (file or files):
            files = files or [file]
            for file in files:
                await self.author.send(file=file, delete_after=delete_after)
            await destination.send(
                f"I was missing permission to send files in {self.channel.mention}, check your DM."
            )
            files, file = None, None

        await destination.send(
            content=content,
            tts=tts,
            embed=embed,
            file=file,
            files=files,
            delete_after=delete_after,
        )

    async def send_command_help(self):
        """Shortcut for `ctx.send_help(str(ctx.command))`"""
        return await self.send_help(str(self.command))

    async def em(self, *, delete_after=None, **kwargs) -> discord.Message:
        """Shortcut to send a embed."""
        if not self.guild.me.permissions_in(self.channel).embed_links:
            raise CannotEmbed(
                f"I do not have permission to send embeds in this channel."
            )

        return await self.send(embed=self.bot.em(**kwargs), delete_after=delete_after)

    async def cleanup(self, *messages, delay: float = 10.0) -> None:
        """Shortcut for deleting multiple messages, with optional delay parameter."""
        return await self.bot.cleanup(*messages, delay=delay)

    async def react(self, message, *reactions, delay: float = 0.5):
        """Shortcut to add multiple reactions to a message."""
        return await self.bot.react(*reactions, message=message, delay=delay)

    async def input(
        self,
        prompt: str,
        *,
        timeout: float = 60.0,
        delete_after: bool = True,
        author_id: int = None,
        suffix: str = "\n\nReply to answer.",
    ) -> Union[str, None]:
        """Prompt for input from `author_id`.
        If no input is given or prompt times out return `None`.
        """
        author_id = author_id or self.author.id
        msg = await self.send("{}{}".format(prompt, suffix))

        try:
            message = await self.bot.wait_for(
                "message",
                timeout=timeout,
                check=lambda m: m.author.id == author_id
                and msg.channel == self.channel,
            )
        except asyncio.TimeoutError:
            await self.send("Timed out.", delete_after=60.0 if delete_after else None)
            return None

        try:
            if delete_after:
                await self.cleanup(msg, message, delay=10.0)

        finally:
            if message.content:
                return str(message.content)
            return None

    async def prompt(
        self,
        prompt: str,
        *,
        timeout: float = 60.0,
        delete_after: bool = True,
        author_id: int = None,
        suffix: str = "\n\nReply to answer.",
    ) -> Union[bool, None]:
        """Prompt a boolean response from `author_id`.
        If the user does not reply return None."""
        author_id = author_id or self.author.id
        if self.channel.permissions_for(self.me).add_reactions:
            return  # await self.__prompt_reaction()..

        reply = await self.input(
            prompt=prompt,
            timeout=timeout,
            delete_after=delete_after,
            suffix=suffix,
            author_id=author_id,
        )

        if reply is None:
            return None

        return BoolConverter.check(reply)

    async def __prompt_reaction(
        self,
        prompt: str,
        *,
        timeout: float = 60.0,
        delete_after: bool = True,
        author_id: int = None,
        suffix: str = "\n\nReply to answer.",
    ) -> Union[bool, None]:
        msg = await self.send("{}{}".format(prompt, suffix))
        await self.react(self.message, CHECK, CROSS, 0.5)

        try:
            payload = await self.bot.wait_for(
                "raw_reaction_add",
                timeout=timeout,
                check=lambda p: p.message_id == msg.id
                and p.user_id == author_id
                and str(p.emoji) in (CHECK, CROSS),
            )
        except asyncio.TimeoutError:
            await self.send("Timed out", delete_after=60.0)
            payload = discord.Object(id=None)
            payload.emoji = ""

        try:
            if delete_after:
                await self.cleanup(msg, delay=10.0)

        finally:
            return {CHECK: True, CROSS: False}.get(str(payload.emoji), None)

    @property
    def db(self) -> Optional[Client]:
        return self.bot.db
