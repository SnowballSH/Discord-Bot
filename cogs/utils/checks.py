from discord import Member
from discord.ext.commands import check


def is_admin(member: Member):
    for role in member.roles:
        if role.id in (739207116711133245, 580911082290282506, 537990081156481025):
            return True
    return False


def is_mod(member: Member):
    for role in member.roles:
        if role.id in (739207116711133245, 739207116711133245):
            return True
    return is_admin(member)


def is_engineer(member: Member):
    for role in member.roles:
        if role.id == 739207116711133245:
            return True
    return is_mod(member)


def is_mod_check():
    def predicate(ctx):
        return is_mod(ctx.author)
    return check(predicate)


def is_engineer_check():
    def predicate(ctx):
        return is_engineer(ctx.author)
    return check(predicate)


def in_twt():
    def predicate(ctx):
        return ctx.guild.id == 739205949134471238
    return check(predicate)
