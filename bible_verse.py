from discord.ext import commands, tasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from yelobot_utils import reply, YeloBot
import bible_api
import traceback
import timezones
import time


class BibleVerse(commands.Cog):
    def __init__(self, bot: YeloBot, mongo: AsyncIOMotorDatabase, key):
        self.bot = bot
        self.collection = mongo['BibleVerse']
        self.key = key
        self.verse_loop.start()

    @commands.command(name='biblesub')
    @commands.has_permissions(kick_members=True)
    async def bible_sub(self, ctx: commands.Context):
        """Misc
        Subscribe to or unsubscribe from daily bible verses in the current channel.
        +biblesub
        """
        doc = await self.collection.find_one({'type': 'channel', 'channel': ctx.channel.id})
        if not doc:
            doc = {'type': 'channel', 'channel': ctx.channel.id}
            await self.collection.insert_one(doc)
            await reply(ctx, 'Subscribed to daily bible verses.')
        else:
            await self.collection.delete_one(doc)
            await reply(ctx, 'Unsubscribed from daily bible verses.')

    async def send_verse(self):
        verse_ref, verse = await bible_api.get_random_verse(self.bot.aiohttp_sess, self.key)
        verse_msg = f'Daily bible verse:\n*{verse_ref}*\n{verse}'

        docs = self.collection.find({'type': 'channel'})
        for doc in await docs.to_list(None):
            try:
                channel = self.bot.get_channel(int(doc['channel']))
            except:
                traceback.print_exc()
                continue

            await channel.send(verse_msg)

    @tasks.loop(minutes=60.0)
    async def verse_loop(self):
        dt_now_la = timezones.datetime_now_in_tz('America/Los_Angeles')
        unix_12 = timezones.unix_at_time('America/Los_Angeles', dt_now_la.month, dt_now_la.day, dt_now_la.year, 12, 0, 0)
        now = time.time()

        if 0 <= now - unix_12 <= 2 * 60 * 60:
            doc = await self.collection.find_one({'type': 'last_verse_time'})
            if now - int(doc['last_verse_time']) >= 20 * 60 * 60:
                await self.collection.update_one(doc, {'$set': {'last_verse_time': int(now)}})
                await self.send_verse()

    @verse_loop.before_loop
    async def before_verse_loop(self):
        await self.bot.wait_until_ready()

