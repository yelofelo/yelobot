###############################################################################
# I started working on this when I was very new to coding. A lot
# of the codebase and especially this file (bot.py) is pretty hacky and 
# inconsistent. I try to clean things up as much as I can every now and again,
# but a full rewrite may be necessary one day.
# - YeloFelo
###############################################################################


import os
import asyncio
import random
import time
import wikipedia
import urllib
import re
from datetime import timedelta
from dotenv import load_dotenv
from mcstatus import JavaServer
from mcrcon import MCRcon
import socket
from bs4 import BeautifulSoup, element
from motor.motor_asyncio import AsyncIOMotorClient
import emoji
import io
import certifi
import aiohttp
from fuzzywuzzy import fuzz
from typing import Iterable

import urllib.request
import urllib.parse
import urllib.error

import requests
import json

from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands import has_permissions, has_guild_permissions
from discord.ext.commands.errors import CommandError

import discord

from lastmessages import LastMessages
import nominatim
import timezonedb
import timezones
from tictactoe import TicTacToe, TicTacToeInvalidMoveError, TicTacToeWrongPlayerError
from startup_tasks import StartupTask
from birthdays import Birthdays
import save_roles
from reminders import Reminders
import gpt_discord
from openai_interface import OpenAIInterface
from message_filter import MessageFilter
from archive_pins import ArchivePins
from bible_verse import BibleVerse
from daily_messages import DailyMessages
import checks
from help_command import HelpCommand
from currency_conversion import CurrencyConversion
#from timestamps import Timestamps

import yelobot_utils
from yelobot_utils import search_for_user, reply, Pagination, formatted_exception, YeloBot

load_dotenv()
os.environ['TZ'] = 'Europe/London'  # Set the timezone to UTC

_STEAM_API_KEY = os.getenv('STEAM_KEY')
_STEAM_BASE_URL = 'https://api.steampowered.com/'

LWOLF_SERVER_ID = 230963738574848000
BOT_TESTING_SERVER_ID = 764984305696636939
YELOFELO_USER_ID = 181276019301416960

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEATHER_KEY = os.getenv('WEATHER_KEY')
MINECRAFT_IP = os.getenv('MINECRAFT_IP')
RCON_PASSWORD = os.getenv('RCONPW')
TIMEZONEDB_KEY = os.getenv('TIMEZONE_KEY')
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION')
MONGO_DATABASE_NAME = os.getenv('MONGO_DATABASE')
MINECRAFT_HOST = os.getenv('MINECRAFT_HOST')
BIBLE_API_KEY = os.getenv('BIBLE_API_KEY')
EXCHANGE_RATE_KEY = os.getenv('EXCHANGE_RATE_KEY')

MC_PORT = 25589
RCON_PORT = 8088
MC_PLAYERS_SET = set()
CHANNEL_FOR_MC_PLAYERS = None
CHANNEL_FOR_MC_PLAYERS_ID = 1003172707183099977
ANNOUNCE_MINECRAFT_EVENTS = False

OPENAI_INTERFACE = OpenAIInterface(os.getenv('OPENAI_API_KEY'))

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.presences = True
intents.message_content = True

###
# For weather command. This is very disorganized and should definitely be rewritten.
units = 'imperial'
base_weather_url = 'https://api.openweathermap.org/data/2.5/weather?q='
sewanee_weather_url = 'https://api.openweathermap.org/data/2.5/weather?q=sewanee&units=imperial&appid=' + WEATHER_KEY
weather_url_ext = '&units='
###

bot = YeloBot(command_prefix="+", intents=intents)
bot.remove_command('help')
StartupTask.set_bot(bot)

lastmessages = LastMessages()

PLAYING_STATUS = 'Mario Remastered'


RESPONSE_TIME_TO_WAIT = random.randrange(20 * 60, int(1.5 * 60 * 60))
RESPONSE_IDLE_STATUSES = []
RESPONSE_MESSAGE_COUNTER = 0
RESPONSE_MESSAGE_GOAL = random.randint(50, 200)
RESPONSE_LOCK = None

IS_TALKING = None
RESPOND_TO_MENTIONS = False


@bot.event
async def on_ready():
    # bot.tree.copy_global_to(guild=discord.Object(BOT_TESTING_SERVER_ID))
    # await bot.tree.sync(guild=discord.Object(BOT_TESTING_SERVER_ID))

    print(f'{bot.user} is connected to:\n')
    for guild in bot.guilds:
        print(
            f'{guild.name}(id: {guild.id})'
        )
    await bot.change_presence(activity=discord.Game(name=PLAYING_STATUS))


@bot.command(name='syncglobal', hidden=True)
@commands.check(checks.invoked_by_yelofelo)
async def sync_global(ctx: commands.Context):
    await reply(ctx, 'Syncing commands globally.')
    await bot.tree.sync()


@bot.command(name='synclocal', hidden=True)
@commands.check(checks.invoked_by_yelofelo)
async def sync_local(ctx: commands.Context):
    await reply(ctx, 'Syncing commands to only this server.')
    bot.tree.clear_commands(guild=ctx.guild)
    bot.tree.copy_global_to(ctx.guild)
    await bot.tree.sync(guild=ctx.guild)


@bot.event
async def on_message(message: discord.Message):
    # This NEEDS to be refactored into other functions. This event is an absolute mess.
    #  This is probably true for all of the event functions, but this one is a disaster.
    global lastmessages
    global RESPONSE_MESSAGE_COUNTER
    global RESPONSE_MESSAGE_GOAL
    global RESPONSE_IDLE_STATUSES
    global RESPONSE_LOCK
    global RESPONSE_TIME_TO_WAIT

    if message.author == bot.user or message.channel.id == 247568720682024961:
        return
    
    if message.type == discord.MessageType.pins_add:
        archive_cog: ArchivePins = bot.get_cog('ArchivePins')
        if len(await message.channel.pins()) == 50 and (await archive_cog.archiving_is_on(message.channel.id)):
            pin_arch_msg = await message.channel.send('We\'ve hit the pin limit. Archiving pins...')
            await archive_cog.commence_archive(message.channel)
            await reply(pin_arch_msg, 'Done.')
            return

    if await bot.get_cog('MessageFilter').filter_out(message):
        await message.delete()
        return

    if message.guild.id == LWOLF_SERVER_ID:
        if message.content == 'Hey gamers! Stay hydrated! :)' and 'MEE6' in message.author.name:
            await message.channel.send(':cup_with_straw:')
        elif message.content.lower() == 'tylko jedno w głowie mam':
            await message.channel.send('koksu pięć gram')
            await message.channel.send('odlecieć sam')
            await message.channel.send('w krainę zapomnienia')

    if len(message.content) > 0 and message.content[0] == '+':
        await bot.process_commands(message)
        return

    # counting
    if message.content:
        try:
            if message.content == '9+10' or message.content == '9 + 10':
                number = 21
            else:
                number = int(message.content.split()[0])
            await process_counting(message, number)
        except ValueError:
            pass

    if lastmessages.resend(message.content, message.channel.id, message.author.id):
        await message.channel.send(message.content)
        return
    
    if await bot_is_talking():
        if RESPOND_TO_MENTIONS and message.guild.id == LWOLF_SERVER_ID and message.channel.id != 247568720682024961 and bot.user in message.mentions:
            await gpt_discord.respond_to(bot, message, OPENAI_INTERFACE)
        elif message.channel.id == 230963738574848000: # general club cheadle, for talking
            async with RESPONSE_LOCK:
                RESPONSE_MESSAGE_COUNTER += 1
                if RESPONSE_MESSAGE_COUNTER >= RESPONSE_MESSAGE_GOAL:
                    await gpt_discord.respond_to(bot, message, OPENAI_INTERFACE)
                    RESPONSE_MESSAGE_COUNTER = 0
                    RESPONSE_MESSAGE_GOAL = random.randint(50, 200)
                if RESPONSE_IDLE_STATUSES:
                    status = RESPONSE_IDLE_STATUSES.pop()
                    status['idle'] = False
            
            new_status = {'idle': True}
            async with RESPONSE_LOCK:
                RESPONSE_IDLE_STATUSES.append(new_status)
            if await gpt_discord.send_if_idle(bot, RESPONSE_TIME_TO_WAIT, message.channel, new_status, OPENAI_INTERFACE, RESPONSE_LOCK):
                RESPONSE_TIME_TO_WAIT = random.randrange(20 * 60, 1.5 * 60 * 60)
                RESPONSE_MESSAGE_GOAL = random.randint(50, 200)
                RESPONSE_MESSAGE_COUNTER = 0

@bot.event
async def on_raw_message_delete(payload):
    counting_collection = MONGO_DB['Counting']

    doc = await counting_collection.find_one({'server': payload.guild_id})

    if not doc:
        return

    if payload.message_id == doc['last_message']:
        guild = bot.get_guild(payload.guild_id)
        author = yelobot_utils.get(guild.members, id=int(doc['last_user']))

        name = author.nick if author.nick else author.name
        channel = bot.get_channel(payload.channel_id)
        await channel.send(f'{name} deleted their message. The next number is {doc["count"] + 1}.')


@bot.event
async def on_raw_message_edit(payload):
    counting_collection = MONGO_DB['Counting']
    
    doc = await counting_collection.find_one({'server': payload.guild_id})

    if not doc:
        return

    if payload.message_id == doc['last_message']:
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        warn_condition = False

        try:
            num = int(message.content.split()[0])
            warn_condition = num != doc['count']
        except ValueError:
            warn_condition = True

        if warn_condition:
            guild = bot.get_guild(payload.guild_id)
            author = yelobot_utils.get(guild.members, id=int(doc['last_user']))

            name = author.nick if author.nick else author.name

            await channel.send(f'{name} edited their message. The next number is {doc["count"] + 1}.')


@bot.event
async def on_member_join(member: discord.Member):
    server_id = str(member.guild.id)

    sal_collection = MONGO_DB['Salutations']
    sal_doc = await sal_collection.find_one({'server': int(server_id)})

    jr_collection = MONGO_DB['JoinRole']
    jr_doc = await jr_collection.find_one({'server_id': int(server_id)})

    if sal_doc and sal_doc['join'] and sal_doc['channel']:
        await bot.get_channel(sal_doc['channel']).send(sal_doc['join'].replace('%USER%', f'{member.mention}').replace('%SERVER%', member.guild.name))

        if (not await save_roles.assign_roles(member, MONGO_DB)) and jr_doc:
            join_role = discord.utils.get(member.guild.roles, id=jr_doc['role_id'])
            if join_role:
                try:
                    await member.add_roles(join_role, reason='Assigning the join role to a new server member.')
                except discord.Forbidden:
                    pass


@bot.event
async def on_member_remove(member):
    server = str(member.guild.id)

    collection = MONGO_DB['Salutations']
    doc = await collection.find_one({'server': int(server)})

    if doc and doc['leave'] and doc['channel']:
        await bot.get_channel(doc['channel']).send(doc['leave'].replace('%USER%', f'{member}').replace('%SERVER%', member.guild.name))

    await save_roles.save_roles(member, MONGO_DB)

# @bot.command(name='synctesting', hidden=True)
# async def sync_app_commands(ctx):
#     if ctx.author.id != YELOFELO_USER_ID:
#         return

    
#     await reply(ctx, 'Synced to Bot Testing.')

@bot.command(name='sayinchannel', hidden=True)
@commands.check(checks.invoked_by_yelofelo)
async def say_in_channel(ctx: commands.Context, channel_id: int, *, message=None): # This just allows YelFelo to talk through YeloBot in an arbitrary channel
    if ctx.author.id != YELOFELO_USER_ID:
        return

    if message is None:
        message = ''
    
    channel = bot.get_channel(channel_id)
    await channel.send(f'{ctx.author.name}: {message}', files=[await att.to_file() for att in ctx.message.attachments])


@bot.command(name='joinmessage')
@has_guild_permissions(manage_messages=True)
async def add_join_message(ctx, *, message):
    """Server Configuration
    Update the message that appears when someone joins. %USER% will be replaced with the user's @, and %SERVER% will be
    replaced with the server name.
    +joinmessage <Message>
    """
    collection = MONGO_DB['Salutations']
    doc = await collection.find_one({'server': ctx.guild.id})

    if doc:
        await collection.update_one({'server': ctx.guild.id}, {'$set': {'join': message}})
        msg = 'Join message updated.'
    else:
        await collection.insert_one({'server': ctx.guild.id, 'join': message, 'leave': '', 'channel': 0})
        msg = 'Join message updated. Please remember to set the channel using +salutationchannel <#channel>.'

    await reply(ctx, msg)

@bot.command(name='leavemessage')
@has_guild_permissions(manage_messages=True)
async def add_leave_message(ctx, *, message):
    """Server Configuration
    Update the message that appears when someone leaves. %USER% will be replaced with their username,
    and %SERVER% will be replaced with the server name.
    +leavemessage <Message>
    """
    collection = MONGO_DB['Salutations']
    doc = collection.find_one({'server': ctx.guild.id})

    if doc:
        await collection.update_one({'server': ctx.guild.id}, {'$set': {'leave': message}})
        msg = 'Leave message updated.'
    else:
        await collection.insert_one({'server': ctx.guild.id, 'leave': message, 'join': '', 'channel': 0})
        msg = 'Leave message updated. Please remember to set the channel using +salutationchannel <#channel>.'

    await reply(ctx, msg)

@bot.command(name='salutationchannel')
@has_guild_permissions(manage_messages=True)
async def set_salutation_channel(ctx, *, channel=None):
    """Server Configuration
    Set the channel where the join and leave messages are posted.
    +salutationchannel #<Channel>
    """
    if channel:
        try:
            channel_id = int(channel.lstrip('<#').rstrip('>'))
            if not bot.get_channel(channel_id):
                raise
        except:
            await ctx.send('Please specify a channel using #channel-name, or use this command with no arguments to use the current channel.')
            return
    else:
        channel_id = ctx.message.channel.id

    collection = MONGO_DB['Salutations']
    doc = await collection.find_one({'server': ctx.guild.id})

    if doc:
        await collection.update_one({'server': ctx.guild.id}, {'$set': {'channel': channel_id}})
    else:
        await collection.insert_one({'server': ctx.guild.id, 'leave': '', 'join': '', 'channel': channel_id})

    await reply(ctx, f'{bot.get_channel(channel_id)} has been set as the salutation channel.')

