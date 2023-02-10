import discord
from discord.ext import commands
from discord import app_commands
import re
import time
from datetime import datetime, timedelta
import asyncio

import yelobot_utils
from yelobot_utils import Pagination, PaginationButton, reply
import timezones

months = dict([
    ('january', '1'),
    ('february', '2'),
    ('march', '3'),
    ('april', '4'),
    ('may', '5'),
    ('june', '6'),
    ('july', '7'),
    ('august', '8'),
    ('september', '9'),
    ('october', '10'),
    ('november', '11'),
    ('december', '12')
])

months_reverse = dict([
    (1, 'January'),
    (2, 'February'),
    (3, 'March'),
    (4, 'April'),
    (5, 'May'),
    (6, 'June'),
    (7, 'July'),
    (8, 'August'),
    (9, 'September'),
    (10, 'October'),
    (11, 'November'),
    (12, 'December')
])

class ReminderModal2(discord.ui.Modal, title='Create Reminder (Page 2)'):
    field_hour = discord.ui.TextInput(label='Hour', default='12', required=True, min_length=1, max_length=2, row=0)
    field_minute = discord.ui.TextInput(label='Minute', default='00', required=True, min_length=1, max_length=2, row=1)
    field_second = discord.ui.TextInput(label='Second', default='00', required=True, min_length=1, max_length=2, row=2)
    field_am_pm = discord.ui.TextInput(label='AM or PM', placeholder='AM/PM or leave blank for 24 hour time.', required=False, min_length=0, max_length=2, row=3)

    def __init__(self, reminders_collection, user_tz, message, month, day, year, reminder_thread):
        super().__init__()
        self.tz = user_tz
        self.message_value = message
        self.month_value = month
        self.day_value = day
        self.year_value = year
        self.collection = reminders_collection
        self.reminder_thread = reminder_thread

    async def on_submit(self, interaction: discord.Interaction):
        if self.month_value.lower() in months:
            self.month_value = months[self.month_value.lower()]
        else:
            await interaction.response.edit_message(content='Looks like you need some help. Maybe check this out: <https://www.englishclub.com/vocabulary/time-months-of-year.htm>', view=None)
            return

        try:
            month = int(self.month_value)
            day = int(self.day_value)
            year = int(self.year_value)
            hour = int(self.field_hour.value)
            minute = int(self.field_minute.value)
            second = int(self.field_second.value)
        except ValueError:
            await interaction.response.edit_message(content='The numerical values have to be numbers. This shouldn\'t be hard...', view=None)
            return
        
        ampm = self.field_am_pm.value.lower()
        if ampm and ampm not in ('am', 'pm'):
            await interaction.response.edit_message(content='The AM/PM field has to be AM, PM, or blank. How do you even mess that up?', view=None)
            return
        
        if ampm and (hour <= 0 or hour > 12):
            await interaction.response.edit_message(content='You picked 12-hour time, but the hour you entered was not in 12-hour time.', view=None)
            return
        
        if ampm == 'am' and hour == 12:
            hour = 0
        elif ampm == 'pm' and hour != 12:
            hour += 12
        
        try:
            unix = timezones.unix_at_time(self.tz, month, day, year, hour, minute, second)
        except ValueError:
            await interaction.response.edit_message(content='Your timestamp was invalid.', view=None)
            return

        if datetime.utcfromtimestamp(unix) > datetime.now() + timedelta(days=(365 * 5)):
            await interaction.response.edit_message(content='Cannot create reminders for dates past 5 years from now.', view=None)
            return

        item = {'user': interaction.user.id, 'channel': interaction.channel_id, 'time': unix, 'message': self.message_value}
        self.collection.insert_one(item)

        await interaction.response.edit_message(content='Reminder set.', view=None)

        if unix - time.time() < 86400:
            await self.reminder_thread(unix, interaction.channel_id, interaction.user.id, self.message_value)

class ModalTransitionButton(discord.ui.Button):
    def __init__(self, user_id, reminders_collection, user_tz, message, month, day, year, reminder_thread):
        super().__init__(label='Continue')
        self.user_id = user_id
        self.collection = reminders_collection
        self.tz = user_tz
        self.message = message
        self.month = month
        self.day = day
        self.year = year
        self.reminder_thread = reminder_thread

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label='Continue', disabled=True))
        await interaction.message.edit(view=view)
        await interaction.response.send_modal(ReminderModal2(self.collection, self.tz, self.message, self.month, self.day, self.year, self.reminder_thread))

