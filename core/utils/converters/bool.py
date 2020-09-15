from discord.ext import commands

from core.errors import Error


class BoolConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return self.check(argument)

    @staticmethod
    def check(argument):
        argument = str(argument).lower()
        if argument in (
            "yes",
            "y",
            "true",
            "t",
            "1",
            "positive",
            "+",
            "yeah",
            "enable",
            "enabled",
            "on",
        ):
            return True
        elif argument in (
            "no",
            "n",
            "false",
            "f",
            "0",
            "negative",
            "-",
            "nope",
            "disable",
            "disabled",
            "off",
        ):
            return False
        else:
            raise Error(f"Could'nt determine Boolean value when converting {argument}")