@bot.event
async def on_raw_reaction_add(reaction: discord.RawReactionActionEvent):
    emote_collection = MONGO_DB['EmoteRoles']

    item = await emote_collection.find_one({'message': reaction.message_id})

    if item and reaction.emoji.name in item['emotes']:
        await reaction.member.add_roles(
            reaction.member.guild.get_role(item['emotes'][reaction.emoji.name]),
            reason='Member used a self-assign reaction'
        )
        return

    timezone_collection = MONGO_DB['Timezones']
    youtube_collection = MONGO_DB['YoutubeSubs']

    if reaction.emoji.name == '✅':
        if await timezone_collection.find_one({'message_id': reaction.message_id, 'user_id': reaction.user_id}):
            await confirm_timezone(reaction.user_id, await bot.fetch_channel(reaction.channel_id))
            return
        elif await youtube_collection.find_one({'message': reaction.message_id, 'user_id': reaction.user_id}):
            yt_cog = bot.get_cog('YouTube')
            await yt_cog.confirm_sub(reaction.message_id, reaction.channel_id)
            return


@bot.event
async def on_raw_reaction_remove(reaction: discord.RawReactionActionEvent):
    collection = MONGO_DB['EmoteRoles']

    item = await collection.find_one({'message': reaction.message_id})

    if item:
        member = bot.get_guild(LWOLF_SERVER_ID).get_member(reaction.user_id)
        if reaction.emoji.name in item['emotes']:
            await member.remove_roles(
                member.guild.get_role(item['emotes'][reaction.emoji.name]),
                reason='Member undid a self-assign reaction'
            )


@bot.command(name='toggletalking')
@has_guild_permissions(manage_messages=True)
@commands.check(checks.invoked_in_club_cheadle)
async def toggle_talking(ctx: commands.Context):
    """Server Configuration
    Toggles YeloBot talking in #general.
    +toggletalking
    """
    global IS_TALKING
    collection = MONGO_DB['Talking']

    if await bot_is_talking():
        await reply(ctx, 'I will stop talking.')
    else:
        await reply(ctx, 'I will start talking again.')
    
    await collection.update_one({}, {'$set': {'talking': not IS_TALKING}})
    IS_TALKING = not IS_TALKING


@bot.command(name='joinrole', aliases=['defaultrole'])
@has_guild_permissions(manage_roles=True)
async def set_join_role(ctx: commands.Context, role_id=None):
    """Server Configuration
    Marks a specific role to be assigned to every user when they join the server.
    +joinrole <Role ID>
    """
    usage = '+joinrole <Role ID>'

    if role_id is None:
        await clear_join_role(ctx)
        return

    try:
        role_id = int(role_id)
    except ValueError:
        await reply(ctx, usage)
        return

    if discord.utils.get(ctx.guild.roles, id=role_id) is None:
        await reply(ctx, usage)
        return

    collection = MONGO_DB['JoinRole']
    doc = await collection.find_one({'server_id': ctx.guild.id})

    if doc is None:
        await collection.insert_one({'server_id': ctx.guild.id, 'role_id': role_id})
    else:
        await collection.update_one({'server_id': ctx.guild.id}, {'$set': {'role_id': role_id}})

    await reply(ctx, 'Join role set.')


async def clear_join_role(ctx: commands.Context):
    collection = MONGO_DB['JoinRole']
    if not await collection.find_one({'server_id': ctx.guild.id}):
        await reply(ctx, 'This server has no join role set.')
        return

    await collection.delete_one({'server_id': ctx.guild.id})
    await reply(ctx, 'Join role cleared.')


@bot.command(name='giveroletoall')
@has_guild_permissions(manage_roles=True)
async def give_role_to_all(ctx: commands.Context, role_id=None):
    """Server Configuration
    Gives the role to every server member.
    +giveroletoall <Role ID>
    """
    usage = '+giveroletoall <Role ID>'

    if role_id is None:
        await reply(ctx, usage)
        return

    try:
        role_id = int(role_id)
    except ValueError:
        await reply(ctx, usage)
        return

    role = discord.utils.get(ctx.guild.roles, id=role_id)

    if role is None:
        await reply(ctx, usage)
        return

    for member in ctx.guild.members:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            pass

    await reply(ctx, 'Gave every member this role. If any did not receive the role, it was due to permissions issues.')


@bot.command(name='emoterole', aliases=['addemoterole', 'addrole'])
@has_guild_permissions(manage_messages=True)
async def add_emote_role(ctx, channel_id=None, message_id=None, role_id=None, emote=None):
    """Server Configuration
    Marks a specific emote to assign the provided role to a user who reacts to the provided message
    using that emote.
    +emoterole <Channel ID> <Message ID> <Role ID> <Emote>
    """
    if channel_id is None or message_id is None or role_id is None or emote is None:
        await reply(ctx, 'Usage: +emoterole <CHANNEL ID> <MESSAGE ID> <ROLE ID> <EMOTE>')
        return

    try:
        message_id = int(message_id)
        role_id = int(role_id)
        assert emoji.demojize(emote) != emote
        assert yelobot_utils.get(ctx.guild.roles, id=role_id)
        channel = bot.get_channel(int(channel_id))
        assert isinstance(channel, discord.TextChannel)
        msg = await channel.fetch_message(message_id)
        assert msg
    except Exception as e:
        await ctx.send('Invalid argument(s).')
        print(formatted_exception(e))
        return

    collection = MONGO_DB['EmoteRoles']

    item = await collection.find_one({'message': message_id})

    if item:
        item['emotes'][emote] = role_id
        await collection.delete_many({'message': message_id})
    else:
        item = {'message': message_id, 'emotes': {emote: role_id}}

    await collection.insert_one(item)

    await reply(ctx, 'Done.')

######################### COUNTING ############################
# This should absolutely be in a separate file, but it isn't.

COUNTING_REACTIONS = {
    69: '♋',
    100: '💯',
    420: '🌿',
    666: '😈',
    911: '✈️',
    1000: '👏',
    1337: '😎',
    1984: '👁️',
    7310: '😶'
}
DEFAULT_COUNTING_REACTION = '✅'
RECORD_COUNTING_REACTION = '☑️'
GRACE_PERIOD_END_REACTION = '⚠️'
COUNTING_FAIL_REACTION = '❌'

async def process_counting(message, number):
    if message.author.bot:
        return

    collection = MONGO_DB['Counting']
    query = {'channel': message.channel.id}
    doc = await collection.find_one(query)
    if doc is None:
        return

    if message.author.id == doc['last_user'] or number != doc['count'] + 1:
        if message.author.id == doc['last_user']:
            reason_message = f'{message.author.mention} counted twice in a row! The next number is 1.'
        else:
            if doc['count'] == 0:
                return
            reason_message = f'{message.author.mention} doesn\'t know how to count! (The correct number was {doc["count"] + 1}, but they entered {number}). The next number is 1.'

        await message.add_reaction(COUNTING_FAIL_REACTION)
        await message.channel.send(reason_message)
        await punish_counting(message)
        await counting_stats(message, doc['count'] + 1, dict(doc['users']))
        await reset_counting(message)
        return

    record = number > doc['record']

    users = dict(doc['users'])
    old_user_num = users.setdefault(str(message.author.id), 0)
    users[str(message.author.id)] = old_user_num + 1
    if record:
        await collection.update_one({'server': message.guild.id}, {'$set': {'count': doc['count'] + 1, 'record': doc['count'] + 1, 'users': users, 'last_user': message.author.id, 'last_message': message.id}})
    else:
        await collection.update_one({'server': message.guild.id}, {'$set': {'count': doc['count'] + 1, 'users': users, 'last_user': message.author.id, 'last_message': message.id}})

    if doc['grace_period'] != 1 and doc['grace_period'] == number:
        reaction = GRACE_PERIOD_END_REACTION
    elif 'custom_reactions' in doc and str(number) in doc['custom_reactions']:
        reaction = doc['custom_reactions'][str(number)]
        default_emoji = True
        try:
            emote_id = int(reaction)
            default_emoji = False
        except Exception:
            pass

        if not default_emoji:
            reaction = yelobot_utils.get(message.guild.emojis, id=emote_id)
            if not reaction:
                await reply(message, 'Could not find the custom reaction emoji for this number (but still counted it).')
                return
    elif record:
        reaction = RECORD_COUNTING_REACTION
    elif number in COUNTING_REACTIONS:
        reaction = COUNTING_REACTIONS[number]
    else:
        reaction = DEFAULT_COUNTING_REACTION
    
    await message.add_reaction(reaction)

async def reset_counting(message):
    collection = MONGO_DB['Counting']
    await collection.update_one({'server': message.guild.id}, {'$set': {'count': 0, 'users': {}, 'last_user': 0}})

async def counting_stats(message, next_number, users):
    highest_user_id = 0
    highest_num = 0

    for user_id, count in users.items():
        if count > highest_num:
            highest_user_id = int(user_id)
            highest_num = count
    
    member = yelobot_utils.get(message.guild.members, id=highest_user_id)
    name = member.nick if member.nick else member.name
    await message.channel.send(f'{name} contributed the most with {highest_num} messages ({round(100 * highest_num / (next_number-1))}%).')

COUNTING_PUNISHMENT_TIMES = {
    1: 12 * 60 * 60,
    2: 24 * 60 * 60,
    3: 7 * 24 * 60 * 60,
    4: 30 * 24 * 60 * 60,
    5: 365 * 24 * 60 * 60
}

COUNTING_PUNISHMENT_STRINGS = {
    1: '12 hours',
    2: '24 hours',
    3: '7 days',
    4: '1 month',
    5: '1 year'
}

async def punish_counting(message):
    collection = MONGO_DB['CountingPunishments']
    counting_collection = MONGO_DB['Counting']
    doc = await collection.find_one({'server': message.guild.id})
    if not doc:
        return

    counting_doc = await counting_collection.find_one({'server': message.guild.id})

    next_number = counting_doc['count'] + 1

    if next_number < counting_doc['grace_period']:
        await message.channel.send(f'We did not pass the grace period of {counting_doc["grace_period"]}, so there is no punishment.')
        return
    
    punish_role = yelobot_utils.get(message.guild.roles, id=doc['role'])
    users = dict(doc['users'])
    if str(message.author.id) in users:
        punish_level = users[str(message.author.id)]['current_level'] + 1
    else:
        punish_level = 1
    
    time_to_remove = time.time() + COUNTING_PUNISHMENT_TIMES.setdefault(punish_level, COUNTING_PUNISHMENT_TIMES[5])
    users[str(message.author.id)] = {'time_to_remove': time_to_remove, 'current_level': punish_level}

    await collection.update_one({'server': message.guild.id}, {'$set': {'users': users}})

    member = yelobot_utils.get(message.guild.members, id=message.author.id)
    await member.add_roles(punish_role)
    await message.channel.send(f'{message.author.mention} will be punished for {COUNTING_PUNISHMENT_STRINGS.setdefault(punish_level, COUNTING_PUNISHMENT_TIMES[5])}.')
    if time_to_remove - time.time() < 86400:
        bot.loop.create_task(counting_punishment_thread(time_to_remove, message.guild.id, message.author.id, punish_role.id))
    

@bot.command(name='countingpunishment')
@has_guild_permissions(manage_messages=True)
async def set_counting_punishment_role(ctx, *, role_id=None):
    """Counting
    Sets the role that is given to users when they mess up counting.
    +countingpunishment <Role ID>
    """
    try:
        role_id = int(role_id)
    except:
        await ctx.send('Please enter a valid role ID number.')
        return
    
    role = yelobot_utils.get(ctx.guild.roles, id=role_id)

    if not role:
        await ctx.send('Please enter a valid role ID number.')
        return

    current_time = time.time()

    collection = MONGO_DB['CountingPunishments']
    doc = await collection.find_one({'server': ctx.guild.id})
    if doc:
        old_role = yelobot_utils.get(ctx.guild.roles, id=doc['role'])
        if old_role:
            users = dict(doc['users'])
            for user_id in users:
                member = yelobot_utils.get(ctx.guild.members, id=ctx.author.id)
                if member and users[str(user_id)]['time_to_remove'] > current_time:
                    member.remove_roles(old_role)
                    member.add_roles(role)
        await collection.update_one({'server': ctx.guild.id}, {'$set': {'role': role_id}})
    else:
        await collection.insert_one({'server': ctx.guild.id, 'role': role.id, 'users': {}})

    await reply(ctx, 'Counting punishment role set successfully.')


@bot.command(name='removecountingpunishments')
@has_guild_permissions(manage_messages=True)
async def remove_counting_punishments(ctx):
    """Counting
    Removes all of the counting punishments in the server.
    +removecountingpunishments
    """
    collection = MONGO_DB['CountingPunishments']
    doc = await collection.find_one({'server': ctx.guild.id})
    if not doc:
        return

    role = yelobot_utils.get(ctx.guild.roles, id=doc['role'])

    await collection.update_one({'server': ctx.guild.id}, {'$set': {'users': {}}})

    for member in ctx.guild.members:
        try:
            await member.remove_roles(role)
        except discord.HTTPException:
            pass
    
    await reply(ctx, 'Removed all counting punishments.')


@bot.command(name='countingstandings')
async def counting_standings(ctx):
    """Counting
    Displays a list of how long each user has last been punished for, and how long they have left (if applicable).
    +countingstandings
    """
    collection = MONGO_DB['CountingPunishments']
    doc = await collection.find_one({'server': ctx.guild.id})
    if not doc:
        return

    output = ''

    for user_id in doc['users']:
        member = yelobot_utils.get(ctx.guild.members, id=int(user_id))
        if member is None:
            continue
        name = member.nick if member.nick else member.name
        time_str = COUNTING_PUNISHMENT_STRINGS.setdefault(doc['users'][user_id]['current_level'], COUNTING_PUNISHMENT_STRINGS[5])
        output += f'{name} was punished for {time_str}\n'
        if doc["users"][user_id]["time_to_remove"] > time.time():
            output = output.rstrip() + f' ({yelobot_utils.time_remaining(doc["users"][user_id]["time_to_remove"])} remaining)\n'

    await reply(ctx, output.strip())


