from core import Bot, setup_logging, settings
import argparse
import asyncio

setup_logging("discord", "websockets", "matplotlib")

parser = argparse.ArgumentParser(
    prog="BotBase", description="The Tech With Tim Discord Bot.", allow_abbrev=False
)

choices = (
    "PRODUCTION",
    "TESTING",
)

parser.add_argument(
    "--status", action="store", type=str, choices=choices, default=choices[0]
)

args = parser.parse_args()

try:
    import uvloop
except ImportError:
    uvloop = None
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
finally:
    loop = asyncio.get_event_loop()


async def main():
    config = settings.BotConfig

    bot = Bot(description=parser.description, status=args.status)

    try:
        await bot.start(config.get_token(status=args.status))
    except KeyboardInterrupt:
        await bot.close()


if __name__ == "__main__":
    loop.run_until_complete(main())