class ReminderModal1(discord.ui.Modal, title='Create Reminder (Page 1)'):
    field_message = discord.ui.TextInput(label='Message', placeholder='This is what YeloBot will @ you with.', required=True, style=discord.TextStyle.long, max_length=500, row=0)
    field_month = discord.ui.TextInput(
        label='Month',
        default=months_reverse[timezones.current_month_in_tz('Etc/UTC')],
        required=True, row=1, style=discord.TextStyle.short, min_length=1, max_length=9)
    field_day = discord.ui.TextInput(label='Day', default='1', required=True, style=discord.TextStyle.short, min_length=1, max_length=2, row=2)
    field_year = discord.ui.TextInput(label='Year', default=str(timezones.current_year_in_tz('Etc/UTC')), required=True, min_length=4, max_length=4, row=3)

    def __init__(self, reminders_collection, user_tz, reminder_thread):
        super().__init__()
        self.tz = user_tz
        self.collection = reminders_collection
        self.reminder_thread = reminder_thread

    async def on_submit(self, interaction: discord.Interaction):
        view = discord.ui.View()
        view.add_item(
            ModalTransitionButton(interaction.user.id, self.collection, self.tz, self.field_message.value, self.field_month.value, self.field_day.value, self.field_year.value, self.reminder_thread)
            )
        await interaction.response.send_message(view=view)