@bot.command(name='countingrecord', aliases=['countinghighscore', 'countinghigh', 'countingbest', 'countinghighest'])
async def counting_record(ctx):
    """Counting
    The current highest number reached in counting in this server.
    +countingrecord
    """
    collection = MONGO_DB['Counting']
    doc = await collection.find_one({'server': ctx.guild.id})

    if not doc:
        return

    await reply(ctx, f'The highest number reached so far is {doc["record"]}.')


@bot.command(name='countingreaction')
@has_guild_permissions(manage_messages=True)
async def set_counting_reaction(ctx, number=None, *, emote=None):
    """Counting
    Sets a custom reaction emote for a number in counting.
    +countingreaction <Number> <Emote>
    """
    usage = '+countingreaction <number> <emote>'

    if number is None:
        await reply(ctx, usage)
        return

    try:
        int(number)
    except Exception:
        await reply(ctx, usage)
        return
    
    collection = MONGO_DB['Counting']
    doc = await collection.find_one({'server': ctx.guild.id})

    if not doc:
        await reply(ctx, 'This server has no counting channel set.')
        return

    if 'custom_reactions' not in doc:
        collection.update_one({'server': ctx.guild.id}, {'$set': {'custom_reactions': dict()}})

    if emote is None:
        await collection.update_one({'server': ctx.guild.id}, {'$unset': {f'custom_reactions.{number}': ''}})
    elif emoji.is_emoji(emote):
        await collection.update_one({'server': ctx.guild.id}, {'$set': {f'custom_reactions.{number}': emote}})
    else:
        mo = re.match(r'^<a?:.+:(\d+)>$', emote)
        if not mo:
            await reply(ctx, usage)
            return
        
        emote_id = int(mo.group(1))
        emote_obj = yelobot_utils.get(ctx.guild.emojis, id=emote_id)
        
        if emote_obj is None:
            await reply(ctx, usage)
            return
        
        await collection.update_one({'server': ctx.guild.id}, {'$set': {f'custom_reactions.{number}': emote_id}})

    await reply(ctx, 'Custom reaction updated.')


@bot.command(name='countingchannel')
@has_guild_permissions(manage_messages=True)
async def set_counting_channel(ctx, *, channel):
    """Counting
    Sets the channel used for counting in this server.
    +countingchannel #<Channel>|<Channel ID>
    """
    try:
        channel_id = int(channel.lstrip('<#').rstrip('>'))
        channel = bot.get_channel(channel_id)
    except:
        channel = None

    if channel is None or channel.guild != ctx.guild:
        await reply(ctx, 'Invalid channel. Please use #channel_name, or the channel ID.')
        return

    collection = MONGO_DB['Counting']
    server_doc = await collection.find_one({'server': ctx.guild.id})

    if server_doc is not None:
        server_doc = dict(server_doc)
        if server_doc['channel'] == channel_id:
            await reply(ctx, 'This is already the counting channel.')
            return
        await collection.delete_one(server_doc)
        server_doc['channel'] = channel_id
        for_new_channel = f'Counting has been moved to this channel. The next number is {server_doc["count"] + 1}.'
        if server_doc['last_user'] != 0:
            last_counter = yelobot_utils.get(bot.get_all_members(), id=server_doc["last_user"], guild=ctx.guild)
            last_counter_name = last_counter.nick if last_counter.nick else last_counter.name
            for_new_channel += f' The last user to count was {last_counter_name}.'
        await channel.send(for_new_channel)
    else:
        server_doc = {'server': ctx.guild.id, 'channel': channel_id, 'count': 0, 'record': 0, 'users': {}, 'last_user': 0, 'grace_period': 1, 'last_message': 0}
        await channel.send('Welcome to the counting channel! Type "1" to begin.')

    await collection.insert_one(server_doc)
    await reply(ctx, f'<#{channel_id}> has been set as the counting channel.')


@bot.command(name='countinggraceperiod', aliases=['grace'])
@has_guild_permissions(manage_messages=True)
async def set_counting_grace_period(ctx, *, period=None):
    """Counting
    Sets the grace period for counting. Users who mess up before this number is reached will not be punished.
    +countinggraceperiod <Number>
    """
    try:
        period = int(period)
    except:
        await ctx.send('Please enter a valid number.')
        return

    collection = MONGO_DB['Counting']
    server_doc = await collection.find_one({'server': ctx.guild.id})

    if not server_doc:
        await reply(ctx, 'Please set a counting channel first, using +countingchannel [channel].')
        return
    
    await collection.update_one({'server': ctx.guild.id}, {'$set': {'grace_period': period}})
    await reply(ctx, 'Grace period updated successfully.')


async def counting_punishment_thread(time_set, guild_id, user_id, role_id):
    server = bot.get_guild(guild_id)
    member = yelobot_utils.get(server.members, id=user_id)
    if not member: # CHANGE THIS -- currently if someone is not in the server while their punishment expires,
        return     #  the role will still be added when they rejoin

    role = yelobot_utils.get(server.roles, id=role_id)

    if time_set - time.time() > 0.1:
        await asyncio.sleep(time_set - time.time())

    await member.remove_roles(role)
    await member.send(f'You can now return to counting in **{server.name}**.')

@StartupTask
async def init_counting_punishments():
    await asyncio.sleep(5) # Wait for the bot to initialize
    collection = MONGO_DB['CountingPunishments']

    to_add = []

    for item in await (collection.find().to_list(None)):
        item = dict(item)
        for user_id in item['users']:
            try:
                server = await bot.fetch_guild(int(item['server']))
                await server.fetch_member(int(user_id))
            except:
                continue
            if 0 < item['users'][user_id]['time_to_remove'] - time.time() < 86400:
                to_add.append([float(item['users'][user_id]['time_to_remove']), int(item['server']), int(user_id), int(item['role'])])

    print(f'Initializing {len(to_add)} counting punishments')
    await asyncio.gather(*[counting_punishment_thread(t, g, u, r) for t, g, u, r in to_add])


##################### END COUNTING ############################

@bot.command(name='settimezone', aliases=['timezone'])
async def set_timezone(ctx, *, tz=None):
    """Time/Reminders
    Sets a timezone. This will be used for +time, +remindme, etc.
    Please enter a location (doesn't have to be too specific), not an actual timezone name.
    +settimezone <Location>
    """
    if tz is None:
        await ctx.send('+settimezone <location>')
    try:
        nm_response = nominatim.query(tz)
    except nominatim.NominatimStatusCodeError as e:
        await ctx.send(formatted_exception(e))
        return

    if len(nm_response) == 0:
        await ctx.send('Please specify a valid location (not a timezone abbreviation; just a location, eg. Sydney or California)')
        return

    collection = MONGO_DB['Timezones']

    timezone = timezones.tz_from_location(nm_response[0]['lat'], nm_response[0]['lon'])
    
    msg_sent = await ctx.send(
        f'The location found was: {nm_response[0]["display_name"]}\n' +
        f'The corresponding timezone is {timezone} (currently {timezones.abbreviation_from_tz(timezone)}).\n' +
        '**If this is correct, click the checkmark.** Otherwise, try again.'
    )

    doc = await collection.find_one({'user_id': ctx.author.id})

    if doc is None:
        await collection.insert_one(
            {
                'user_id': ctx.author.id,
                'is_set': False,
                'timezone': timezone,
                'message_id': msg_sent.id,
                'ddmmyy': False
            }
        )
    else:
        await collection.update_one(doc,
            {
                '$set':
                {'is_set': False, 'timezone': timezone, 'message_id': msg_sent.id}
            }
        )

    await msg_sent.add_reaction('✅')

async def confirm_timezone(user_id, channel):
    collection = MONGO_DB['Timezones']
    await collection.update_one({'user_id': user_id},
        {
            '$set': {'is_set': True}
        }
    )

    await channel.send('Your timezone was successfully added.') # TODO modify this to include the user's name


@bot.command(name='dateformat')
async def set_date_format(ctx, *, format=None):
    """Time/Reminders
    Sets a format for displaying dates for you. Can be dd/mm/yyyy or mm/dd/yyyy.
    +dateformat <Format>
    """
    if format.lower() == 'dd/mm/yyyy' or format.lower() == 'dd/mm':
        ddmmyy = True
    elif format.lower() == 'mm/dd/yyyy' or format.lower() == 'mm/dd':
        ddmmyy = False
    else:
        await ctx.send('Please specify "dd/mm/yyyy" or "mm/dd/yyyy".')
        return

    collection = MONGO_DB['Timezones']
    doc = await collection.find_one({'user_id': ctx.author.id})

    if doc is None:
        await collection.insert_one(
            {
                'user_id': ctx.author.id,
                'is_set': False,
                'timezone': '',
                'message_id': 0,
                'ddmmyy': ddmmyy
            }
        )
    else:
        await collection.update_one({'user_id': ctx.author.id},
            {'$set': {'ddmmyy': ddmmyy}}
        )

    await reply(ctx, 'Preference updated.')


# Tic Tac Toe commands should also be in a separate file.

TTT_GAME_EXPIRATION_TIME = 5 * 60
TTT_INVITE_EXPIRATION_TIME = 60


@bot.command(name='tictactoe', aliases=['ttt', 'xo', 'ox'])
async def tic_tac_toe(ctx, row=None, col=None):
    """Games
    Make a Tic-Tac-Toe move.
    +tictactoe <Row> <Column>
    """
    collection = MONGO_DB['TicTacToe']
    query = {'server': ctx.message.guild.id}
    server_doc = await collection.find_one(query)
    if server_doc is None:
        await ctx.send('You are not currently in a Tic Tac Toe game. Use +tttinvite to invite someone.')
        return

    for i_game in server_doc['games']:
        if i_game['x'] == ctx.author.id:
            game_doc = i_game
            player_x = ctx.author
            player_o = yelobot_utils.get(bot.get_all_members(), id=game_doc['o'], guild=ctx.message.guild)
            break
        elif i_game['o'] == ctx.author.id:
            game_doc = i_game
            player_x = yelobot_utils.get(bot.get_all_members(), id=game_doc['x'], guild=ctx.message.guild)
            player_o = ctx.author
            break
    else:
        await ctx.send('You are not currently in a Tic Tac Toe game. Use +tttinvite to invite someone.')
        return

    if row is None or col is None:
        await ctx.send('Use +ttt [row] [col] to make your move!')
        return

    try:
        row = int(row)
        col = int(col)
    except:
        await ctx.send('Row and column must be valid numbers between 1 and 3.')
        return
    
    if not (1 <= row <= 3 and 1 <= col <= 3):
        await ctx.send('Row and column must be between 1 and 3.')
        return

    game = TicTacToe(game_doc['board'])

    if ctx.author == player_x:
        player_piece = game.X
    else:
        player_piece = game.O

    try:
        game.take_turn(player_piece, row - 1, col - 1)
    except TicTacToeWrongPlayerError:
        await ctx.send('It\'s not your turn!')
        return
    except TicTacToeInvalidMoveError:
        await ctx.send('This is an invalid move.')
        return
    except Exception as e:
        await ctx.send('An unknown error has occured... please ask Yelo to take a look at this')
        print(formatted_exception(e))
        return

    if game.check_game_over():
        await ctx.send(f'```{str(game)}```')
        await ctx.send('GAME OVER!')
        await collection.update_one(query, {'$pull': {'games': game_doc}})
    elif game.board_full():
        await ctx.send(f'```{str(game)}```')
        await ctx.send('DRAW!')
        await collection.update_one(query, {'$pull': {'games': game_doc}})
    else:
        await ctx.send(f'```{str(game)}```')
        if ctx.author == player_x:
            await ctx.send(f'{player_o.nick if player_o.nick else player_o.name}\'s turn! (**O**)')
        else:
            await ctx.send(f'{player_x.nick if player_x.nick else player_x.name}\'s turn! (**X**)')
        expires = time.time() + TTT_GAME_EXPIRATION_TIME
        await collection.update_one({'server': ctx.guild.id, 'games': game_doc}, {'$set': {'games.$': {
            'x': player_x.id,
            'o': player_o.id,
            'board': game.get_game_list(),
            'channel': ctx.message.channel.id,
            'expires': expires}}})
        await tic_tac_toe_game_thread(expires, ctx.message.channel.id, player_x.id, player_o.id)


@bot.command(name='tictactoeleave', aliases=['tictactoeforfeit', 'tttleave', 'tttforfeit'])
async def tic_tac_toe_leave(ctx):
    """Games
    Forfeit a Tic-Tac-Toe game.
    +tictactoeleave
    """
    collection = MONGO_DB['TicTacToe']
    query = {'server': ctx.message.guild.id}
    server_doc = await collection.find_one(query)
    if server_doc is None:
        await reply(ctx, 'You are not in a Tic Tac Toe game.')
        return

    for i_game in server_doc['games']:
        if i_game['x'] == ctx.author.id:
            game = i_game
            player_is_x = True
            break
        elif i_game['o'] == ctx.author.id:
            game = i_game
            player_is_x = False
            break
    else:
        await reply(ctx, 'You are not in a Tic Tac Toe game.')
        return

    opponent = yelobot_utils.get(bot.get_all_members(), id=(game['o'] if player_is_x else game['x']), guild=ctx.message.guild)
    await ctx.send(f'{opponent.nick if opponent.nick else opponent.name} wins!')
    await collection.update_one(query, {'$pull': {'games': game}})


