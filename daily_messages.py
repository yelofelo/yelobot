from discord.ext import commands
from yelobot_utils import YeloBot, reply, Pagination, PaginationButton
from pymongo.database import Database
from datetime import timedelta, datetime

import timezones
import re
import asyncio
import discord
import time


class DailyMessages(commands.Cog):
    RE = re.compile(r'^(?P<hour>\d(\d)?):(?P<minute>\d\d) ((?P<ampm>([Aa][Mm])|([Pp][Mm])) )?(?P<message>.+)$')

    def __init__(self, bot: YeloBot, mongo_db: Database):
        self.bot = bot
        self.MONGO_DB = mongo_db

    async def message_thread(self, channel_id: int, hour: int, minute: int, message: str):
        now = datetime.now()
        today = datetime(now.year, now.month, now.day, 0, 0, 0, 0)

        if (target - now).total_seconds() > 0.1:
            target = today + timedelta(hours=hour, minutes=minute)
        else:
            target = today + timedelta(days=1) - timedelta(hours=hour, minutes=minute)

        channel = await self.bot.fetch_channel(channel_id)
        await asyncio.sleep((target - now).total_seconds())
        await channel.send(message)


    @commands.command('dailymessage')
    @commands.has_guild_permissions(kick_members=True)
    async def add_daily_message(self, ctx: commands.Context, *, command: str):
        """Server Configuration
        Schedules a message that will be sent in this channel every day at a specific time.
        This is based on the time zone that you have set. Defaults to UTC if you have not set one.
        +dailymessage <HH>:<MM> [AM|PM] <message>
        """
        usage = '+dailymessage <HH>:<MM> [AM|PM] <message>'

        mo = re.match(self.RE, command)

        if not mo:
            await reply(ctx, usage)
            return

        hour = int(mo.group('hour'))
        minute = int(mo.group('minute'))

        if hour > 23 or minute > 59 or (mo.group('ampm') and (hour > 12 or hour == 0)):
            await reply(ctx, usage)
            return

        if mo.group('ampm') and mo.group('ampm').lower() == 'am':
            if hour == 12:
                hour = 0
        elif mo.group('ampm') and mo.group('ampm').lower() == 'pm': # second part technically redundant but more clear
            if hour != 12:
                hour += 12
        
        default_timezone = True
        timezone = 'Etc/UTC'

        tz_collection = self.MONGO_DB['Timezones']
        tz_doc = tz_collection.find_one({'user_id': ctx.author.id})

        if tz_doc and tz_doc['is_set']:
            default_timezone = False
            timezone = tz_doc['timezone']

        hours_offset, minutes_offset = timezones.get_utc_offset(timezone)
        hour -= hours_offset
        minute -= minutes_offset

        hour %= 24
        minute %= 60

        daily_collection = self.MONGO_DB['DailyMessages']
        daily_collection.insert_one({'server_id': ctx.guild.id, 'channel_id': ctx.channel.id, 'message': mo.group('message'), 'hour': hour, 'minute': minute})

        to_reply = 'Daily message added.'
        if default_timezone:
            to_reply += ' Warning: You have not set a timezone using +settimezone, so the time you entered was interpreted in UTC.'

        await reply(ctx, to_reply)
        await self.message_thread(ctx.channel.id, hour, minute, mo.group('message'))

    @commands.command(name='dailymessages', aliases=['listdailymessages'])
    @commands.has_guild_permissions(kick_members=True)
    async def list_daily_messages(self, ctx: commands.Context):
        """Server Configuration
        Get a list of all daily messages in this server. Allows you to delete them too.
        +dailymessages
        """
        collection = self.MONGO_DB['DailyMessages']

        query = {'server_id': ctx.guild.id}

        messages = list(collection.find(query))
        
        if not messages:
            await reply(ctx, 'This server has no daily messages set up.')
        else:
            def read_data(message):
                return f'**Message:**\n{message["message"]}\n\n**Channel:**\n{self.bot.get_channel(int(message["channel_id"])).mention}'
            
            async def button_callback(message_data, interaction: discord.Interaction):
                if message_data['author'] != interaction.user.id:
                    await interaction.response.defer()
                    return

                i = message_data['field_idx']
                message = message_data['fields'][i]

                del message_data['fields'][i]
                message_data['max_page'] -= 1

                if message_data['max_page'] <= 1:
                    message_data['next_button'].disabled = True

                if i != 0:
                    message_data['field_idx'] -= 1
                if i <= 1:
                    message_data['prev_button'].disabled = True

                message_data['on_page'] = message_data['field_idx'] + 1

                collection.delete_one(message)
                
                if message_data['max_page'] == 0:
                    message_data['additional_buttons'][0].disabled = True
                    message_data['fields'] = ['This server has no daily messages set up.']
                    message_data['read_data_fn'] = lambda x: x
                    message_data['on_page'] = 1
                    message_data['max_page'] = 1
                    message_data['field_idx'] = 0

                
                if message_data['fields_on_page'] == 1:
                    desc = message_data['read_data_fn'](message_data['fields'][message_data['field_idx']])
                elif message_data['field_idx'] + message_data['fields_on_page'] >= len(message_data['fields']):
                    desc = '\n'.join([message_data['read_data_fn'](field) for field in message_data['fields'][message_data['field_idx']:]])
                else:
                    desc = '\n'.join([message_data['read_data_fn'](field) for field in message_data['fields'][message_data['field_idx']:(message_data['field_idx'] + message_data['fields_on_page'])]])

                embed = discord.Embed(description=desc, title=message_data['title'], color=message_data['color'])
                embed.set_footer(text=f'Page {message_data["on_page"]}/{message_data["max_page"]}')

                view = discord.ui.View(timeout=Pagination.TIMEOUT - (time.time() - message_data['time']))
                view.add_item(message_data['prev_button'])
                view.add_item(message_data['next_button'])
                view.add_item(message_data['additional_buttons'][0])

                await interaction.response.edit_message(
                    embed=embed,
                    view=view
                )

            delete_button = PaginationButton(style=discord.ButtonStyle.danger, label='Delete')
            delete_button.set_callback(button_callback)

            await Pagination.send_paginated_embed(
                ctx, messages, title=f'Daily Messages', color=discord.Color.blurple(), fields_on_page=1, read_data_fn=read_data,
                additional_buttons=[delete_button])

    async def init_daily_messages(self):
        await self.bot.wait_until_ready()

        collection = self.MONGO_DB['DailyMessages']

        to_add = []

        for doc in collection.find():
            to_add.append(self.message_thread(int(doc['channel_id']), int(doc['hour']), int(doc['minute']), doc['message']))

        await asyncio.gather(*to_add)
