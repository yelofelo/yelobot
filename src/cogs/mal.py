import clients.mal_rss as mal_rss
import clients.tenrai as tenrai
import utils.timezones as timezones
import time
import random
import discord
import asyncio
import math
import traceback
from typing import Optional
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import commands
from discord.ext.commands import has_permissions
from utils.yelobot_utils import YeloBot, reply
from motor.motor_asyncio import AsyncIOMotorDatabase

class MyAnimeList(commands.Cog):
    def __init__(self, bot: YeloBot, mongodb: AsyncIOMotorDatabase):
        self.bot = bot
        self.MONGO_DB = mongodb

    @commands.command('createmalfeed')
    @has_permissions(manage_messages=True)
    async def create_mal_feed(self, ctx: commands.Context, *, feed_time: str | None=None):
        """MyAnimeList
        Creates a MyAnimeList feed in the current channel, which will post daily at the provided time. You must use 24-hour time for the time argument.
        +createmalfeed <time>
        """
        usage = '+createmalfeed <time>'

        if feed_time is None:
            await reply(ctx, usage)
            return
        
        split_feed_time = feed_time.split(':')
        if len(split_feed_time) != 2:
            await reply(ctx, usage)
            return
        
        if not all((item.isdigit() for item in split_feed_time)):
            await reply(ctx, usage)
            return
        
        if len(split_feed_time[1]) != 2:
            await reply(ctx, usage)
            return
        
        feed_hour, feed_minute = int(split_feed_time[0]), int(split_feed_time[1])

        if (not (0 <= feed_hour <= 23)) or not (0 <= feed_minute <= 59):
            await reply(ctx, usage)
            return
        
        tz_collection = self.MONGO_DB['Timezones']
        tz_doc = await tz_collection.find_one({'user_id': ctx.author.id})

        if not tz_doc:
            await reply(ctx, 'Please use +settimezone first.')
            return
        
        now = datetime.now(ZoneInfo(tz_doc['timezone']))
        time_to_send = timezones.unix_at_time(tz_doc['timezone'], now.month, now.day, now.year, feed_hour, feed_minute, 0)
        
        if time.time() > time_to_send:
            time_to_send += 24 * 60 * 60

        mal_collection = self.MONGO_DB['MALFeeds']

        mal_doc = await mal_collection.find_one({'_id': ctx.channel.id})
        if mal_doc:
            await reply(ctx, 'This channel already has a MyAnimeList feed!')
            return

        await mal_collection.insert_one({
            "_id": ctx.channel.id,
            "time_to_send": time_to_send,
            "users": {}
        })

        await reply(ctx, 'Successfully created a daily MyAnimeList feed!')
        await self.mal_thread(ctx.channel.id)

    @commands.command('deletemalfeed')
    @has_permissions(manage_messages=True)
    async def delete_mal_feed(self, ctx: commands.Context):
        """MyAnimeList
        Deletes this channel's MyAnimeList feed.
        +deletemalfeed
        """
        mal_collection = self.MONGO_DB['MALFeeds']
        mal_doc = await mal_collection.find_one({'_id': ctx.channel.id})

        if not mal_doc:
            await reply(ctx, 'This channel does not have a MyAnimeList feed set up.')
            return

        await mal_collection.delete_one({'_id': ctx.channel.id})
        await reply(ctx, 'MyAnimeList feed deleted.')

    @commands.command('malsub', aliases=['malsubscribe'])
    async def mal_subscribe(self, ctx: commands.Context, *, username: str):
        """MyAnimeList
        Add the username's MyAnimeList account to this channel's MAL feed. You are limited to one MAL account added per Discord user.
        +malsub <username>
        """
        usage = '+malsub <username>'
        if ' ' in username:
            await reply(ctx, usage)
            return

        collection = self.MONGO_DB['MALFeeds']
        doc = await collection.find_one({'_id': ctx.channel.id})

        if not doc:
            await reply(ctx, 'This channel does not have a MyAnimeList feed created. Get a server moderator to help if you would like one!')
            return

        if str(ctx.author.id) in doc['users']:
            await reply(ctx, 'You have already added a MyAnimeList account to the feed! Remove that one first with +malunsub.')
            return

        # Try to get a MAL RSS feed for this user to verify that it's a valid username
        try:
            await mal_rss.get_mal_rss(self.bot.aiohttp_sess, mal_rss.MALContentType.ANIME, username)
        except mal_rss.MALRSSRequestException as e:
            if e.status_code == 404:
                await reply(ctx, f'{username} doesn\'t seem to be a valid MyAnimeList username.')
                return
            await reply(ctx, f'Issue when calling the MyAnimeList API (status {e.status_code}). Maybe try again later?')
            return

        await collection.update_one({'_id': ctx.channel.id}, {'$set': {f'users.{ctx.author.id}': username}})

        await reply(ctx, f'Added your account {username} to the MyAnimeList feed.')

    @commands.command('malunsub', aliases=['malunsubscribe'])
    async def mal_unsubscribe(self, ctx: commands.Context):
        """MyAnimeList
        Remove the MyAnimeList account that you have added to this channel's feed from it.
        +malunsub
        """
        collection = self.MONGO_DB['MALFeeds']
        doc = await collection.find_one({'_id': ctx.channel.id})

        if not doc:
            await reply(ctx, 'This channel does not have a MyAnimeList feed created.')
            return

        if str(ctx.author.id) not in doc['users']:
            await reply(ctx, 'You have not added a MyAnimeList user to this channel\'s feed.')
            return

        await collection.update_one({'_id': ctx.channel.id}, {'$unset': {f'users.{ctx.author.id}': ''}})

        await reply(ctx, f'Your account {doc["users"][str(ctx.author.id)]} has been removed from this channel\'s MyAnimeList feed.')

    async def mal_thread(self, channel_id: int):
        collection = self.MONGO_DB['MALFeeds']
        channel = discord.utils.get(self.bot.get_all_channels(), id=channel_id)
        time_to_send = None

        doc = await collection.find_one({'_id': channel_id})
        while True:
            if not doc:
                print(f'Channel {channel} has no MAL thread feed anymore! Stopping mal_thread for this channel.')
                return
            
            if time_to_send is None:  # First iteration
                time_to_send = float(doc['time_to_send'])
            if time.time() < time_to_send:
                await asyncio.sleep(time_to_send - time.time())

            doc = await collection.find_one({'_id': channel_id})
            if not doc:
                print(f'Channel {channel} has no MAL thread feed anymore! Stopping mal_thread for this channel.')
                return
            
            if not math.isclose(time_to_send, float(doc['time_to_send'])):
                print('Time to send is not close to whats in the doc!', time_to_send, float(doc['time_to_send']))
                # A new thread was created during the wait, so abandon this one. I guess there is an edge case here if the new thread
                # has the same time_to_send as the last one and we may get duplicate messages until the bot restarts... but oh well
                # I don't want to deal with that right now lol
                return
            
            last_time_sent = time_to_send - (24 * 60 * 60)

            anime_embed = await self.get_embed(mal_rss.MALContentType.ANIME, last_time_sent, doc, channel.guild)
            manga_embed = await self.get_embed(mal_rss.MALContentType.MANGA, last_time_sent, doc, channel.guild)

            if anime_embed:
                await channel.send(embed=anime_embed)
            if manga_embed:
                await channel.send(embed=manga_embed)

            time_to_send += 24 * 60 * 60
            await collection.update_one({'_id': channel_id}, {"$set": {'time_to_send': time_to_send}})

    async def get_embed(self, mal_content_type: mal_rss.MALContentType, last_time_sent: int, doc, guild: discord.Guild) -> Optional[discord.Embed]:
        updates = defaultdict(list)
        frequencies = defaultdict(int)
        members = {member.id: member for member in guild.members}

        for discord_user, mal_user in doc['users'].items():
            if int(discord_user) not in members:
                print(f'MyAnimeList.get_embed: User {user_id} not found, just skipping for now...')
                continue

            try:
                media_list = await mal_rss.get_mal_rss(self.bot.aiohttp_sess, mal_content_type, mal_user)
            except mal_rss.MALRSSRequestException:
                traceback.print_exc()
          
            for media_id, pub_time, title, description in media_list:
                if pub_time < last_time_sent:
                    break
                updates[int(discord_user)].append((media_id, title, description))
                frequencies[media_id] += 1

        if not updates:
            return None
        
        most_frequent_media = []
        most_frequent_media_count = 0

        for media_id, count in frequencies.items():
            if count > most_frequent_media_count:
                most_frequent_media_count = count
                most_frequent_media = [media_id]
            elif count == most_frequent_media_count:
                most_frequent_media.append(media_id)

        tenrai_data = None
        try:
            if mal_content_type == mal_rss.MALContentType.ANIME:
                tenrai_data = await tenrai.get_anime_details(self.bot.aiohttp_sess, random.choice(most_frequent_media))
            else:
                tenrai_data = await tenrai.get_manga_details(self.bot.aiohttp_sess, random.choice(most_frequent_media))
        except tenrai.TenraiRequestException:
            traceback.print_exc()

        embed_description = ''

        for user_id, updates_list in updates.items():
            user = members[user_id]

            if embed_description != '':
                embed_description += '\n'

            embed_description += f'\n**[{doc["users"][str(user_id)]}](https://myanimelist.net/profile/{doc["users"][str(user_id)]}) | {user.mention}**\n'
            embed_description += '\n'.join([f'• {title} | {description}' for _, title, description in updates_list])

        embed = discord.Embed(
            title='Anime Updates' if mal_content_type == mal_rss.MALContentType.ANIME else 'Manga Updates',
            description=embed_description,
            color=discord.Color.blue()
        )

        if tenrai_data:
            embed.set_thumbnail(url=tenrai_data['data']['images']['jpg']['image_url'])

        return embed

    async def init_feeds(self):
        await self.bot.wait_until_ready()
        collection = self.MONGO_DB['MALFeeds']

        to_add = []

        for item in await (collection.find()).to_list():
            try:
                channel = await self.bot.fetch_channel(int(item['_id']))
            except:
                print(f'MyAnimeList.init_feeds: channel {item["_id"]} is dead? Skipping it.')
                continue
            to_add.append(channel.id)

        print(f'Initializing {len(to_add)} MAL threads')
        await asyncio.gather(*[self.mal_thread(c) for c in to_add])