@bot.command(name='tictactoeinvite', aliases=['tttinvite', 'tttinv', 'tictactoeinv'])
async def tic_tac_toe_invite(ctx, *, user=None):
    """Games
    Invite someone to a Tic-Tac-Toe game.
    +tictactoeinvite <User>
    """
    if user is None:
        await ctx.send('Use +tttinvite [name] to invite someone to a Tic Tac Toe game.')
        return

    member = search_for_user(ctx, user)
    if not member:
        await ctx.send('Could not find that user.')
        return

    if member.id == ctx.author.id:
        await ctx.send('You can\'t invite yourself. Thanks John.')
        return

    collection = MONGO_DB['TicTacToe']

    server_query = {'server': ctx.guild.id}
    server_doc = await collection.find_one(server_query)

    if server_doc is None:
        server_doc = {'server': ctx.guild.id, 'invites': [], 'games': []}
        await collection.insert_one(server_doc)

    author_in_game = len(server_doc['games']) > 0 and any(game['x'] == ctx.author.id or game['o'] == ctx.author.id for game in server_doc['games'])

    if author_in_game:
        await reply(ctx, 'You can\'t invite someone when you are already in a game!')
        return

    already_invited = len(server_doc['invites']) > 0 and any([invite['to'] == member.id for invite in server_doc['invites']])

    if already_invited:
        await reply(ctx, 'That user already has a pending invitation...')
        return

    other_in_game = len(server_doc['games']) > 0 and any(game['x'] == member.id or game['o'] == member.id for game in server_doc['games'])

    if other_in_game:
        await reply(ctx, f'{member.nick if member.nick else member.name} is already in a Tic Tac Toe game.')

    expires = time.time() + TTT_INVITE_EXPIRATION_TIME
    await collection.update_one(server_query, {'$push': {'invites': {'to': member.id, 'from': ctx.author.id, 'expires': expires, 'channel': ctx.message.channel.id}}})
    await ctx.send(f'{member.mention}, {ctx.author.nick if ctx.author.nick else ctx.author.name} has invited you to Tic Tac Toe. Use +tttaccept or +tttdecline.')
    await tic_tac_toe_invite_thread(expires, ctx.message.channel.id, ctx.author.id, member.id)


@bot.command(name='tictactoeaccept', aliases=['tttaccept'])
async def tic_tac_toe_accept(ctx):
    """Games
    Accept an invitation to a Tic-Tac-Toe game.
    +tictactoeaccept
    """
    collection = MONGO_DB['TicTacToe']
    query = {'server': ctx.guild.id}
    server_doc = await collection.find_one(query)

    if server_doc is None:
        await reply(ctx, 'You have not been invited to a Tic Tac Toe game.')
        return

    for invite in server_doc['invites']:
        if invite['to'] == ctx.author.id:
            invitation = invite
            break
    else:
        await reply(ctx, 'You have not been invited to a Tic Tac Toe game.')
        return

    await collection.update_one(query, {'$pull': {'invites': {'to': ctx.author.id, 'from': invitation['from'], 'expires': invitation['expires'], 'channel': invitation['channel']}}})

    from_starts = random.random() > .5

    game = TicTacToe()

    expires = time.time() + TTT_GAME_EXPIRATION_TIME
    await collection.update_one(query, {'$push': {'games': {
        'x': invitation['from'] if from_starts else invitation['to'],
        'o': invitation['to'] if from_starts else invitation['from'],
        'board': game.get_game_list(),
        'channel': ctx.message.channel.id,
        'expires': expires
        }}})

    from_member = yelobot_utils.get(bot.get_all_members(), id=int(invitation['from']), guild=ctx.message.guild)

    from_name = from_member.nick if from_member.nick else from_member.name
    to_name = ctx.author.nick if ctx.author.nick else ctx.author.name

    x_name = from_name if from_starts else to_name
    o_name = to_name if from_starts else from_name

    await ctx.send(f'{x_name} is X, {o_name} is O')
    await ctx.send(f'```{str(game)}```')
    await ctx.send(f'{x_name}\'s turn! (**X**) Use +ttt [row] [column].')
    await tic_tac_toe_game_thread(expires, ctx.message.channel.id, from_member.id if from_starts else ctx.author.id, ctx.author.id if from_starts else from_member.id)


@bot.command(name='tictactoedecline', aliases=['tictactoedeny', 'tttdecline', 'tttdeny'])
async def tic_tac_toe_decline(ctx):
    """Games
    Decline an invitation to a Tic-Tac-Toe game.
    +tictactoedecline
    """
    collection = MONGO_DB['TicTacToe']
    query = {'server': ctx.guild.id}
    server_doc = await collection.find_one(query)

    if server_doc is None:
        await reply(ctx, 'You have not been invited to a Tic Tac Toe game.')
        return

    for invite in server_doc['invites']:
        if invite['to'] == ctx.author.id:
            invitation = invite
            break
    else:
        await reply(ctx, 'You have not been invited to a Tic Tac Toe game.')
        return

    await collection.update_one(query, {'$pull': {'invites': {'to': ctx.author.id, 'from': invitation['from'], 'expires': invitation['expires'], 'channel': invitation['channel']}}})
    from_member = yelobot_utils.get(bot.get_all_members(), id=int(invitation['from']), guild=ctx.message.guild)

    await reply(ctx, f'You have declined {from_member.nick if from_member.nick else from_member.name}\'s Tic Tac Toe invitation.')


async def tic_tac_toe_invite_thread(time_set, channel_id, from_id, to_id):
    channel = yelobot_utils.get(bot.get_all_channels(), id=channel_id)
    server = channel.guild
    from_member = yelobot_utils.get(bot.get_all_members(), id=from_id, guild=server)
    to_member = yelobot_utils.get(bot.get_all_members(), id=to_id, guild=server)

    if time_set - time.time() > 0:
        await asyncio.sleep(time_set - time.time())

    collection = MONGO_DB['TicTacToe']
    query = {'server': server.id}
    server_doc = await collection.find_one(query)

    invite_still_here = len(server_doc['invites']) > 0 and \
        any([invite['to'] == to_id and invite['from'] == from_id and invite['expires'] == time_set and invite['channel'] == channel_id \
        for invite in server_doc['invites']])

    if invite_still_here:
        await collection.update_one(query, {'$pull': {'invites': {'to': to_id, 'from': from_id, 'expires': time_set, 'channel': channel_id}}})
        from_name = from_member.nick if from_member.nick else from_member.name
        to_name = to_member.nick if to_member.nick else to_member.name
        await channel.send(f'{from_name}\'s Tic Tac Toe invite to {to_name} has expired.')

@StartupTask
async def init_tic_tac_toe_invites():
    await asyncio.sleep(5)

    to_init = []
    collection = MONGO_DB['TicTacToe']

    for server_doc in await (collection.find()).to_list(None):
        for invite in server_doc['invites']:
            to_init.append([invite['expires'], invite['channel'], invite['from'], invite['to']])

    print(f'Initializing {len(to_init)} Tic Tac Toe invites.')

    asyncio.gather(*[tic_tac_toe_invite_thread(e, c, f, t) for e, c, f, t in to_init])


async def tic_tac_toe_game_thread(time_set, channel_id, player_x_id, player_o_id):
    channel = yelobot_utils.get(bot.get_all_channels(), id=channel_id)
    server = channel.guild
    x_member = yelobot_utils.get(bot.get_all_members(), id=player_x_id, guild=server)
    o_member = yelobot_utils.get(bot.get_all_members(), id=player_o_id, guild=server)

    if time_set - time.time() > 0:
        await asyncio.sleep(time_set - time.time())

    collection = MONGO_DB['TicTacToe']
    query = {'server': server.id}
    server_doc = await collection.find_one(query)

    game_unchanged = False
    for game in server_doc['games']:
        if game['x'] == player_x_id and game['o'] == player_o_id and game['expires'] == time_set and game['channel'] == channel_id:
            game_unchanged = True
            break

    if game_unchanged:
        await collection.update_one(query, {'$pull': {'games': {'x': player_x_id, 'o': player_o_id, 'expires': time_set}}})

        x_name = x_member.nick if x_member.nick else x_member.name
        o_name = o_member.nick if o_member.nick else o_member.name
        await channel.send(f'The Tic Tac Toe game between {x_name} and {o_name} has expired.')

@StartupTask
async def init_tic_tac_toe_games():
    await asyncio.sleep(5)

    to_init = []
    collection = MONGO_DB['TicTacToe']

    for server_doc in await (collection.find()).to_list(None):
        for invite in server_doc['games']:
            to_init.append([invite['expires'], invite['channel'], invite['x'], invite['o']])

    print(f'Initializing {len(to_init)} Tic Tac Toe games.')

    asyncio.gather(*[tic_tac_toe_game_thread(e, c, x, o) for e, c, x, o in to_init])

    

@bot.command(name='nowplaying', aliases=['np'])
async def now_playing(ctx, s_member=None):
    """Utility
    Display the given user's Spotify playing status. Leave the User argument blank to display your own status.
    +nowplaying [User]
    """
    song = None

    if s_member is None:
        member = ctx.author
    elif len(ctx.message.mentions) > 0:
        member = ctx.message.mentions[0]
    else:
        member = search_for_user(ctx, s_member)

    if not member:
        await ctx.send('Who?')
        return

    for activity in member.activities:
        if type(activity == discord.activity.Spotify):
            song = activity

    if song is None:
        await ctx.send('This user is not currently listening to Spotify.')
    else:
        artists = song.artists[0]
        if len(song.artists) > 1:
            for song_artist in song.artists[1:]:
                artists += ', ' + song_artist

        embed = discord.Embed(
            title=member.display_name,
            colour=discord.Colour.green()
        )
        embed.add_field(name='Title', value=song.title, inline=False)
        embed.add_field(name='Artist(s)', value=artists, inline=False)
        embed.add_field(name='Album', value=song.album, inline=False)

        embed.set_thumbnail(url=song.album_cover_url)
        await ctx.send(embed=embed)


@bot.command(name='wikipedia', aliases=['wiki'])
async def wikipedia_search(ctx, *, input_query):
    """Utility
    Search for a Wikipedia page. Warning: this API fucking sucks and is very buggy.
    +wikipedia <Query>
    """
    try:
        output = ''
        for character in wikipedia.summary(input_query):
            if character == '\n':
                break
            else:
                output += character
        page = wikipedia.page(input_query)
        output += f'\n\nRead the full article here:\n<{page.url}>'
        await reply(ctx, output)
    except wikipedia.exceptions.DisambiguationError as e:
        send_string = e.options[0]
        for option in e.options[1:]:
            send_string += ', ' + option
        await reply(ctx, f'{input_query} could refer to:\n{send_string}')
    except wikipedia.exceptions.PageError:
        await reply(ctx, "That page doesn't exist.")
    except:
        await reply(ctx, 'This page is probably too long or something idk this api sucks')


@bot.command(name='youtube', aliases=['yt'])
async def youtube_search(ctx, *, input_query):
    """Utility
    Search for a YouTube video.
    +youtube <Query>
    """
    query = ''
    for character in input_query:
        if character == ' ':
            query += '+'
        else:
            query += character
    search_html = urllib.request.urlopen(f'https://www.youtube.com/results?search_query={query}')
    video_ids = re.findall(r'watch\?v=(\S{11})', search_html.read().decode())
    await reply(ctx, 'https://www.youtube.com/watch?v=' + video_ids[0])


@bot.command(name='minecraft', aliases=['mc'])
@commands.check(checks.invoked_in_club_cheadle)
async def minecraft(ctx):
    """Minecraft
    Get the current status of the Minecraft server.
    Warning: if we do not currently have a Minecraft server, this command may sometimes say that the server is on.
    +minecraft
    """
    if ctx.message.guild.id != LWOLF_SERVER_ID:
        return
    try:
        server = JavaServer(MINECRAFT_IP, MC_PORT)
        status = server.status()

        to_send = f'🟢 The Minecraft server is up at `{MINECRAFT_HOST}` for Minecraft {status.version.name} with `{status.players.online}` players online.'
        if status.version.name == '1.12.2':
            to_send += '\nLooks like we are currently running Pixelmon. For instructions on installation, use +pixelmon.'
        elif status.version.name == '1.10.2':
            to_send += '\nLooks like we are currently running our custom modpack. For installation instructions, use +modpack.'

        await ctx.send(to_send)
    except socket.timeout:
        await ctx.send('🔴 The Minecraft server is not currently running.')
    except ConnectionRefusedError:
        await ctx.send('🔴 The Minecraft server is not currently running.')
    except Exception as e:
        await ctx.send('🟡 ERROR (no idea if server is up or not)')
        print(type(e), e)


@bot.command(name='minecraftplayers', aliases=['mcplayers'])
@commands.check(checks.invoked_in_club_cheadle)
async def minecraft_players(ctx):
    """Minecraft
    List the players currently in the Minecraft server.
    +minecraftplayers
    """
    if ctx.message.guild.id != LWOLF_SERVER_ID:
        return
    
    try:
        server = JavaServer(MINECRAFT_IP, MC_PORT)
        status = server.status()
        players_string = ''

        if status.players.sample is not None:
            for player in status.players.sample:
                players_string += player.name + ', '

        if players_string:
            if status.players.online > 1:
                await ctx.send(f'There are `{status.players.online}` players online: `{players_string[:-2]}`.')
            else:
                await ctx.send(f'There is `1` player online: `{players_string[:-2]}`.')
        else:
            await ctx.send('There are zero players online.')

    except socket.timeout:
        await ctx.send('The Minecraft server is offline.')
    except ConnectionRefusedError:
        await ctx.send('The Minecraft server is offline.')
    except Exception as e:
        etype = str(type(e)).lstrip('<class \'').rstrip('\'>')
        await ctx.send(f'{etype}: {e}')


@tasks.loop(seconds=15.0)
async def check_minecraft_events():
    global MC_PLAYERS_SET
    try:
        server = JavaServer(MINECRAFT_IP, MC_PORT)
        status = server.status()
    except Exception as e:
        etype = str(type(e)).lstrip('<class \'').rstrip('\'>')
        print(f'check_minecraft_events: {etype}: {e}')
        return

    current_players_set = set()

    if status.players.sample is None:
        status.players.sample = set()

    for player in status.players.sample:
        player = str(player.name)
        if player not in MC_PLAYERS_SET:
            await CHANNEL_FOR_MC_PLAYERS.send(f'`{player}` joined the Minecraft server.')
        current_players_set.add(player)

    for player in MC_PLAYERS_SET:
        if player not in current_players_set:
            await CHANNEL_FOR_MC_PLAYERS.send(f'`{player}` left the Minecraft server.')

    MC_PLAYERS_SET = current_players_set


@check_minecraft_events.before_loop
async def before_check_minecraft_events():
    global MC_PLAYERS_SET, CHANNEL_FOR_MC_PLAYERS

    await bot.wait_until_ready()
    CHANNEL_FOR_MC_PLAYERS = bot.get_channel(CHANNEL_FOR_MC_PLAYERS_ID)

    try:
        server = JavaServer(MINECRAFT_IP, MC_PORT)
        status = server.status()
    except Exception as e:
        etype = str(type(e)).lstrip('<class \'').rstrip('\'>')
        print(f'before_check_minecraft_events: {etype}: {e}')
        return

    if status.players.sample is None:
        status.players.sample = set()

    for player in status.players.sample:
        MC_PLAYERS_SET.add(str(player.name))
    