class Reminders(commands.Cog):
    REMIND_RE = re.compile(r'^((?P<weeks>\d*)w)?((?P<days>\d*)d)?((?P<hours>\d*)h)?((?P<minutes>\d*)m)?((?P<seconds>\d*)s)?$')

    def __init__(self, bot, mongo):
        self.bot = bot
        self.MONGO_DB = mongo

    def get_remind_time(self, mo):
        time_set = 0
        if mo.group('weeks'):
            time_set += int(mo.group('weeks')) * 604800
        if mo.group('days'):
            time_set += int(mo.group('days')) * 86400
        if mo.group('hours'):
            time_set += int(mo.group('hours')) * 3600
        if mo.group('minutes'):
            time_set += int(mo.group('minutes')) * 60
        if mo.group('seconds'):
            time_set += int(mo.group('seconds'))

        return time_set + time.time()

    async def reminder_thread(self, time_set, channel_id, user_id, message):
        query = {'user': user_id, 'channel': channel_id, 'time': time_set, 'message': message}
        channel = yelobot_utils.get(self.bot.get_all_channels(), id=channel_id)
        user = yelobot_utils.get(self.bot.get_all_members(), id=user_id)
        to_send = f'{user.mention} {message}'

        if time_set - time.time() <= 0:
            await channel.send(to_send)
        else:
            await asyncio.sleep(time_set - time.time())
            if not self.MONGO_DB['Reminders'].find_one(query):
                return
            await channel.send(to_send)

        collection = self.MONGO_DB['Reminders']
        collection.delete_many(query)

    @app_commands.command(name='remindme', description='Creates an absolute-time reminder.')
    async def remindme_app(self, interaction: discord.Interaction):
        collection = self.MONGO_DB['Timezones']
        doc = collection.find_one({'user_id': interaction.user.id})
        if not doc or not doc['is_set']:
            await interaction.response.send_message('You have not yet set a timezone. Please use +settimezone first.')
            return

        await interaction.response.send_modal(ReminderModal1(self.MONGO_DB['Reminders'], doc['timezone'], self.reminder_thread))

    @commands.command(name='remindme', aliases=['remind'])
    async def remind_me(self, ctx: commands.Context, *, command=None):
        """Time/Reminders
        Creates a relative-time reminder. For absolute-time reminders, use /remindme. Here's an example
        of the Time argument: 5w2d3h25m55s
        +remindme <Time> <Message>
        """
        usage = 'Usage: +remindme 5w2d3h25m55s Say hello to YeloFelo!'

        if ctx.message.content == '+remindme 5w2d3h25m55s Say hello to YeloFelo!':
            await reply(ctx, 'yep you\'re so funny')
            return

        if '@everyone' in ctx.message.content or '@here' in ctx.message.content:
            await reply(ctx, 'nice try')
            return
        
        if not command:
            await reply(ctx, usage)
            return

        complete_re = r'^((?P<relative>((\d*)w)?((\d*)d)?((\d*)h)?((\d*)m)?((\d*)s)?)|(?P<absolute>(\d?\d)[-\/\.](\d?\d)([-\/\.]((\d\d)?\d\d)) (\d?\d)[:\.](\d\d)([:\.](\d\d))?( ?([AaPp][Mm]))?)) (?P<message>.+)$'
        complete_re_match = re.match(complete_re, command)

        if not complete_re_match:
            await reply(ctx, usage)
            return

        message = complete_re_match.group('message')

        is_absolute_time = False

        if complete_re_match.group('relative'):
            mo_relative = re.match(self.REMIND_RE, complete_re_match.group('relative'))
            time_to_remind = self.get_remind_time(mo_relative)
        else:
            is_absolute_time = True
            collection = self.MONGO_DB['Timezones']

            doc = collection.find_one({'user_id': ctx.author.id})

            if doc is None or not doc['is_set']:
                await reply(ctx, 'Your time does not match the usage (or, for absolute times, you have not yet set a timezone using +settimezone).\n' + usage)
                return

            if doc['ddmmyy']:
                absolute_re = r'^(?P<day>\d?\d)[-\/\.](?P<month>\d?\d)([-\/\.](?P<year>(\d\d)?\d\d)) (?P<hour>\d?\d)[:\.](?P<minute>\d\d)([:\.](?P<second>\d\d))?( ?(?P<ampm>[AaPp][Mm]))?$'
            else:
                absolute_re = r'^(?P<month>\d?\d)[-\/\.](?P<day>\d?\d)([-\/\.](?P<year>(\d\d)?\d\d)) (?P<hour>\d?\d)[:\.](?P<minute>\d\d)([:\.](?P<second>\d\d))?( ?(?P<ampm>[AaPp][Mm]))?$'

            mo_absolute = re.match(absolute_re, complete_re_match.group('absolute'))
            if not mo_absolute:
                await reply(ctx, usage)
                return
            
            month = int(mo_absolute.group('month'))
            day = int(mo_absolute.group('day'))
            hour = int(mo_absolute.group('hour'))
            minute = int(mo_absolute.group('minute'))
            second = int(mo_absolute.group('second')) if mo_absolute.group('second') else 0

            if mo_absolute.group('ampm'):
                if hour > 12 or hour == 0:
                    await reply(ctx, 'Invalid hour when using 12-hour time.')
                    return

                if mo_absolute.group('ampm').lower() == 'am':
                    if hour == 12:
                        hour = 0
                else:
                    if hour != 12:
                        hour += 12


            year = int(mo_absolute.group('year')) if len(mo_absolute.group('year')) == 4 else int(mo_absolute.group('year')) + 2000

            try:
                unix = timezones.unix_at_time(doc['timezone'], month, day, year, hour, minute, second)
            except ValueError:
                await reply(ctx, 'You have an error in your timestamp. (Make sure your date format is set correctly with the +dateformat command!)')
                return

            time_to_remind = unix

        if datetime.utcfromtimestamp(time_to_remind) > datetime.now() + timedelta(days=(365 * 5)):
            await reply(ctx, 'Cannot create reminders for dates past 5 years from now.')
            return

        collection = self.MONGO_DB['Reminders']
        item = {'user': ctx.author.id, 'channel': ctx.message.channel.id, 'time': time_to_remind, 'message': message}
        collection.insert_one(item)

        await reply(ctx, 'Reminder set.' + ('\n*Absolute-time reminders are easier to set using the slash command (/remindme). Try that next time :)*' if is_absolute_time else ''))

        if time_to_remind - time.time() < 86400:
            await self.reminder_thread(time_to_remind, ctx.message.channel.id, ctx.author.id, message)

    @commands.command(name='listreminders', aliases=['reminders'])
    async def list_reminders(self, ctx):
        """Time/Reminders
        Get a list of all of your active reminders.
        +listreminders
        """
        collection = self.MONGO_DB['Reminders']

        query = {'user': ctx.author.id}

        reminders = []

        for reminder in collection.find(query):
            channel = self.bot.get_channel(int(reminder['channel']))
            if channel is not None and channel.guild.id == ctx.guild.id:
                reminders.append(reminder)
        
        if not reminders:
            await ctx.send('You have no active reminders.')
        else:
            def read_data(reminder):
                time_remaining = yelobot_utils.time_remaining(int(reminder['time'])) if reminder['time'] > time.time() else 'Already sent.'

                return f'**Message:**\n{reminder["message"]}\n\n**Channel:**\n{self.bot.get_channel(int(reminder["channel"])).mention}\n\n'\
                f'**Time Remaining:**\n{time_remaining}'
            
            async def button_callback(message_data, interaction: discord.Interaction):
                if message_data['author'] != interaction.user.id:
                    await interaction.response.defer()
                    return

                i = message_data['field_idx']
                reminder = message_data['fields'][i]

                del message_data['fields'][i]
                message_data['max_page'] -= 1

                if message_data['max_page'] <= 1:
                    message_data['next_button'].disabled = True

                if i != 0:
                    message_data['field_idx'] -= 1
                if i <= 1:
                    message_data['prev_button'].disabled = True

                message_data['on_page'] = message_data['field_idx'] + 1

                if time.time() < reminder['time']:
                    self.MONGO_DB['Reminders'].delete_one(reminder)
                
                if message_data['max_page'] == 0:
                    message_data['additional_buttons'][0].disabled = True
                    message_data['fields'] = ['You have no active reminders.']
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
                ctx, reminders, title=f'{ctx.author.nick if ctx.author.nick else ctx.author.name}\'s Reminders', color=discord.Color.blurple(), fields_on_page=1, read_data_fn=read_data,
                additional_buttons=[delete_button])


    async def init_reminders(self):
        await asyncio.sleep(5) # Wait for the bot to initialize
        collection = self.MONGO_DB['Reminders']

        to_add = []

        for item in list(collection.find()):
            try:
                server = (await self.bot.fetch_channel(int(item['channel']))).guild
                await server.fetch_member(int(item['user']))
            except:
                continue
            if item['time'] - time.time() < 86400:
                to_add.append([float(item['time']), int(item['channel']), int(item['user']), str(item['message'])])

        print(f'Initializing {len(to_add)} reminders')
        await asyncio.gather(*[self.reminder_thread(t, c, u, m) for t, c, u, m in to_add])