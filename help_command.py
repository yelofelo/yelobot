import discord
from discord.ext import commands
from discord.ext.commands.errors import MissingPermissions
from yelobot_utils import YeloBot, Pagination, reply


def get_category_from_command(command: commands.Command):
    return command.help.splitlines()[0]


def get_help_field_for_command(command: commands.Command):
    split_help = command.help.splitlines()
    help_text = ' '.join(split_help[1:-1])
    usage = split_help[-1]
    aliases = ', '.join(f'+{alias}' for alias in command.aliases)

    final_text = f'**+{command.name}**\n{help_text}\n'
    if aliases:
        final_text += f'Aliases: {aliases}\n'
    final_text += f'Usage: {usage}'

    return final_text


class HelpCommand(commands.Cog):
    def __init__(self, bot: YeloBot):
        self.bot = bot

    @commands.command(name='help')
    async def help(self, ctx: commands.Context, *, help_target=None):
        """Misc
        Information about YeloBot's commands.
        +help
        """
        if not help_target:
            categories = self.get_categories_for_member(ctx)

            await Pagination.send_paginated_embed(
                ctx, sorted(categories), title='Use +help <Category> with one of the following:',
                fields_on_page=20, color=discord.Color.yellow())
        else:
            commands = self.get_commands_for_category_and_member(ctx, help_target)
            if not commands:
                await reply(ctx, 'This is either not a real category, or not one that you can access.')
                return
            
            await Pagination.send_paginated_embed(
                ctx, sorted(commands, key=lambda x: x.name), title=f'{help_target} Commands', fields_on_page=5,
                color=discord.Color.yellow(), read_data_fn=get_help_field_for_command
            )


    def get_categories_for_member(self, ctx: commands.Context):
        categories = set()
        for command in self.bot.commands:
            if command.help and not command.hidden:
                try:
                    if all(check(ctx) for check in command.checks):
                        categories.add(get_category_from_command(command))
                except MissingPermissions:
                    pass
        return categories


    def get_commands_for_category_and_member(self, ctx: commands.Context, category: str):
        cat_lower = category.lower()
        commands = set()
        for command in self.bot.commands:
            if command.help and get_category_from_command(command).lower() == cat_lower \
                and command.help and not command.hidden:
                try:
                    if all(check(ctx) for check in command.checks):
                        commands.add(command)
                except MissingPermissions:
                    pass
        return commands