@bot.command(name='tellminecraft', aliases=['tellmc', 'chatmc', 'chatminecraft'])
@commands.check(checks.invoked_in_club_cheadle)
async def tell_minecraft(ctx, *, message):
    """Minecraft
    Send a message to the players in the Minecraft server.
    +tellminecraft <Message>
    """
    if ctx.message.guild.id != LWOLF_SERVER_ID and ctx.message.guild.id != 764984305696636939:
        return

    if not message:
        await ctx.send('Usage: +tellminecraft [message]')
        return

    name = ctx.author.name

    try:
        with MCRcon(MINECRAFT_IP, RCON_PASSWORD, port=RCON_PORT) as mcr:
            try:
                mcr.command(f'tellraw @a "D<{name}> {message}"')
                await ctx.send('Message sent.')
            except Exception as e:
                await ctx.send(f'Failed to send the message:\n{formatted_exception(e)}')
    except:
        await ctx.send('Could not connect.')
    

@bot.command(name='servericon')
async def server_icon(ctx):
    """Utility
    Post the icon of the server.
    +servericon
    """
    try:
        await reply(ctx, ctx.guild.icon.url)
    except:
        await reply(ctx, "This server doesn't have an icon.")


@bot.command(name='ranks', aliases=['levels'], hidden=True)
@commands.check(checks.invoked_in_club_cheadle)
async def ranks(ctx):
    if ctx.message.guild.id != LWOLF_SERVER_ID:
        return
    await reply(ctx, 'use +i ranks instead')


@bot.command(name='rank', hidden=True)
@commands.check(checks.invoked_in_club_cheadle)
async def rank(ctx: commands.Context):
    if ctx.guild.id != LWOLF_SERVER_ID:
        return
    
    await reply(ctx, 'it\'s /rank idiot')


@bot.command(name='worldrecord', aliases=['wr', 'record', 'besttime', 'speedrun'])
async def srcwr(ctx, *, game_name=None):
    """Utility
    Get the world record of a game's default category speedrun on speedrun.com.
    This may or may not work super well.
    +worldrecord <Game>
    """
    def format_record_time(rtime):
        regex = re.match(r'^PT[.|]*(?P<hour>(\d+H)?)(?P<min>(\d+M)?)(?P<sec>(\d+S)?)', rtime)

        return_str = ''
        if regex.group('hour'):
            return_str += regex.group('hour')[0:-1] + 'h'
        if regex.group('min'):
            return_str += regex.group('min')[0:-1] + 'm'
        if regex.group('sec'):
            return_str += regex.group('sec')[0:-1] + 's'
        return return_str

    async def get_category_name(cat_id):
        async with bot.aiohttp_sess.get('https://www.speedrun.com/api/v1/categories/' + cat_id) as res:
            cat = await res.json()
        return cat['data']['name']

    async def get_user_name(usr_id):
        async with bot.aiohttp_sess.get('https://www.speedrun.com/api/v1/users/' + usr_id) as res:
            usr = await res.json()
        return usr['data']['names']['international']

    async with bot.aiohttp_sess.get('https://www.speedrun.com/api/v1/games?', params={'name': game_name}) as response:
        if response.status != 200:
            await reply(ctx, 'Could not find this game. Either it does not exist, or there was an API issue.')
            return

        try:
            game = await response.json()
        except:
            await reply(ctx, 'uh oh OOPSIE THERE WAS A FUCKY WHEN DECODING JSON DATA FROM THE API AHFIAHFHAH')
            return

    for l in game['data'][0]['links']:
        if l['rel'] == 'records':
            records_uri = l['uri'] + '?'

    async with bot.aiohttp_sess.get(records_uri, params={'top': 1, 'scope': 'full-game', 'skip-empty': True}) as response:
        if response.status != 200:
            await reply(ctx, 'the api is fucked lol sorry')
            return

        records = await response.json()

    record = records['data'][0]['runs'][0]['run']
    record_time_formatted = format_record_time(record['times']['primary'])
    record_url = record['weblink']
    category = get_category_name(record['category'])
    user = get_user_name(record['players'][0]['id'])
    real_game_name = game['data'][0]['names']['international']

    await reply(ctx, f'The World Record for **{real_game_name} {category}** is **{record_time_formatted}** by **{user}**'
                   + f'\n{record_url}')


@bot.command(name='egsfree', aliases=['egs', 'epic', 'freeegs', 'freeepic', 'epicfree', 'free', 'freegames'])
async def egs_free(ctx):
    """Video Games
    Get a list of the current free games on the Epic Games store.
    This is done in a very hacky way and is often not entirely accurate.
    +egsfree
    """
    request_url = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US' \
                  '&allowCountries=US'
    async with bot.aiohttp_sess.get(request_url) as response:
        if response.status != 200:
            await ctx.send(f'Oops, response came back with code {response.status_code} @YeloFelo#8879')
            return
        rjson = await response.json()

    free_games_str = 'The current free games on the Epic Games Store are'

    free_game_found = False

    for game in rjson['data']['Catalog']['searchStore']['elements']:
        if game['price']['totalPrice']['discountPrice'] == 0 and game['price']['totalPrice']['originalPrice'] != 0:
            free_games_str += f' **{game["title"]}**,'
            free_game_found = True

    if free_game_found:
        await ctx.send(free_games_str.rstrip(',') + '.')
    else:
        await ctx.send('There are currently no limited-time free game offers on the Epic Games Store.')


@bot.command(name='setcountry')
async def set_country(ctx, *, country=None):
    """Video Games
    Set your country. This is currently only used to convert currencies for +steamprice.
    +setcountry <country>
    """
    if country is None:
        await reply(ctx, '+setcountry <country>')
        return
    
    with open('country_codes.json', 'r') as f:
        data = json.load(f)

    lower_country = country.lower()

    if lower_country not in data:
        await reply(ctx, 'Country not found.')
        return

    collection = MONGO_DB['Countries']

    doc = await collection.find_one({'user_id': ctx.author.id})

    if not doc:
        await collection.insert_one({'user_id': ctx.author.id, 'country': data[lower_country]})
    else:
        await collection.update_one({'user_id': ctx.author.id}, {'$set': {'country': data[lower_country]}})

    await reply(ctx, 'Country updated.')


@bot.command(name='steamprice', aliases=['price'])
async def steam_price(ctx, *, game):
    """Video Games
    Get the price of a Steam game. Use +setcountry to have it appear in your currency.
    +steamprice <Game>
    """
    async with bot.aiohttp_sess.get('https://store.steampowered.com/search/', params={'term': game}) as search_response:
        search_soup = BeautifulSoup(await search_response.content.read(), 'html.parser')

    search_results = search_soup.find(id='search_resultsRows')

    if search_results is None:
        await reply(ctx, 'Zero results found.')
        return

    result_list = search_results.find_all('a')

    filtered_results = []
    i = 0
    while len(filtered_results) < 20 and len(result_list) > i:
        if 'data-ds-appid' not in result_list[i].attrs:
            i += 1
            continue
        if not result_list[i]['href'].startswith('https://store.steampowered.com/app/'):
            i += 1
            continue
        if result_list[i].find('span', {'class': 'platform_img music'}):
            i += 1
            continue

        search_price_results = result_list[i].find('div', {'class': 'search_price'})

        if search_price_results is not None and search_price_results.text.strip() == '':
            i += 1
            continue

        search_price_discount_combined_results = result_list[i].find('div', {'class': 'search_price_discount_combined'})

        if search_price_discount_combined_results is not None and search_price_discount_combined_results.text.strip() == '':
            i += 1
            continue

        if search_price_results is None and search_price_discount_combined_results is None:
            i += 1
            continue

        filtered_results.append(str(result_list[i]['data-ds-appid']))
        i += 1

    async def pagination_callback(app_id):
        collection = MONGO_DB['Countries']

        currency = 'us'
        doc = await collection.find_one({'user_id': ctx.author.id})
        if doc:
            currency = doc['country']

        details_params = {'appids': app_id, 'l': 'en_us', 'cc': currency}
        url = 'https://store.steampowered.com/api/appdetails?'
        response = requests.get(url, params=details_params)

        if response.status_code != 200:
            return f'{response.status_code} error; could not retrieve this result right now.'

        details_data_json = response.json()

        app_name = details_data_json[app_id]['data']['name']

        output_string = f'[{app_name}](https://store.steampowered.com/app/{app_id}/)\n'

        if details_data_json[app_id]['data']['release_date']['coming_soon']:
            return output_string + 'Coming soon.'

        if not details_data_json[str(app_id)]['data']['is_free']:
            if not 'price_overview' in details_data_json[str(app_id)]['data']:
                return 'ERROR: no price_overview in JSON'
                
            pricing = details_data_json[str(app_id)]['data']['price_overview']

        if details_data_json[str(app_id)]['data']['is_free']:
            output_string += 'Free!'
        elif pricing['discount_percent'] == 0:
            output_string += f'Not on sale.\nPrice: **{pricing["final_formatted"]}**'
        else:
            output_string += f'{pricing["discount_percent"]}% off!\n'
            output_string += f'Original price: {pricing["initial_formatted"]}\n'
            output_string += f'Current price: **{pricing["final_formatted"]}**'

        return output_string

    await Pagination.send_paginated_embed(
            ctx, filtered_results, title=f'Steam search results for: {game}', color=discord.Color.blurple(),
            fields_on_page=1, read_data_async_fn=pagination_callback
        )


@bot.command(name='steamachievements', aliases=['achievements', 'achievement', 'steamachievement'])
async def steam_achieve(ctx, user=None, game=None, show=None):
    """Video Games
    Get the number of achievements a player has earned in the given game. Add the "show" argument
    to list the achievements. The user here is a Steam user, not a Discord user. If you can't use
    a username, try a SteamID.
    +steamachievements <User> <Game> [show]
    """
    id_params = [('key', _STEAM_API_KEY), ('vanityurl', user)]
    id_url = _STEAM_BASE_URL + 'ISteamUser/ResolveVanityURL/v0001/?' + urllib.parse.urlencode(id_params)

    try:
        request_id = urllib.request.Request(id_url)
        response_id = urllib.request.urlopen(request_id)
        data_id = response_id.read()
        response_id.close()
        data_id_string = data_id.decode('utf-8')
        data_id_json = json.loads(data_id_string)
        user_id = data_id_json['response']['steamid']
    except:
        user_id = user

    app_request = urllib.request.Request('https://api.steampowered.com/ISteamApps/GetAppList/v2/')
    app_response = urllib.request.urlopen(app_request)
    app_data = app_response.read()
    app_response.close()
    app_data_string = app_data.decode('utf-8')
    app_data_json = json.loads(app_data_string)

    app_id = None
    for app in app_data_json['applist']['apps']:
        if app['name'].lower() == game.lower():
            app_name = app['name']
            app_id = app['appid']
            break

    if app_id is None:
        await ctx.send('Game not found.')
        return

    ach_params = [('appid', app_id), ('key', _STEAM_API_KEY), ('steamid', user_id), ('l', 'en_us')]
    ach_url = _STEAM_BASE_URL + 'ISteamUserStats/GetPlayerAchievements/v0001/?' + urllib.parse.urlencode(ach_params)

    try:
        ach_request = urllib.request.Request(ach_url)
        ach_response = urllib.request.urlopen(ach_request)
        ach_data = ach_response.read()
        ach_response.close()
        ach_data_string = ach_data.decode('utf-8')
        ach_data_json = json.loads(ach_data_string)
    except urllib.error.HTTPError:
        await ctx.send('Error. Try using your SteamID instead of your username.')
        return

    if show is not None and (show.lower() == 's' or show.lower() == 'show'):
        show_name = True
    else:
        show_name = False

    if show_name:
        achieves = []
        missing_achieves = []

    achieved_count = 0
    total_count = 0

    for a in ach_data_json['playerstats']['achievements']:
        total_count += 1
        if a['achieved'] == 1:
            achieved_count += 1

        if show_name:
            if a['achieved'] == 1:
                achieves.append((a['name'], a['description']))
            else:
                missing_achieves.append((a['name'], a['description']))

    percentage = str(int(round((achieved_count / total_count) * 100)))

    first_output = f'{user} has obtained `{achieved_count}` out of `{total_count}` achievements for {app_name}.'
    first_output += f'\n{percentage}% complete.\n'
    await ctx.send(first_output)
    if not show_name:
        return

    achieves_string = '**Obtained achievements:**\n'
    for a in achieves:
        achieves_string += f'{a[0]}: {a[1]}\n'
    achieves_string += '**Missing achievements:**\n'
    for a in missing_achieves:
        achieves_string += f'{a[0]}: {a[1]}\n'

    if len(achieves_string.splitlines()) > 100:
        await ctx.send('This would be more than 100 lines long. I will not show you all the achievements.')
        return

    string_list = []
    current_string = ''
    len_counter = 0
    for line in achieves_string.splitlines():
        current_string += line + '\n'
        len_counter += 1
        if len_counter >= 20:
            string_list.append(current_string)
            current_string = ''
            len_counter = 0
    string_list.append(current_string)
    current_string = ''

    for string in string_list:
        await ctx.send(string)


