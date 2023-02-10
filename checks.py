from discord.ext import commands


def invoked_by_yelofelo(ctx: commands.Context) -> bool:
    return ctx.author.id == 181276019301416960


def invoked_in_club_cheadle(ctx: commands.Context) -> bool:
    return ctx.guild.id == 230963738574848000


def invoked_by_user(*args) -> 'function':
    users = set(args)

    def check(ctx: commands.Context):
        return ctx.author.id in users

    return check
