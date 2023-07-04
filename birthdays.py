import discord
from discord.ext import commands
import discord
from discord.ext.commands import has_permissions, has_guild_permissions
import re
import asyncio
import timezones
import time
from yelobot_utils import reply, search_for_user, Pagination, YeloBot

class Birthdays(commands.Cog):
    DEFAULT_TZ = 'Etc/GMT'
    def __init__(self, bot: YeloBot, mongodb):
        self.bot = bot
        self.MONGO_DB = mongodb

    @has_guild_permissions(manage_messages=True)
    @commands.command(name='birthdayrole')
    async def birthday_role(self, ctx, *, role_id=None):
        """Birthdays
        Set the role given to users when their birthday comes.
        +birthdayrole <Role ID>
        """
        role = discord.utils.get(ctx.guild.roles, id=int(role_id))

        if not role:
            await reply(ctx, '+birthdayrole <role id>')
            return

        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': ctx.guild.id})

        if not doc:
            await collection.insert_one({'server': ctx.guild.id, 'role': int(role_id), 'channel': 0, 'message': '', 'users': {}})
        else:
            await collection.update_one({'server': ctx.guild.id}, {'$set': {'role': int(role_id)}})

        await reply(ctx, 'Birthday role updated successfully.')

    @has_permissions(manage_messages=True)
    @commands.command(name='birthdaychannel')
    async def birthday_channel(self, ctx, *, channel_id=None):
        """Birthdays
        Set the channel where birthday announcements are made.
        +birthdaychannel <Channel ID>
        """
        if channel_id is None:
            channel_id = ctx.message.channel.id

        channel = discord.utils.get(ctx.guild.channels, id=int(channel_id))

        if not channel:
            await reply(ctx, '+birthdaychannel <channel id>')
            return
        
        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': ctx.guild.id})

        if not doc:
            await collection.insert_one({'server': ctx.guild.id, 'role': 0, 'channel': int(channel_id), 'message': '', 'users': {}})
        else:
            await collection.update_one({'server': ctx.guild.id}, {'$set': {'channel': int(channel_id)}})

        await reply(ctx, 'Birthday channel updated successfully.')

    @has_permissions(manage_messages=True)
    @commands.command(name='birthdaymessage')
    async def birthday_message(self, ctx, *, message=None):
        """Birthdays
        Set the message that is sent when a user's birthday comes. %USER% will be replaced with the user's @.
        +birthdaymessage <Message>
        """
        if not message:
            await reply(ctx, '+birthdaymessage <message> (use %USER% to mention the user in the message)')
            return
        
        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': ctx.guild.id})

        if not doc:
            await collection.insert_one({'server': ctx.guild.id, 'role': 0, 'channel': 0, 'message': message, 'users': {}})
        else:
            await collection.update_one({'server': ctx.guild.id}, {'$set': {'message': message}})

        await reply(ctx, 'Birthday message updated successfully.')

    DATE_RE = re.compile(r'^(\d?\d)[-\/\.](\d?\d)(?:[-\/\.](?:(?:\d\d)?\d\d))?$')

    @commands.command(name='setbirthday', aliases=['addbirthday'])
    async def set_birthday(self, ctx, *, date=None):
        """Birthdays
        Set your birthday. Use mm/dd for the date (or dd/mm if set using +dateformat). Leave the date blank to remove your birthday.
        +setbirthday [Date]
        """
        usage = '+setbirthday <MM/DD (or DD/MM if set using +dateformat)>'

        if not date:
            tz_doc = await tz_collection.find_one({'user_id': ctx.author.id})
            if not tz_doc:
                await reply(ctx, usage)
            else:
                await tz_collection.delete_one(tz_doc)
                await reply(ctx, 'Your birthday was removed.')
            return

        mo = re.match(self.DATE_RE, date)
        if not mo:
            await reply(ctx, usage)
            return

        tz_collection = self.MONGO_DB['Timezones']
        tz_doc = await tz_collection.find_one({'user_id': ctx.author.id})

        if tz_doc:
            ddmmyy = tz_doc['ddmmyy']
        else:
            ddmmyy = False
        
        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': ctx.guild.id})

        if not doc:
            doc = {'server': ctx.guild.id, 'role': 0, 'channel': 0, 'message': '', 'users': {}}
            await collection.insert_one(doc)

        user_doc = doc['users'].get(str(ctx.author.id))

        if not ddmmyy:
            month = int(mo.group(1))
            day = int(mo.group(2))
        else:
            month = int(mo.group(2))
            day = int(mo.group(1))

        if not valid_date(month, day):
            await reply(ctx, 'This date is invalid. Make sure you have set the correct date format using +dateformat.')
            return

        if user_doc:
            await collection.update_one({'server': ctx.guild.id}, {'$set': {f'users.{ctx.author.id}.month': month, f'users.{ctx.author.id}.day': day, f'users.{ctx.author.id}.is_birthday': False}})
        else:
            await collection.update_one({'server': ctx.guild.id}, {'$set': {f'users.{ctx.author.id}': {
                'month': month, 'day': day, 'is_birthday': False
            }}})

        response = 'Birthday updated successfully.'

        if not tz_doc or not tz_doc['is_set']:
            response += ' If you would like it to match up with your timezone, use +settimezone.'

        await reply(ctx, response)

    @commands.command(name='birthday')
    async def check_birthday(self, ctx, *, user=None):
        """Birthdays
        Find the birthday of this user. If you don't include the User argument, your birthday will be shown.
        +birthday [User]
        """
        if user is None:
            user = ctx.author
        else:
            user = search_for_user(ctx, user)
            if not user:
                await reply(ctx, 'Could not find that user.')
                return
        
        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': ctx.guild.id})

        if doc:
            usr_doc = doc['users'].get(str(user.id))

        if not doc or not usr_doc:
            await reply(ctx, f'{user.nick if user.nick else user.name} has not set a birthday.')
        else:
            ddmmyy = False
            tz_collection = self.MONGO_DB['Timezones']
            tzdoc = await tz_collection.find_one({'user_id': ctx.author.id})
            if tzdoc and tzdoc['ddmmyy']:
                ddmmyy = True
            
            if ddmmyy:
                await reply(ctx, f'{user.nick if user.nick else user.name}\'s birthday is on {usr_doc["day"]:02d}/{usr_doc["month"]:02d}.')
            else:
                await reply(ctx, f'{user.nick if user.nick else user.name}\'s birthday is on {usr_doc["month"]:02d}/{usr_doc["day"]:02d}.')

    @commands.command(name='nextbirthday', aliases=['upcomingbirthday'])
    async def next_birthday(self, ctx):
        """Birthdays
        Find the user whose birthday is up next.
        +nextbirthday
        """
        birthdays = await self.get_birthdays(ctx)

        if birthdays == []:
            await reply(ctx, 'Looks like there are no birthdays in this server.')
            return

        cur_time = time.time()
        tz_collection = self.MONGO_DB['Timezones']

        ddmmyy = False
        tz_doc = await tz_collection.find_one({'user_id': ctx.author.id})
        if tz_doc and tz_doc['ddmmyy']:
            ddmmyy = True

        for month, day, user_id in birthdays:
            
            tz_doc = await tz_collection.find_one({'user_id': user_id})
            if tz_doc and tz_doc['is_set']:
                timezone = tz_doc['timezone']
            else:
                timezone = self.DEFAULT_TZ

            day_to_check = day

            if month == 2 and day == 29 and not timezones.is_leap_year_in_tz(timezone):
                day = 28

            if timezones.unix_at_time(timezone, month, day_to_check, timezones.current_year_in_tz(timezone), 0, 0, 0) > cur_time:
                user = discord.utils.get(ctx.guild.members, id=user_id)
                if not ddmmyy:
                    await reply(ctx, f'{user.nick if user.nick else user.name}\'s birthday is next on {month:02d}/{day:02d}.')
                else:
                    await reply(ctx, f'{user.nick if user.nick else user.name}\'s birthday is next on {day:02d}/{month:02d}.')
                return
        
        month, day, user_id = birthdays[0]
        user = discord.utils.get(ctx.guild.members, id=user_id)
        if not ddmmyy:
            await reply(ctx, f'{user.nick if user.nick else user.name}\'s birthday is next on {month:02d}/{day:02d}.')
        else:
            await reply(ctx, f'{user.nick if user.nick else user.name}\'s birthday is next on {day:02d}/{month:02d}.')

    @commands.command(name='birthdays')
    async def birthdays_cmd(self, ctx):
        """Birthdays
        List the birthdays of everyone in the server.
        +birthdays
        """
        birthdays = await self.get_birthdays(ctx)

        if birthdays == []:
            await reply(ctx, 'Looks like there are no birthdays in this server.')
            return

        ddmmyy = False
        tz_collection = self.MONGO_DB['Timezones']
        tz_doc = await tz_collection.find_one({'user_id': ctx.author.id})
        if tz_doc and tz_doc['ddmmyy']:
            ddmmyy = True

        fields = []

        for month, day, user_id in birthdays:
            member = discord.utils.get(ctx.guild.members, id=user_id)
            date = f'{month:02d}/{day:02d}' if not ddmmyy else f'{day:02d}/{month:02d}'
            fields.append(f'**{date}** - {member.mention}')

        color = discord.Color.blurple()
        birth_collection = self.MONGO_DB['Birthdays']
        cf_doc = await birth_collection.find_one({'server': ctx.guild.id})
        if cf_doc and cf_doc['role'] != 0:
            color = discord.utils.get(ctx.guild.roles, id=int(cf_doc['role'])).color

        await Pagination.send_paginated_embed(ctx, fields, title=f'Birthdays In {ctx.guild.name}', color=color)

    @has_permissions(manage_messages=True)
    @commands.command(name='overwritebirthday', aliases=['obirthday'])
    async def overwrite_birthday(self, ctx, user=None, date=None, *, err=None):
        """Birthdays
        Overwrite a user's birthday.
        +overwritebirthday <User> <New Birthday>
        """
        if user is None or err:
            await reply(ctx, '+overwritebirthday "<user>" [date] (leave date blank to remove)')
            return

        user = search_for_user(ctx, user)
        if not user:
            await reply(ctx, f'Could not find user *{user}*.')
            return

        name = user.nick if user.nick else user.name
        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': ctx.guild.id})

        if doc:
            usr_doc = doc['users'].get(str(user.id))

        if not date:
            if not doc or not usr_doc:
                await reply(ctx, f'*{name}* has not set a birthday.')
                return
            
            await collection.update_one({'server': ctx.guild.id}, {'$unset': {f'users.{user.id}': ''}})
            await reply(ctx, f'Removed *{name}*\'s birthday.')
        else:
            tz_collection = self.MONGO_DB['Timezones']
            tz_doc = await tz_collection.find_one({'user_id': ctx.author.id})
            if tz_doc and tz_doc['ddmmyy']:
                ddmmyy = True
            else:
                ddmmyy = False

            mo = re.match(self.DATE_RE, date)
            if not mo:
                await reply(ctx, f'The date should be in {"MM/DD" if not ddmmyy else "DD/MM"} format, but was *{date}*.')
                return
            
            if not ddmmyy:
                month = int(mo.group(1))
                day = int(mo.group(2))
            else:
                month = int(mo.group(2))
                day = int(mo.group(1))

            if not valid_date(month, day):
                await reply(ctx, f'This date is invalid ({date}). Remember: your date format is set to {"MM/DD" if not ddmmyy else "DD/MM"}.')
                return

            if not doc:
                await collection.insert_one({'server': ctx.guild.id, 'role': 0, 'channel': 0, 'message': '', 'users': {}})

            if usr_doc:
                await collection.update_one({'server': ctx.guild.id}, {'$set': {f'users.{user.id}.day': day, f'users.{user.id}.month': month, f'users.{user.id}.is_birthday': False}})
            else:
                await collection.update_one({'server': ctx.guild.id}, {'$set': {f'users.{user.id}': {
                    'day': day, 'month': month, 'is_birthday': False
                }}})

            new_date = f'{day:02d}/{month:02d}' if ddmmyy else f'{month:02d}/{day:02d}'
            date_format = 'DD/MM' if ddmmyy else 'MM/DD'
            await reply(ctx, f'Updated *{name}*\'s birthday to {new_date} (in {date_format} format).')

    @has_permissions(manage_messages=True)
    @commands.command(name='removebirthdays')
    async def remove_birthdays(self, ctx):
        """Birthdays
        Remove everyone's birthday role. This command is mostly useful if something went wrong.
        +removebirthdays
        """
        collection = self.MONGO_DB['Birthdays']
        birthday_role = ctx.guild.get_role(int(await collection.find_one({'server': ctx.guild.id})['role']))

        for member in ctx.guild.members:
            if birthday_role.id in {r.id for r in member.roles}:
                await member.remove_roles(birthday_role)

    async def get_birthdays(self, ctx):
        collection = self.MONGO_DB['Birthdays']
        birthdays = []

        doc = await collection.find_one({'server': ctx.guild.id})

        if not doc:
            return []

        for usr_id, usr_doc in doc['users'].items():
            member = discord.utils.get(ctx.guild.members, id=int(usr_id))
            if not member:
                continue
            birthdays.append((int(usr_doc['month']), int(usr_doc['day']), int(usr_id)))

        birthdays.sort(key=lambda x: x[0] * 1000 + x[1])
        
        return birthdays

    async def birthday_start(self, user_id, server_id):
        user = self.bot.get_user(int(user_id))
        if not user:
            return

        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': server_id})
        for server_found in user.mutual_guilds:
            if server_found.id == server_id:
                server = server_found
                break
        else:
            print(f'ERROR: server not found (birthday_start)')
            return
        
        member =  await server.fetch_member(int(user_id))
        if doc['role']:
            role = discord.utils.get(server.roles, id=doc['role'])
            await member.add_roles(role)
        if int(doc['channel']) != 0 and doc['message'] != '':
            channel = server.get_channel(int(doc['channel']))

            if member.id == self.bot.user.id:
                await channel.send('It\'s my birthday!')
            else:
                await channel.send(str(doc['message']).replace('%USER%', f'{member.mention}'))
                    
    async def birthday_end(self, user_id, server_id):
        user = self.bot.get_user(int(user_id))
        if not user:
            return

        collection = self.MONGO_DB['Birthdays']
        doc = await collection.find_one({'server': server_id})
        for server_found in user.mutual_guilds:
            if server_found.id == server_id:
                server = server_found
                break
        else:
            print(f'ERROR: server not found (birthday_end)')
            return
        
        member =  await server.fetch_member(int(user_id))
        if doc['role']:
            role = discord.utils.get(server.roles, id=doc['role'])
            await member.remove_roles(role)

    async def init_birthdays(self):
        tz_collection = self.MONGO_DB['Timezones']
        birth_collection = self.MONGO_DB['Birthdays']
        print('Birthdays are being initialized (no conclusion message).')

        while True:
            await asyncio.sleep(10)

            for top_doc in await (birth_collection.find()).to_list(None):
                for user_id, item in top_doc['users'].items():
                    tz_doc = await tz_collection.find_one({'user_id': int(user_id)})
                    if tz_doc and tz_doc['is_set']:
                        timezone = tz_doc['timezone']
                    else:
                        timezone = self.DEFAULT_TZ

                    if int(item['day']) == 29 and int(item['month']) == 2 and not timezones.is_leap_year_in_tz(timezone):
                        day = int(item['day']) - 1
                    else:
                        day = int(item['day'])

                    timestamp = timezones.unix_at_time(
                        timezone, int(item['month']), day, timezones.current_year_in_tz(timezone), 0, 0, 0
                        )
                    
                    if timestamp < time.time() < timestamp + 60 * 60 * 24 and not item['is_birthday']:
                        await self.birthday_start(str(user_id), top_doc['server'])
                        await birth_collection.update_one({'server': top_doc['server']}, {'$set': {f'users.{user_id}.is_birthday': True}})
                    elif item['is_birthday'] and not (timestamp < time.time() < timestamp + 60 * 60 * 24 ):
                        await self.birthday_end(str(user_id), top_doc['server'])
                        await birth_collection.update_one({'server': top_doc['server']}, {'$set': {f'users.{user_id}.is_birthday': False}})

def valid_date(month, day):
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return 1 <= day <= 31
    elif 4 <= month <= 11:
        return 1 <= day <= 30
    elif month == 2:
        return 1 <= day <= 29
    else:
        return False
    
    