@bot.command(name='inspire', aliases=['inspirobot', 'inspiro', 'motivate'])
async def inspirobot(ctx):
    """Fun
    Generate an image using InspiroBot.
    +inspire
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                             'Chrome/87.0.4280.88 Safari/537.36'}

    async with bot.aiohttp_sess.get('https://inspirobot.me/api?generate=true', headers=headers) as response:
        data = await response.content.read()

    ib_message = '*Inspirational quotes provided by InspiroBot*: <https://inspirobot.me/>\n'

    async with bot.aiohttp_sess.get(data.decode('utf-8')) as response:
        await yelobot_utils.send_image(ctx, (ib_message if random.random() < 0.05 else ''), await response.content.read(), 'inspire.jpg')


@bot.command(name='speak', hidden=True)
async def speak(ctx):
    # if speak_cooldown.not_on_cooldown(ctx.author):
    #     speak_cooldown.add_user(ctx.author)
    #     gen = await generate_gpt_2()
    #     generated = gen.splitlines()
    #     for line in generated:
    #         async with ctx.typing():
    #             await asyncio.sleep(len(line) / 12)
    #         await ctx.send(line)
    # else:
    #     await ctx.send('you\'re on cooldown bitch')
    await ctx.send('This isn\'t a thing anymore.')


@bot.command(name='map', hidden=True)
@commands.check(checks.invoked_in_club_cheadle)
async def map_cmd(ctx):
    if ctx.message.guild.id != LWOLF_SERVER_ID:
        return
    await reply(ctx, 'use "+i map" instead')


@bot.command(name='taglist', aliases=['tags', 'images', 'imagelist'])
async def taglist(ctx: commands.Context):
    """Tagged Images
    List all of the tags in this server.
    +taglist
    """
    collection = MONGO_DB['ImageTags']
    full_dict = await collection.find_one({'server': ctx.message.guild.id})

    if full_dict:
        images = full_dict['tags']
    else:
        await reply(ctx, 'This server has no images saved.')
        return

    def read_data(tag):
        image = images[tag]
        if isinstance(image, str): # legacy -- means raw url
            return tag
        else:
            added_by = bot.get_user(images[tag]["author"])
            if added_by and ctx.guild in added_by.mutual_guilds:
                return f'{tag} (added by {added_by.mention})'
            else:
                return f'{tag} (added by a user no longer in this server)'

    await Pagination.send_paginated_embed(ctx, sorted(images.keys(), key=lambda x: x.lower()),
    'Image Tags', color=discord.Color.yellow(), read_data_fn=read_data)


@bot.command(name='image', aliases=['i'])
async def image(ctx, *, tag=None):
    """Tagged Images
    Post an image from the collection. If you leave the tag argument blank, the image is chosen randomly.
    +image [Tag]
    """
    collection = MONGO_DB['ImageTags']
    full_dict = await collection.find_one({'server': ctx.message.guild.id})

    if not full_dict:
        await reply(ctx, 'This server has no images saved.')
        return

    images: dict = full_dict['tags']

    text = ''
    image_url = None

    if tag is None:
        key_list = list(images.keys())
        random_key = random.choice(key_list)
        text = random_key
        tag_name = random_key
        image = images[random_key]
    else:
        image = images.get(tag)
    
    if image is None: # TODO: this part will be replaced with the fuzzy matching subroutine
        await fuzzy_img_match(ctx, tag, images.keys())
        return
    
    if isinstance(image, str):
        image_url = image
        image_author = None
    else:
        image_url = image['url']
        image_author = int(image['author'])

    async with bot.aiohttp_sess.get(image_url) as image_response:
        if image_response.status != 200:
            await reply(ctx, f'This image seems to be broken (tag: {tag_name}, url: {image_url})')
            return
        
        filename_match = re.match(r'^.+/(.+)$', image_url)
        if filename_match:
            filename = filename_match.group(1)
        else:
            filename = 'unknown_image'

        binary_data = io.BytesIO(await image_response.content.read())

    if image_author and text:
        author_member = bot.get_user(image_author)
        text += f' (added by {author_member})'

    await reply(ctx, text, file=discord.File(binary_data, filename=filename))
    binary_data.close()

FUZZ_TAG_MATCH_MIN_RATIO = 60

async def fuzzy_img_match(ctx: commands.Context, tag_entered: str, tags: Iterable[str]):
    def get_word_and_fuzz_ratio(to_match_against: str) -> tuple[str, int]:
        match_ratio = fuzz.ratio(tag_entered.lower(), to_match_against.lower())
        return to_match_against, match_ratio
    
    best_match, best_match_ratio = max(map(get_word_and_fuzz_ratio, tags), key=lambda tag_and_match: tag_and_match[1])
    # sorry for the functional programming BS here but it's pretty neat and compact :D

    if best_match_ratio < FUZZ_TAG_MATCH_MIN_RATIO:
        await reply(ctx, f'Image not found.')
    else:
        await reply(ctx, f'Image not found. Did you mean `{best_match}`?')


@bot.command(name='imagecount')
async def image_count(ctx):
    """Tagged Images
    Count how many images are currently in the collection.
    +imagecount
    """
    collection = MONGO_DB['ImageTags']
    full_dict = await collection.find_one({'server': ctx.message.guild.id})

    if not full_dict:
        await reply(ctx, 'This server has no images saved. (Add some using +addimage)')
        return

    count = len(full_dict['tags'])
    
    await reply(ctx, f'There are currently `{count}` images in the collection. Add more using +addimage!')


@bot.command(name='addimage')
async def add_image(ctx, tag=None, url=None):
    """Tagged Images
    Add an image to the collection. The image can be a URL or an attachment.
    +addimage "<Tag>" <Image>
    """
    if tag is None:
        await reply(ctx, '+addimage "<tag>" <image>. The image can be a URL or an attachment :). Make sure those quotes are there if the tag is more than one word.')
        return

    if len(ctx.message.attachments) > 0:
        url = ctx.message.attachments[0].url
    if url is None or tag is None:
        await reply(ctx, 'You must specify a tag and an image.')
        return
    if not ('.png' in url or '.jpg' in url or '.jpeg' in url or '.gif' in url):
        await reply(ctx, 'That is not a valid image.')
        return
    
    collection = MONGO_DB['ImageTags']

    full_dict = await collection.find_one({'server': ctx.message.guild.id})
    if not full_dict:
        await collection.insert_one({'server': ctx.message.guild.id, 'tags': dict()})
        full_dict = await collection.find_one({'server': ctx.message.guild.id})
    images = full_dict['tags']
    
    for key in images.keys():
        if key.lower() == tag.lower():
            await reply(ctx, 'That tag already exists.')
            return

    await collection.update_one({'server': ctx.message.guild.id}, {'$set': {f'tags.{tag}': {'url': url, 'author': ctx.author.id}}})    

    await reply(ctx, f'{tag} added.')


@bot.command(name='usertags', aliases=['userimages'])
async def user_tags(ctx: commands.Context, *, user: str=None):
    """Tagged Images
    List the tags of the images that this user has added. Leave the user argument blank to list your images.
    YeloBot has only been tracking this since sometime around mid-2022. Any images added before then will not be listed.
    +usertags <User>
    """
    if user is None:
        user = ctx.author
    else:
        user = yelobot_utils.search_for_user(ctx, user)
        if user is None:
            await reply(ctx, 'Could not find that user.')
            return

    collection = MONGO_DB['ImageTags']
    doc = await collection.find_one({'server': ctx.guild.id})
    tags = [k for k, v in doc['tags'].items() if isinstance(v, dict) and v['author'] == user.id]

    if not tags:
        await reply(ctx, 'This user has not uploaded any images (at least since I\'ve been keeping track of who uploads them).')
        return
    
    await yelobot_utils.Pagination.send_paginated_embed(ctx, tags, f'Images Added by {user}')


@bot.command(name='removeimage', aliases=['deleteimage', 'deletetag', 'removetag'])
@has_guild_permissions(manage_messages=True)
async def remove_image(ctx, *, tag=None):
    """Tagged Images
    Remove an image from the collection.
    +removeimage <Tag>
    """
    collection = MONGO_DB['ImageTags']
    full_dict = await collection.find_one({'server': ctx.message.guild.id})

    if tag not in full_dict['tags']:
        await reply(ctx, 'This is not an image tag.')
        return

    await collection.update_one({'server': ctx.message.guild.id}, {'$unset': {f'tags.{tag}': ''}})  
    await reply(ctx, 'Image removed.')


@bot.command(name='edittag')
@has_guild_permissions(manage_messages=True)
async def edit_tag(ctx, tag1=None, tag2=None):
    """Tagged Images
    Edit the tag of an image in the collection.
    +edittag "<Original Tag>" "<New Tag>"
    """
    if None in (tag1, tag2):
        await reply('+edittag "<tag1>" "<tag2>"')
        return

    collection = MONGO_DB['ImageTags']

    full_dict = await collection.find_one({'server': ctx.message.guild.id})

    if tag1 not in full_dict['tags'].keys():
        await reply(ctx, 'The tag you are attempting to edit does not exist.')
        return

    if tag2 in full_dict['tags'].keys():
        await reply(ctx, 'An image with the new tag already exists.')
        return

    image = full_dict['tags'][tag1]    
    await collection.update_one({'server': ctx.message.guild.id}, {'$set': {f'tags.{tag2}': image}})
    await collection.update_one({'server': ctx.message.guild.id}, {'$unset': {f'tags.{tag1}': image}})

    await reply(ctx, 'Tag changed.')


@has_guild_permissions(kick_members=True)
@bot.command(name='kelprole')
async def kelp_role(ctx: commands.Context, role=None):
    """Fun
    Set the role that a user is given when they are kelp'd.
    +kelprole <Role ID>
    """
    collection = MONGO_DB['KelpRole']
    doc = await collection.find_one({'server': ctx.guild.id})
    if role is None:
        if doc is None:
            await reply(ctx, '+kelprole <Role ID>')
        else:
            await collection.delete_one({'server': ctx.guild.id})
            await reply(ctx, 'The kelp role has been removed.')
        return
    
    invalid_role_msg = 'This is not a valid role ID.'
    try:
        role = int(role)
    except ValueError:
        reply(ctx, invalid_role_msg)
        return
    
    role: discord.Role = yelobot_utils.get(ctx.guild.roles, id=role)
    if not role:
        reply(ctx, invalid_role_msg)
        return
    
    if doc:
        await collection.update_one({'server': ctx.guild.id}, {'$set': {'role': role.id}})
    else:
        await collection.insert_one({'server': ctx.guild.id, 'role': role.id})

    await reply(ctx, f'The Kelp role has been set to **{role.name}**.')


@bot.command(name='kelproulette', aliases=['kelp', 'kelpcheck'])
@commands.check(checks.invoked_in_club_cheadle)
async def kelp(ctx):
    """Fun
    Play the Kelp Roulette! If you get Kelp'd, you will hold the Kelp role until you play the Roulette again.
    +kelproulette
    """
    global kelp_cooldown
    if not kelp_cooldown.not_on_cooldown(ctx.author):
        await reply(ctx, f'You cannot use the Kelp Roulette for another {kelp_cooldown.get_remaining_time(ctx.author)}.')
        return

    collection = MONGO_DB['KelpRole']
    doc = await collection.find_one({'server': ctx.guild.id})
    has_role = doc is not None
    if has_role:
        kelp_role: discord.Role = yelobot_utils.get(ctx.guild.roles, id=int(doc['role']))
        if kelp_role is None:
            has_role = False

    kelp_list = [
        ('https://cdn.discordapp.com/attachments/235949492992475137/776666143259492352/08ea0nmgs4531.png', ':)'),
        ('https://static.wikia.nocookie.net/disney/images/1/19/Don_Cheadle.jpg/revision/latest?cb=20190924222841',
         'Don Cheadle wishes you a good day.'),
        (
            'https://vignette.wikia.nocookie.net/veggietales-the-ultimate-veggiepedia/images/4/41/Larryprofile1.png/revision/latest/scale-to-width-down/340?cb=20170130173921',
            'Revelation 2:9')]

    num = random.random()
    kelpd = False

    if num <= 0.33:
        await reply(ctx, 'https://p1.hiclipart.com/preview/636/174/332/gimp-handguns-silver-revolver-png-clipart.jpg')
        await ctx.send('**CLICK**\nYou got lucky this time...') # dont change this to reply
    elif num <= 0.5:
        await reply(ctx,
            'https://lh3.googleusercontent.com/qwGxJIKS7PyQzPmdGXltS9kkOd-7SsW0tjSCbbv_WyjFuhDPkhTCSN0_qACRXlt_WAwCJOFFl5W_ZgFv4XQr6Q=s400')
        await ctx.send('**KELP\'D!!!**') # dont change to reply
        kelpd = True
    else:
        choice = random.choice(kelp_list)
        await reply(ctx, choice[0])
        await ctx.send(choice[1]) # dont change this to reply

    if has_role:
        member_has_role = kelp_role in ctx.author.roles
        if (not member_has_role) and kelpd:
            await ctx.author.add_roles(kelp_role)
        elif member_has_role and not kelpd:
            await ctx.author.remove_roles(kelp_role)


@bot.command(name='light', hidden=True)
async def light(ctx):
    await reply(ctx, 'https://open.spotify.com/album/6NK27l0MYTxek8r4s4sX3C?si=TASxYZAFTb6Wt_j-jYgfbQ')


@bot.command(name='currenttime', aliases=['time'])
async def current_time(ctx, *, location=None):
    """Time/Reminders
    Display the current time in a region of the world, or the current time of a user.
    +time <Location> OR +time user <User>
    """
    usage = '+currenttime <location> OR +currenttime user <name>'
    user = None
    if location is None:
        user = ctx.author
    elif location == 'u' or location == 'usage':
        await reply(ctx ,usage)
        return

    if user or location.split()[0].lower() == 'user':
        collection = MONGO_DB['Timezones']
        if user:
            data = await collection.find_one({'user_id': user.id})
            if not data or not data['is_set']:
                await reply(ctx, f'{usage}\nIf you want to see your local time, first use +settimezone.')
                return
        else:
            user = search_for_user(ctx, ''.join(location.split()[1:]))
            if user is None:
                await reply(ctx, 'Could not find the specified user.')
                return
            data = await collection.find_one({'user_id': user.id})
            if not data or not data['is_set']:
                await reply(ctx, 'This user has not used +settimezone.')
                return
        
        try:
            tz_response = timezonedb.query_zone(TIMEZONEDB_KEY, data['timezone'])
        except timezonedb.TimezoneDBStatusCodeError as e:
            await reply(ctx, formatted_exception(e))
            return

        display = user.nick if user.nick else user.name
    else:
        try:
            nominatim_response = nominatim.query(location)
        except nominatim.NominatimStatusCodeError as e:
            await reply(ctx, formatted_exception(e))
            return

        if len(nominatim_response) == 0:
            await reply(ctx, 'Could not find the specified location.')
            return

        lat = nominatim_response[0]['lat']
        long = nominatim_response[0]['lon']

        try:
            tz_response = timezonedb.query_lat_long(TIMEZONEDB_KEY, lat, long)
        except timezonedb.TimezoneDBStatusCodeError as e:
            await reply(ctx, formatted_exception(e))
            return

        display = nominatim_response[0]['display_name']

        display = display.replace('Ho Chi Minh City, Vietnam', 'Saigon, Vietnam') # fixing vietnam
    

    timestamp = tz_response['formatted'].split()[1]

    hour = int(timestamp.split(':')[0])

    if hour > 12:
        ampm = 'PM'
        timestamp = str(hour - 12) + ':' + timestamp.split(':')[1] + ':' + timestamp.split(':')[2]
    elif hour == 12:
        ampm = 'PM'
    elif hour == 0:
        timestamp = f'12:{timestamp.split(":")[1]}:{timestamp.split(":")[2]}'
        ampm = 'AM'
    else:
        ampm = 'AM'

    tz_abbreviation = tz_response['abbreviation']

    await reply(ctx, f'{timestamp} {ampm} {tz_abbreviation} ({display})')


@bot.command(name='weather')
async def weather(ctx, *, city=None):
    """Utility
    Get the current weather of the specified location.
    +weather <Location>
    """
    u = 'imperial'

    if city == None:
        async with bot.aiohttp_sess.get(sewanee_weather_url) as response:
            if response.status == 200:
                city = 'Thumping Dick Hollow, Tennessee'
                data = await response.json()
                main = data['main']
                temperature = main['temp']
                humidity = main['humidity']
                report = data['weather']
                embed = discord.Embed(
                    title='Weather',
                    description=city,
                    colour=discord.Colour.dark_gold()
                )

                celcius = (temperature - 32) * 5 / 9
                celcius = round(celcius, 2)

                embed.add_field(name='Description', value=report[0]['description'], inline=False)
                embed.add_field(name='Temperature', value=f'{temperature}°F / {celcius}°C', inline=False)
                embed.add_field(name='Humidity', value=f'{humidity}%', inline=False)

                await reply(ctx, embed=embed)
            else:
                await reply(ctx, 'oh shit there was an error with the weather api')
                return
    else:
        async with bot.aiohttp_sess.get(base_weather_url + city + weather_url_ext + u + '&appid=' + WEATHER_KEY) as response:
            if response.status == 200:
                data = await response.json()
                main = data['main']
                temperature = main['temp']
                humidity = main['humidity']
                report = data['weather']

                embed = discord.Embed(
                    title='Weather',
                    description=city,
                    colour=discord.Colour.dark_gold()
                )

                celcius = (temperature - 32) * 5 / 9
                celcius = round(celcius, 2)

                embed.add_field(name='Description', value=report[0]['description'], inline=False)
                embed.add_field(name='Temperature', value=f'{temperature}°F / {celcius}°C', inline=False)
                embed.add_field(name='Humidity', value=f'{humidity}%', inline=False)

                await reply(ctx, embed=embed)
            else:
                await reply(ctx, 'either thats not a real place or the api isnt working')
                return


@bot.command(name='avatar', aliases=['pfp', 'avi', 'av'])
async def avatar(ctx, *, person=None):
    """Utility
    Get a user's current avatar. This will default to the user's server avatar. Use +globalavatar if that's
    not what you want.
    +avatar <User>
    """
    if len(ctx.message.mentions) > 0:
        member = ctx.message.mentions[0]
    elif person is None:
        member = ctx.author
    else:
        member = search_for_user(ctx, person)

    if member:
        avatar_asset = member.guild_avatar

        if avatar_asset is None:
            avatar_asset = member.avatar

        url_path_match = re.match(r'^.*/(.+)$', urllib.parse.urlparse(str(avatar_asset.url)).path)
        filename = url_path_match.group(1)

        async with bot.aiohttp_sess.get(str(avatar_asset.url)) as resp:
            await yelobot_utils.send_image(ctx, '', await resp.content.read(), filename)
    else:
        await reply(ctx, "i have no idea who you're talking about")


@bot.command(name='globalavatar', aliases=['globalpfp', 'globalavi', 'globalav', 'gavatar', 'gpfp', 'gavi', 'gav'])
async def global_avatar(ctx, *, person=None):
    """Utility
    Get a user's global avatar. If this user has a server avatar set, this command will ignore it.
    +globalavatar <User>
    """
    if len(ctx.message.mentions) > 0:
        member = ctx.message.mentions[0]
    elif person is None:
        member = ctx.author
    else:
        member = search_for_user(ctx, person)

    if member:
        url_path_match = re.match(r'^.*/(.+)$', urllib.parse.urlparse(str(member.avatar.url)).path)
        filename = url_path_match.group(1)

        async with bot.aiohttp_sess.get(str(member.avatar.url)) as resp:
            await yelobot_utils.send_image(ctx, '', await resp.content.read(), filename)
    else:
        await reply(ctx, "i have no idea who you're talking about")


@bot.command(name='sex', hidden=True)
async def sex(ctx):
    await ctx.send('https://cdn.discordapp.com/attachments/231248040688746496/770132377845628958/sins.mp4')


# The funny commands are like the first things I ever implemented.
@bot.command(name='funny')
@commands.check(checks.invoked_in_club_cheadle)
async def first_funny(ctx):
    """Fun
    Funny
    +funny
    """
    if random.random() < 0.99:
        await ctx.send('penis!')
    else:
        await ctx.send('ok')


@bot.command(name='funny2')
@commands.check(checks.invoked_in_club_cheadle)
async def second_funny(ctx):
    """Fun
    Funny 2
    +funny2
    """
    await ctx.send('dick!')


@bot.command(name='funny3')
@commands.check(checks.invoked_in_club_cheadle)
async def third_funny(ctx):
    """Fun
    Funny 3
    +funny3
    """
    funny3_users = {
        # yelofelo
        181276019301416960: 'https://bigmemes.funnyjunk.com/pictures/Funny_12b63a_278641.jpg',
        # buca
        145655981076905985: 'https://cdn.discordapp.com/attachments/290289586415075328/764734481415274496/bla.png',
        # joey
        196713204959805441: get_random_shibe(),
        # daniel
        180132572280389632: 'https://i.pinimg.com/originals/80/96/9c/80969c4535c5444de496b4aaf8e9e364.jpg',
        # chris
        185961037642727425: 'https://images-na.ssl-images-amazon.com/images/I/61sIDOD1ajL._AC_SL1500_.jpg',
        # joseph SPECIAL CASE: FILE fish.mp4
        # lopez
        368544507081261056: 'https://media.giphy.com/media/xT0GqlnvnBse9tudHy/giphy.gif',
        # riddle
        298573140957724673: "You've suffered enough.",
        # frog
        118639270545063936: 'https://www.redrooster.com.au/menu/',
        # remi
        188664746118086656: 'https://cdn.discordapp.com/attachments/230963738574848000/764803738321551400/'
                            '20201011_185531.jpg',
        # james
        191428415755255809: 'https://cdn.discordapp.com/attachments/235949492992475137/929495840928694372/erb_walter.mp4'
    }

    if ctx.author.id in funny3_users.keys():
        await ctx.send(funny3_users[ctx.author.id])
    elif ctx.author.id == 139166757758828544:
        # joseph
        await ctx.send(file=discord.File('fish.mp4'))
    elif ctx.author.id == 147908091768340480:
        await ctx.send(random.choice(['https://cdn.discordapp.com/attachments/230963738574848000/833830199317364736/3.5_tons.jpg',
                                      'https://cdn.discordapp.com/attachments/230963738574848000/833830419157090374/Screenshot_1000.png']))
    else:
        try:
            if ctx.author.guild.id == 230963738574848000:
                await ctx.author.send('https://discord.gg/9hfkY4m')
                await ctx.author.send('that was pretty funny')
            await ctx.author.kick(reason=None)
            await ctx.send('lol get fucked idiot')
        except Exception as e:
            await ctx.send('THERE WAS A FUCKING ERROR')
            print(str(e))


@bot.command(name='drperky', hidden=True, aliases=['perky'])
async def perky(ctx):
    await ctx.send('https://cdn.discordapp.com/attachments/401188624210722816/772980812978192415/video0-71.mp4')


@bot.command(name='pick1', aliases=['pick', 'pickone', 'p1'])
async def pick_one(ctx, *args):
    """Utility
    Pick one of the arguments. If your arguments have spaces, you must put the arguments in quotes.
    +pick1 "<Arg1>" "<Arg2>" ...
    """
    if not args:
        args = ['heads', 'tails']
    if all((arg == 'my nose' for arg in args)):
        await reply(ctx, 'Not falling for that one again.')
        return
    await reply(ctx, 'I pick ' + random.choice(args) + '!')


@bot.command(name='pickn', aliases=['pickseveral', 'pickmultiple'])
async def pick_n(ctx, n=None, *args):
    """Utility
    Pick several arguments. If your arguments have spaces, you must put the arguments in quotes.
    +pickn <Count> "<Arg1>" "<Arg2>" ...
    """
    usage = '+pickn <number of items to pick> <item1> [item2] [item3 ...]'
    if n is None:
        await reply(ctx, usage)
        return
    try:
        n = int(n)
    except:
        await reply(ctx, usage)
    
    if n > len(args):
        await reply(ctx, 'The number of items to pick can\'t be more than the number of items provided!')
        return

    args = list(args)

    if n == 1:
        await reply(ctx, 'I pick ' + random.choice(args) + '!')
        return

    random.shuffle(args)

    if n == 2:
        await reply(ctx, f'I pick {args[0]} and {args[1]}!') 
        return
    
    await reply(ctx, 'I pick ' + ', '.join(args[:n-1]) + ', and ' + args[n] + '!')


@bot.command(name='roll')
async def roll(ctx, die='d6'):
    """Utility
    Roll dice.
    +roll [[Number of Dice]d<Sides on Each Die>]
    """
    if 'd' not in die.lower():
        await ctx.send('Either use +roll with no arguments, or specify +roll [rolls]d[number].')
        return

    try:
        if die[0].lower() == 'd':
            rolls_to_make = 1
        else:
            rolls_to_make = int(die.split('d')[0])
        max_roll = int(die.split('d')[-1])
    except:
        await ctx.send('Either use +roll with no arguments, or specify +roll [rolls]d[number].')
        return

    if rolls_to_make > 1000000:
        await ctx.send('im not gonna roll this die more than a million times')
        return

    if max_roll > 1_000_000_000_000_000_000:
        await ctx.send('im not gonna roll a die that has more than one quintillion sides')
        return

    roll_sum = 0
    for i in range(rolls_to_make):
        roll_sum += random.choice(range(1, max_roll + 1))

    await ctx.send(f'Rolled a D{str(max_roll)} {str(rolls_to_make)} time(s). You rolled **{str(roll_sum)}** in total!')


TONY_USER_ID = 155454518551642113


@bot.command(name='wordcoin', aliases=['wordcoins'])
async def wordcoin(ctx, *, user=None):
    """Fun
    Check your Wordcoin balance.
    +wordcoin <User>
    """
    usage = '+wordcoin <user>'

    if not user:
        target_user = ctx.author
    else:
        target_user = search_for_user(ctx, user)
        if not target_user:
            await reply(ctx, f'User not found ({usage})')
            return

    target_username = target_user.nick if target_user.nick else target_user.name

    if target_user.id == TONY_USER_ID:
        await reply(ctx, f'{target_username}\'s wordcoin balance: infinity')
        return

    collection = MONGO_DB['Wordcoin']
    doc = await collection.find_one({'user': target_user.id})
    if not doc:
        await reply(ctx, f'{target_username}\'s wordcoin balance: 0')
        return
    
    await reply(ctx, f'{target_username}\'s wordcoin balance: {doc["balance"]}')


@bot.command(name='givewordcoin')
@commands.check(checks.invoked_by_user(TONY_USER_ID))
async def give_wordcoin(ctx, *, user=None):
    """Fun
    Give a user one Wordcoin.
    +givewordcoin <User>
    """
    usage = '+givewordcoin <user>'

    if not user:
        await reply(ctx, usage)
        return

    user_found = search_for_user(ctx, user)
    if not user_found:
        await reply(ctx, f'User not found ({usage})')
        return
    
    collection = MONGO_DB['Wordcoin']
    doc = await collection.find_one({'user': user_found.id})
    if not doc:
        await collection.insert_one({'user': user_found.id, 'balance': 1})
        new_balance = 1
    else:
        new_balance = int(doc['balance']) + 1
        await collection.update_one({'user': user_found.id}, {'$set': {'balance': new_balance}})
    
    await reply(ctx, f'{user_found.nick if user_found.nick else user_found.name} has been awarded 1 wordcoin. Their wordcoin balance is now {new_balance}.')


@bot.command(name='removewordcoin', aliases=['takewordcoin'])
@commands.check(checks.invoked_by_user(TONY_USER_ID))
async def remove_wordcoin(ctx, *, user=None):
    """Fun
    Take away 5 Wordcoins from a user.
    +removewordcoin <User>
    """
    usage = '+removewordcoin <user>'

    if not user:
        await reply(ctx, usage)
        return

    user_found = search_for_user(ctx, user)
    if not user_found:
        await reply(ctx, f'User not found ({usage})')
        return
    
    collection = MONGO_DB['Wordcoin']
    doc = await collection.find_one({'user': user_found.id})
    if not doc:
        await reply(ctx, 'This user has no wordcoin.')
        return
    else:
        new_balance = int(doc['balance']) - 5
        if new_balance < 0:
            await reply(ctx, 'This user does not have 5 wordcoin.')
            return
        await collection.update_one({'user': user_found.id}, {'$set': {'balance': new_balance}})
    
    await reply(ctx, f'{user_found.nick if user_found.nick else user_found.name} has redeemed 5 wordcoin. Their wordcoin balance is now {new_balance}.')


@bot.command(name='amiyelofelo')
async def am_i_yelofelo(ctx):
    """Misc
    Are you YeloFelo?
    +amiyelofelo
    """
    if ctx.author.id == YELOFELO_USER_ID:
        await reply(ctx, 'yeah')
    else:
        await reply(ctx, 'no')


@bot.command(name='amibuca', aliases=['amibucer', 'amilwolf', 'amibucertoni', 'amibucadibeppo', 'amibucathebeppo', 'amithebucathebeppo', 'amibucareal', 'amithebucer'])
async def am_i_buca(ctx):
    """Misc
    Are you Buca?
    +amibuca
    """
    if ctx.author.id == 145655981076905985: # buca user id, probably should be in a constant but lol
        await reply(ctx, 'yeah')
    else:
        await reply(ctx, 'no')


@bot.command(name='yelo')
async def yelo(ctx):
    """Misc
    Felo
    +yelo
    """
    await ctx.send('felo')


@bot.command(name='shrek', hidden=True)
async def shrek(ctx):
    await ctx.send('https://cdn.discordapp.com/attachments/670680308907114537/775832704502595624/Shrek.mp4')


@bot.command(name='spongebob', hidden=True)
async def spongebob(ctx):
    await ctx.send(
        'https://cdn.discordapp.com/attachments/230963738574848000/778008786874007592/spongebob_first_movie.mp4')


@bot.command(name='infinitywar', aliases=['avengers', 'thanos'], hidden=True)
async def infinitywar(ctx):
    await ctx.send(
        'https://cdn.discordapp.com/attachments/230963738574848000/778008819019284490/Avengers_Infinity_War_NITRO1.webm')


@bot.command(name='laugh', hidden=True)
async def laugh(ctx):
    await ctx.send('HAHAHAHAHAHAHA')


# @bot.command(name='cheadle', hidden=True)
# async def cheadle(ctx):
#     await ctx.send('Hello! If you\'re seeing this, we assume you found us through our cheadle vanity link! \
# This message is to clarify that this is **not a massive community server, and is not directly related to Don Cheadle or the MCU.\
# ** While we do love the Don, this server is just an obscenely edgy group chat with a bunch of friends. You are welcome to stay if you choose to do so,\
#  this message is just to inform you that you may not have found what you were expecting.')


@bot.command(name='walnut')
async def walnut(ctx):
    """Misc
    Walnut
    +walnut
    """
    await reply(ctx, 'good one hahahahahh')


@bot.command(name='delete', aliases=['purge'])
@has_permissions(manage_messages=True)
async def delete_msg(ctx: commands.Context, amt=None, user=None):
    """Moderation
    Delete the last x messages from this channel.
    +delete <x>
    """
    usage = '+delete <number> [user]'
    try:
        i_amt = int(amt)
    except ValueError:
        await reply(ctx, usage)
        return

    if user is not None:
        user = search_for_user(ctx, user)
        if not user:
            await reply(ctx, usage)
            return

    if user:
        limit = i_amt * 10
        counter = 0
        def delete_check(msg):
            nonlocal counter
            if counter < i_amt and msg.author.id == user.id:
                counter += 1
                return True
            return False
    else:
        limit = i_amt + 1
        delete_check = lambda msg: True

    deleted = await ctx.channel.purge(limit=limit, reason=f'Deleted by {ctx.author}', check=delete_check)
    if user:
        to_send = f'Deleted {len(deleted)} message(s) from {user}.'
    else:
        to_send = f'Deleted {len(deleted) - 1} message(s).'
    await ctx.send(to_send, delete_after=None if user else 5.0)


@bot.command(name='timeout')
@has_permissions(moderate_members=True)
async def timeout(ctx: commands.Context, user: discord.Member, time_str: str, *, reason: str=None):
    """Moderation
    Apply an arbitrary length timeout to a user. The time is in the same format as reminders (eg. 3w2d19h10m3s).
    +timeout <User> <Time> [Reason]
    """
    usage = '+timeout <time> [reason]\nThe time is in the same format as reminders (eg. 3w2d19h10m3s)'
    time_re = r'^((?P<weeks>\d*)w)?((?P<days>\d*)d)?((?P<hours>\d*)h)?((?P<minutes>\d*)m)?((?P<seconds>\d*)s)?$'
    mo = re.match(time_re, time_str)

    if not mo:
        await reply(ctx, usage)
        return

    td_args = dict()
    if mo.group('weeks'):
        td_args['weeks'] = int(mo.group('weeks'))
    if mo.group('days'):
        td_args['days'] = int(mo.group('days'))
    if mo.group('hours'):
        td_args['hours'] = int(mo.group('hours'))
    if mo.group('minutes'):
        td_args['minutes'] = int(mo.group('minutes'))
    if mo.group('seconds'):
        td_args['seconds'] = int(mo.group('seconds'))
    
    td = timedelta(**td_args)
    if td > timedelta(days=28):
        await reply(ctx, 'Currently, timeouts cannot be longer than 28 days.')
        return

    reason_param = f'Timed out by {ctx.author}'
    if reason:
        reason_param += f' with reason: {reason}'
    
    await user.timeout(td, reason=reason_param)
    await reply(ctx, f'Timed out {user.nick if user.nick else user.name}.')


@bot.command(name='8ball')
async def eight_ball(ctx):
    """Fun
    A magic 8-ball.
    +8ball
    """
    l = [
        'Yeah!', 'No...', 'Nah.', 'Of course!', 'Perhaps.', 'Bro...', 'Probably.', 'Nooooo!',
        'Yes.', 'No.', 'Not possible.', 'I have no idea.', 'Maybe?', 'For sure.', 'No way.',
        "That's just not right.", 'YEA!', 'YES', 'NO YOU FUCKING IDIOT', "i honestly don't care",
        'Are you serious bro?', 'LMAOOOOOOOO',
        'youre retarded', 'sure whatever'
        ]
    await reply(ctx, random.choice(l))


@bot.command(name='say')
@commands.check(checks.invoked_by_user(181276019301416960, 145655981076905985, 336681418132553728))
async def say(ctx, *, text):
    """Misc
    Make YeloBot say something.
    +say <Message>
    """
    await ctx.message.delete()
    await ctx.send(text)


@bot.command(name='shibe', hidden=True)
async def shibe(ctx):
    await ctx.send(get_random_shibe())


@bot.command(name='emote', aliases=['e'])
async def emote(ctx, emote):
    """Utility
    Post an emote. This is helpful if you don't have Nitro but want to post an animated emote.
    +emote <Name>
    """
    e = yelobot_utils.get(bot.get_guild(ctx.guild.id).emojis, name=emote)
    if e:
        await ctx.send(e)
    else:
        await ctx.send('emote not found')


@has_guild_permissions(kick_members=True)
@bot.command(name='albinauric')
async def albinauric(ctx):
    """Fun
    Drop the Albinauric bomb on the message you are replying to.
    +albinauric
    """
    if not (ctx.message.reference and ctx.message.reference.cached_message):
        return

    emotes = yelobot_utils.get_all(bot.get_guild(764984305696636939).emojis, name='Albinauric')
    for e in emotes:
        try:
            await ctx.message.reference.cached_message.add_reaction(e)
        except CommandError:
            return

# old thing for funny3 i think? i had no idea what i was doing
def get_random_shibe():
    return random.choice(['https://i.imgur.com/H6p2hxT.jpg', 'https://i.kym-cdn.com/photos/images/newsfeed/001/468'
                                                             '/053/eed.jpg',
                          'https://vignette.wikia.nocookie.net/kirby-twitter/images/a/ae/5E5A351E-0EB0-4BBE-8FF3'
                          '-6FF132B36895.jpeg '
                          '/revision/latest/top-crop/width/360/height/450?cb=20190225042732',
                          'https://i.redd.it/754c5snwaiyy.jpg',
                          'https://steamuserimages-a.akamaihd.net/ugc/937214613632263114'
                          '/3240485AE89BCE1DCFC4E37F30A1E171B065C54A/?imw '
                          '=637&imh=358&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true',
                          'https://assets.change.org/photos/9/dt/lf/jIdtlFZXljLNqDZ-800x450-noPad.jpg?1529319417',
                          'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/cb6c8450-ac06-45d1-b18b'
                          '-5d18b490affc/d6gdiro-072c2584-a21e-481d-8e3c-109746233708.jpg/v1/fill/w_1024,h_768,q_75,'
                          'strp/shibe_doge_by_mcninja01_d6gdiro-fullview.jpg?token'
                          '=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9'
                          '.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3siaGVpZ2h0IjoiPD03NjgiLCJwYXRoIjoiXC9mXC9jYjZjODQ1MC1hYzA2LTQ1ZDEtYjE4Yi01ZDE4YjQ5MGFmZmNcL2Q2Z2Rpcm8tMDcyYzI1ODQtYTIxZS00ODFkLThlM2MtMTA5NzQ2MjMzNzA4LmpwZyIsIndpZHRoIjoiPD0xMDI0In1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmltYWdlLm9wZXJhdGlvbnMiXX0.Tbn_QWrk3JCM2lGstlaXMsWFsSDpMKZ-IpAHd667Hgw',
                          'https://youtu.be/FzF5nf1g14c',
                          'https://cdn.discordapp.com/attachments/369343964622356480/675046953889038346/Screenshot_20191128-090809_Facebook.jpg',
                          'https://cdn.discordapp.com/attachments/369343964622356480/673406190255865857/Screenshot_20200201-165421.png',
                          'https://imgur.com/aCyKQmm',
                          'https://cdn.discordapp.com/attachments/369343964622356480/560866063420489738/Screenshot_20190215-111324_Facebook.jpg',
                          'https://cdn.discordapp.com/attachments/369343964622356480/444534716457156618/8791e202-2db8-4f7f-ae3e-104a2950fd05.jpg',
                          'https://cdn.discordapp.com/attachments/369343964622356480/423617331856670720/a1d33145358e00f284f7bfe9b6383429.jpg',
                          'https://cdn.discordapp.com/attachments/369343964622356480/408839904596983811/06369d4d-414a-4108-b82b-5601a93353fd.jpg',
                          'https://cdn.discordapp.com/attachments/244642058713694211/576504268413206574/side_eyed_shiba.jpg',
                          'https://cdn.discordapp.com/attachments/191363863701225472/265448376022073345/unknown.png',
                          'https://imgur.com/gEYVUBr'
                          ])


def is_a_word(word: str, string: str):
    return string == word or string.startswith(word + ' ') or string.endswith(' ' + word) or f' {word} ' in string


# I don't even know if this is used anymore but I'm too scared to touch it rn
async def bot_is_talking() -> bool:
    global IS_TALKING
    await bot.wait_until_ready()

    if IS_TALKING is None:
        collection = MONGO_DB['Talking']
        IS_TALKING = bool((await collection.find_one())['talking'])
    
    return IS_TALKING


class Cooldown: # rarely used and nearly obsolete, should delete eventually
    def __init__(self, seconds: int or float):
        self.last_used = dict()
        self.cooldown_time = seconds

    def add_user(self, user: discord.user):
        self.last_used[user] = time.time()

    def not_on_cooldown(self, user: discord.user) -> bool:
        if not (user in self.last_used.keys()):
            self.add_user(user)
            return True

        if time.time() - self.last_used[user] >= self.cooldown_time:
            self.add_user(user)
            return True
        return False

    def get_remaining_time(self, user: discord.user) -> str:
        seconds_remaining = round(self.cooldown_time - (time.time() - self.last_used[user]))

        if seconds_remaining < 60:
            return str(seconds_remaining) + ' seconds'
        elif seconds_remaining < 3600:
            return str(round(seconds_remaining / 60)) + ' minutes'
        elif seconds_remaining < 86400:
            return str(round(seconds_remaining / 3600)) + ' hours'
        elif seconds_remaining < 604800:
            return str(round(seconds_remaining / 86400)) + ' days'
        elif seconds_remaining < 2592000:
            return str(round(seconds_remaining / 604800)) + ' weeks'
        elif seconds_remaining < 31556952:
            return str(round(seconds_remaining / 2592000)) + ' months'
        else:
            return str(round(seconds_remaining / 31556952)) + ' years'

@StartupTask
async def set_pagination_emojis():
    await asyncio.sleep(5)
    guild = bot.get_guild(764984305696636939) # this is where pagination emojis are (should be a constant)
    await yelobot_utils.Pagination.set_emojis(guild, 'left_arrow', 'right_arrow')

@StartupTask
async def assign_roles_on_startup():
    await asyncio.sleep(5)
    await save_roles.assign_roles_on_startup_impl(bot, MONGO_DB)

async def main():
    global RESPONSE_LOCK
    RESPONSE_LOCK = asyncio.Lock()

    bd_cog = Birthdays(bot, MONGO_DB)
    await bot.add_cog(bd_cog)
    StartupTask(bd_cog.init_birthdays)

    remind_cog = Reminders(bot, MONGO_DB)
    await bot.add_cog(remind_cog)
    StartupTask(remind_cog.init_reminders)

    # twitter_cog = Twitter(bot, MONGO_DB, os.getenv('TWITTER_BEARER'))
    # await bot.add_cog(twitter_cog)
    # StartupTask(twitter_cog.sub_to_tweets_startup)
    # Twitter API is dead :(

    daily_message_cog = DailyMessages(bot, MONGO_DB)
    await bot.add_cog(daily_message_cog)
    StartupTask(daily_message_cog.init_daily_messages)

    convert_currency_cog = CurrencyConversion(bot, MONGO_DB, EXCHANGE_RATE_KEY)
    await bot.add_cog(convert_currency_cog)
    StartupTask(convert_currency_cog.update_currencies)

    await bot.add_cog(MessageFilter(bot, MONGO_DB))
    await bot.add_cog(ArchivePins(bot, MONGO_DB))
    await bot.add_cog(BibleVerse(bot, MONGO_DB, BIBLE_API_KEY))
    await bot.add_cog(HelpCommand(bot))
    #await bot.add_cog(Timestamps(bot, MONGO_DB))

    if ANNOUNCE_MINECRAFT_EVENTS:
        check_minecraft_events.start()

    for task in StartupTask.tasks:
        StartupTask.bot.loop.create_task(task)
    StartupTask.tasks = []

    await bot.start(BOT_TOKEN)


async def run():
    global MONGO_DB

    async with bot:
        async with aiohttp.ClientSession(loop=bot.loop) as sess:
            MONGO_DB = AsyncIOMotorClient(
                MONGO_CONNECTION_STRING,
                tlsCAFile=certifi.where(),
                io_loop=bot.loop
            )[MONGO_DATABASE_NAME]
            bot.set_aiohttp_sess(sess)
            await main()

if __name__ == '__main__':
    kelp_cooldown = Cooldown(43200)

    asyncio.run(run())
