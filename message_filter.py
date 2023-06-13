from discord.ext import commands
from discord.ext.commands import has_guild_permissions
import re
from yelobot_utils import reply, get_channel_from_input
import discord

class MessageFilter(commands.Cog):
    word_re = re.compile(r'^([a-z]| )+$')
    def __init__(self, bot, mongodb):
        self.bot = bot
        self.collection = mongodb['MessageFilter']
        self.regex_dict = dict()
        self.channel_logging_dict = dict()
        self.regex_computed = False

    async def compute_regex(self, server_id):
        doc = await self.collection.find_one({'server': server_id})
        self.channel_logging_dict[server_id] = self.bot.get_channel(int(doc['log_channel'])) if int(doc['log_channel']) else None
        if len(doc['words']) != 0:
            self.regex_dict[server_id] = re.compile(r'^(.*[^a-z])?(' + '|'.join((f'({word})' for word in doc['words'])) + r')([^a-z].*)?$')
        else:
            if server_id in self.regex_dict:
                del self.regex_dict[server_id]

    async def compute_all_regex(self):
        docs = await (self.collection.find()).to_list(None)
        for doc in docs:
            server_id = int(doc['server'])
            self.channel_logging_dict[server_id] = self.bot.get_channel(int(doc['log_channel'])) if int(doc['log_channel']) else None
            if len(doc['words']) != 0:
                self.regex_dict[server_id] = re.compile(r'^(.*[^a-z])?(' + '|'.join((f'({word})' for word in doc['words'])) + r')([^a-z].*)?$')
            else:
                if server_id in self.regex_dict:
                    del self.regex_dict[server_id]

    async def filter_out(self, message: discord.Message):
        if discord.Permissions(kick_members=True).is_subset(message.author.guild_permissions):
            return False
        if not self.regex_computed:
            await self.compute_all_regex()
            self.regex_computed = True
        if message.guild.id in self.regex_dict and (mo := re.match(self.regex_dict[message.guild.id], message.content.lower())):
            log_channel = self.channel_logging_dict[int(message.guild.id)]
            if log_channel:
                reason = f'used banned term: {mo.group(2)}'
                await log_channel.send(f'**Message from {message.author} in {message.channel.mention} deleted ({reason}).**\n\nORIGINAL MESSAGE:\n{message.content}')
            return True
        return False

    @commands.command(name='filterword', aliases=['addfilter', 'filterterm', 'filter', 'addtofilter', 'addfilterword', 'addfilterterm'])
    @has_guild_permissions(kick_members=True)
    async def add_to_filter(self, ctx, *, term=None):
        """Moderation
        Add a phrase to the filter.
        +fliterword <Term>
        """
        if term is None:
            await reply(ctx, f'+filterword <term>')
            return
        term = term.lower()
        if not re.match(self.word_re, term):
            await reply(ctx, 'The filter currently doesn\'t work for terms that aren\'t strictly letters and spaces.')
            return
        
        await self.add_server_if_doesnt_exist(ctx.guild.id)
        await self.collection.update_one({'server': ctx.guild.id}, {'$push': {'words': term}})
        await self.compute_regex(ctx.guild.id)
        await reply(ctx, 'The term has been added to the filter.')
    
    @commands.command(name='unfilter', aliases=['removefromfilter', 'removefilter', 'unfilterword', 'unfilterterm'])
    @has_guild_permissions(kick_members=True)
    async def remove_from_filter(self, ctx, *, term=None):
        """Moderation
        Remove a term from the filter.
        +unfilter <Term>
        """
        if term is None:
            await reply(ctx, f'+filterword <term>')
            return
        term = term.lower()
        await self.add_server_if_doesnt_exist(ctx.guild.id)
        doc = await self.collection.find_one({'server': ctx.guild.id})
        if term not in doc['words']:
            await reply(ctx, 'This term was not in the filter.')
            return
        await self.collection.update_one({'server': ctx.guild.id}, {'$pull': {'words': term}})
        await self.compute_regex(ctx.guild.id)
        await reply(ctx, 'The term has been removed from the filter.')

    @commands.command(name='listfilter', aliases=['filtered', 'filteredwords', 'filteredterms'])
    @has_guild_permissions(kick_members=True)
    async def list_filter(self, ctx):
        """Moderation
        List all of the phrases currently in the filter. Use at your own risk 0_0
        +listfilter
        """
        await self.add_server_if_doesnt_exist(ctx.guild.id)
        doc = await self.collection.find_one({'server': ctx.guild.id})
        filtered = list(doc['words'])
        if not filtered:
            await reply(ctx, 'This server currently has no filter.')
        else:
            await reply(ctx, f'Filtered term(s): {", ".join(word for word in filtered)}')

    @commands.command(name='filterlog', aliases=['filterlogchannel'])
    @has_guild_permissions(kick_members=True)
    async def filter_log_channel(self, ctx, *, channel=None):
        """Moderation
        Set the channel where filtered messages are logged.
        +filterlog <Channel>
        """
        await self.add_server_if_doesnt_exist(ctx.guild.id)
        if channel is None:
            await self.collection.update_one({'server': ctx.guild.id}, {'$set': {'log_channel': 0}})
            await reply(ctx, 'Disable the logging of filtered messages.')
            return
        
        channel = get_channel_from_input(self.bot, channel)
        if channel is None:
            await reply(ctx, '+filterlog <channel>')
            return
        
        await self.collection.update_one({'server': ctx.guild.id}, {'$set': {'log_channel': channel.id}})
        await self.compute_regex(ctx.guild.id)
        await reply(ctx, f'Log channel set to {channel.mention}.')
    
    async def add_server_if_doesnt_exist(self, server_id):
        if not await self.collection.find_one({'server': server_id}):
            await self.collection.insert_one({'server': server_id, 'words': [], 'log_channel': 0})
