from discord.embeds import EmptyEmbed
from discord.ext import commands
import discord

from typing import Optional
from logging import getLogger
import collections
import datetime
import aiohttp
import asyncio
import sys
import os

from core import utils, errors
from DataBase import Client


os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"

log = getLogger("Bot")

initial_extensions = ["jishaku"]


class Bot(commands.Bot):
    """A subclass of `discord.ext.commands.Bot` with an aiohttp session and an API client."""

    def __init__(self, **kwargs):
        log.info("Bot instance initialized.")
        super().__init__(
            command_prefix=kwargs.pop("command_prefix", ("Tim.", "T.", "t.", "tim.")),
            description=kwargs.pop("description", "The Tech With Tim Discord Bot."),
            fetch_offline_members=kwargs.pop("fetch_offline_members", True),
            case_insensitive=kwargs.pop("case_insensitive", True),
            status=kwargs.pop("status", discord.Status.offline),
        )
        self.start_time: datetime.datetime = datetime.datetime.utcnow()
        self.status: str = kwargs.get("operational_status", "PRODUCTION")

        self.db: Optional[Client] = None  # TODO DB
        self.error_hook: Optional[discord.Webhook] = None
        self.session: Optional[aiohttp.ClientSession] = None

        self.blacklist = utils.JsonIO("./DataBase/local/blacklist.json")
        self.errors = errors.Cache(limit=100)
        self.sockets = collections.Counter()

        self.__first_ready = True
        self.__first_connect = True

    async def on_ready(self) -> None:
        """Called when the client is done preparing the data received from Discord.
        Usually after login is successful and the Client.guilds and co. are filled up."""
        print("~" * 30)
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(
            f"Shared with:\n - {len(self.users)} users.\n - {len(self.guilds)} guilds."
        )
        print("~" * 30)

        if self.__first_ready:
            self.__first_ready = False

            for ext in initial_extensions:
                self.load_extension(ext)

        await self.change_presence(
            status=discord.Status.online,
        )

    async def on_connect(self) -> None:
        """Called when the bot has established a gateway connection with discord"""
        if self.__first_connect:
            self.__first_connect = False
            from core.settings import BotConfig

            self.session = aiohttp.ClientSession()
            self.error_hook = self.get_webhook(
                url=BotConfig.ERROR_HOOK_URL,
                adapter=discord.AsyncWebhookAdapter(session=self.session),
            )

    async def on_disconnect(self) -> None:
        """Called when the client has disconnected from Discord.
        This could happen either through the internet being disconnected, explicit calls to logout,
        or Discord terminating the connection one way or the other."""
        pass

    async def get_context(self, message, *, cls=utils.Context):  # TODO: Custom Context.
        """Use our custom Context class."""
        return await super().get_context(message=message, cls=cls)

    async def on_message(self, message: discord.Message) -> None:
        """Called when a Message is created and sent."""
        return

        if message.author.id == self.user.id:
            return  # Ignore the bot itself.

        if message.author.bot:
            return  # Ignore any other bots.

        if message.author.id in self.blacklist:
            return  # Ignore any blacklisted users.

        if not self.is_ready():
            await self.wait_until_ready()
            # Don't do anything if the bot is not finished setting up.

        return await self.process_commands(message=message)

    async def process_commands(self, message: discord.Message) -> None:
        """Process the incoming message and execute commands"""
        ctx: commands.Context = await self.get_context(message=message)

        if ctx.command is None:
            return

        try:
            await self.invoke(ctx)

        finally:
            log.info(
                f"Command invoked by {ctx.author} (ID: {ctx.author.id}) "
                f"in #{getattr(ctx.channel, 'name', 'DMs')}. (ID: {ctx.channel.id})"
                f"\n{message.clean_content}"
            )

    async def on_socket_response(self, data: dict) -> None:
        """Undocumented event called when the websocket receives a message."""
        if data.get("t") is None:
            data["t"] = "HEARTBEAT"  # This is a heartbeat.

        self.sockets[data.get("t")] += 1

    async def on_error(self, event_method, *args, **kwargs):
        error = errors.EventError(
            event=event_method, error=sys.exc_info()[1], args=args, kwargs=kwargs
        )

        if isinstance(error.error, errors.ToBeIgnored):
            return

        log.exception(msg=error.fmt)
        self.errors.append(error)

        embed = self.em(
            color=discord.Color.red(),
            title=event_method,
            timestamp="now",
            description=f"```py\n{error.fmt_lenght(1900)}\n```\n"
            f"\nCheck error `{error.id}` for more the full traceback",
        )
        await self.error_hook.send(embed=embed)

    async def on_command_error(self, ctx: utils.Context, exception: BaseException):
        error = getattr(exception, "original", exception)

        if isinstance(
            error,
            (
                discord.Forbidden,
                commands.CheckFailure,
                commands.DisabledCommand,
                commands.TooManyArguments,
            ),
        ):
            return

        command = ctx.command

        if hasattr(command, "on_error"):
            return

        elif isinstance(error, errors.Error):
            return await ctx.send(error.message)

        elif isinstance(error, commands.NoPrivateMessage):
            return await ctx.author.send(
                f"This command cannot be used in private messages."
            )

        elif isinstance(
            error, (commands.MissingRequiredArgument, commands.BadArgument)
        ):
            return await ctx.em(
                title=f"Usage: `{ctx.prefix}{command.qualified_name} {command.signature}`",
                description=command.help or discord.embeds.EmptyEmbed,
                delete_after=60.0,
            )

        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(
                f"You are on cooldown! Try again in {error.retry_after}"
            )

        else:
            error = errors.CommandError(ctx, exception)
            log.exception(error.fmt)
            self.errors.append(error)

            if self.status.upper() == "PRODUCTION":
                await self.error_hook.send(
                    embed=self.em(
                        title=ctx.message.content,
                        color=discord.Color.red(),
                        timestamp="now",
                        description=f"```py\n{error.fmt_lenght(1800)}```\n"
                        f"\nCheck error `{error.id}` for full error",
                        footer=f'G: {getattr(ctx.guild, "id", "DM")} | '
                        f"C: {ctx.channel.id} | "
                        f"U: {ctx.author.id}",
                    )
                )
            else:
                from core.utils.pagination import StringPaginator

                pager = StringPaginator(
                    ctx=ctx,
                    content=error.fmt,
                    prefix="```py",
                    max_size=1900,
                    max_pages=100,
                )
                await pager.paginate()

            error.print()

    """ Helpers """

    @staticmethod
    def get_webhook(
        url: str, adapter: discord.WebhookAdapter = discord.AsyncWebhookAdapter
    ):
        """Short version to get a webhook"""
        return discord.Webhook.from_url(url=url, adapter=adapter)

    @staticmethod
    async def cleanup(*messages, delay: float = 10.0) -> None:
        """Shortcut for deleting multiple messages, with optional delay parameter."""

        async def do_deletion(msg):
            await asyncio.sleep(delay)
            try:
                await msg.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

        for message in messages:
            asyncio.ensure_future(do_deletion(message))

    @staticmethod
    async def react(*reactions, message: discord.Message, delay: float = 0.5) -> None:
        """Shortcut to add multiple reactions to a message."""
        for emote in reactions:
            await asyncio.sleep(delay)
            await message.add_reaction(emote)

    @staticmethod
    def em(**attrs) -> discord.Embed:
        """Shortcut to create `Embed` objects."""
        embed = discord.Embed(
            title=attrs.get("title", EmptyEmbed),
            description=attrs.get("description", EmptyEmbed),
            color=attrs.get("color", attrs.get("colour", EmptyEmbed)),
            url=attrs.get("url", EmptyEmbed),
        )

        if timestamp := attrs.get("timestamp"):
            if timestamp == "now":
                embed.timestamp = datetime.datetime.utcnow()
            else:
                embed.timestamp = timestamp

        if thumbnail := attrs.get("thumbnail"):
            embed.set_thumbnail(url=thumbnail)

        if image := attrs.get("image"):
            embed.set_image(url=image)

        if footer := attrs.get("footer"):
            embed.set_footer(
                text=footer, icon_url=attrs.get("footer_icon_url", EmptyEmbed)
            )

        if author := attrs.get("author"):
            embed.set_author(
                name=author,
                url=attrs.get("author_url", EmptyEmbed),
                icon_url=attrs.get("author_icon_url", EmptyEmbed),
            )

        for field in attrs.get("fields", []):
            embed.add_field(**field)

        return embed
