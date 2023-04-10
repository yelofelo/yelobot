import discord
from discord.ext import commands
from discord.ext.commands.errors import MissingPermissions
from yelobot_utils import YeloBot, Pagination, reply


def get_category_from_command(command: commands.Command):
    return command.help.splitlines()[0]


def get_help_field_for_command(command: commands.Command, include_name: bool=True):
    split_help = command.help.splitlines()
    help_text = ' '.join(split_help[1:-1])
    usage = split_help[-1]
    aliases = ', '.join(f'+{alias}' for alias in command.aliases)

    if include_name:
        final_text = f'**+{command.name}**\n{help_text}\n'
    else:
        final_text = f'{help_text}\n'

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
                ctx, sorted(categories), title='Use +help <Command> or +help <Category> with one of the following categories:',
                fields_on_page=20, color=discord.Color.yellow())
        else:
            commands = self.get_commands_for_category_and_member(ctx, help_target)
            if not commands:
                sent = await self.send_help_embed_for_command(ctx, help_target)

                if not sent:
                    await reply(ctx, 'This either not a real command/category of commands, or not one that you can access.')
                return
            
            await Pagination.send_paginated_embed(
                ctx, sorted(commands, key=lambda x: x.name), title=f'{help_target} Commands', fields_on_page=5,
                color=discord.Color.yellow(), read_data_fn=get_help_field_for_command
            )

    async def send_help_embed_for_command(self, ctx: commands.Context, command_name: str) -> bool:
        command = self.get_command_with_name_for_member(ctx, command_name)

        if not command:
            return False
        
        embed = discord.Embed(
            title=command.name,
            color=discord.Color.yellow(),
            description=get_help_field_for_command(command, include_name=False)
        )

        await reply(ctx, embed=embed)

        return True

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
    
    def get_command_with_name_for_member(self, ctx: commands.Context, command_name: str) -> commands.Command:
        command_lower = command_name.lower()
        command_found = None

        for command in self.bot.commands:
            if (not command.help) or command.hidden:
                continue
            try:
                if not all(check(ctx) for check in command.checks):
                    continue
            except MissingPermissions:
                continue
            if command.name.lower() == command_lower:
                command_found = command
            for alias in command.aliases:
                if command_lower == alias.lower():
                    command_found = command

            if command_found:
                break
        
        return command_found

