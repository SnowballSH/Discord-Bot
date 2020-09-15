"""This really needs some work :p"""

from discord.ext import commands
import discord

from core.errors import Error as BaseCustom

import asyncio


class BasePaginator:
    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        self.max_pages = kwargs.get("max_pages", 10)
        self.timeout = kwargs.get("timeout", 300.0)
        self.blocking = asyncio.Semaphore(value=kwargs.get("blocking", 2))
        self.message = kwargs.get("message", None)
        self.current = 0
        self.reactions = {
            "⏮": "first",
            "◀": "previous",
            "⏹": "stop",
            "▶": "next",
            "⏭": "last",
        }


class StringPaginator(BasePaginator):
    def __init__(self, ctx: commands.Context, content: str, **kwargs):

        super().__init__(ctx=ctx, **kwargs)
        self.content: str = str(content)
        self.prefix: str = kwargs.get("prefix", "```")
        self.suffix: str = kwargs.get("suffix", "```")
        self.max_size: int = kwargs.get("max_size", 1900) - (
            len(self.prefix) + len(self.suffix)
        )
        self.max_pages: int = kwargs.get("max_pages", 10)
        self.by_lines: bool = kwargs.get("by_lines", True)
        self.pages: list = (
            self.to_pages_by_lines() if self.by_lines else self.to_pages()
        )

    def __repr__(self):
        return (
            "<StringPaginator Context={0.ctx} Message={0.message} content={0.content} prefix={0.prefix} "
            "suffix={0.suffix} max_size={0.max_size} max_pages={0.max_pages} pages={0.pages} timeout={0.timeout}"
            "current={0.current} Blocking={0.blocking} reactions={0.reactions}>".format(
                self
            )
        )

    def to_pages(self):
        pages = []
        content = self.content
        while len(content) > self.max_size:
            pages.append(content[: self.max_size])
            content = content[self.max_size :]
        pages.append(content)
        return pages

    def to_pages_by_lines(self):
        pages = [""]
        i = 0
        for line in self.content.splitlines(keepends=True):
            if len(pages[i] + line) > self.max_size:
                i += 1
                pages.append("")
            pages[i] += line
        return pages

    def append(self, string: str):
        self.content = self.content + string
        self.pages = self.to_pages()

    async def listener(self):
        def check(p):
            return (
                p.user_id == self.ctx.author.id
                and p.message_id == self.message.id
                and str(p.emoji) in self.reactions
            )

        while not self.ctx.bot.is_closed():
            try:
                payload = await self.ctx.bot.wait_for(
                    "raw_reaction_add", check=check, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                try:
                    await self.message.clear_reactions()
                except discord.Forbidden:
                    pass
                finally:
                    return
            action = self.reactions[str(payload.emoji)]
            if action == "first":
                self.current = 0
            elif action == "previous" and self.current != 0:
                self.current -= 1
            elif action == "next" and len(self.pages) != self.current + 1:
                self.current += 1
            elif action == "last":
                self.current = len(self.pages) - 1
            elif action == "stop":
                try:
                    await self.message.clear_reactions()
                except discord.Forbidden:
                    pass
                finally:
                    return
            await self.update(str(payload.emoji))

    async def update(self, emote: str):
        if self.blocking.locked():
            return

        async with self.blocking:
            await self.message.edit(
                content=f"{self.prefix}{self.pages[self.current]}\n\n"
                f"Page {self.current + 1} / {len(self.pages)}{self.suffix}"
            )

            try:
                await self.message.remove_reaction(emote, self.ctx.author)
            except discord.HTTPException:
                pass

    async def react(self):
        if not len(self.pages) > 1:
            return
        bot = self.ctx.bot.user if not self.ctx.guild else self.ctx.guild.me
        if not bot.permissions_in(self.ctx.channel).add_reactions:
            raise BaseCustom(
                "Failed to react to message - Missing ADD_REACTIONS permission"
            )
        if not isinstance(self.ctx.channel, discord.DMChannel):
            if not bot.permissions_in(self.ctx.channel).manage_messages:
                raise BaseCustom(
                    "Failed to react to message - Missing MANAGE_MESSAGES permission"
                )
        for emote in self.reactions:
            await self.message.add_reaction(emote)

    async def paginate(self):
        self.message = await self.ctx.send(
            f"{self.prefix}{self.pages[self.current]}\n\n"
            f"Page {self.current + 1} / {len(self.pages)}{self.suffix}"
        )

        await self.react()
        self.ctx.bot.loop.create_task(self.listener())
