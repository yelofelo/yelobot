from discord.ext import commands
from datetime import datetime, timezone
from yelobot_utils import reply, YeloBot
import bluesky_interface
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
import time


class Bluesky(commands.Cog):
    subscription_cooldown = 30
    def __init__(self, bot: YeloBot, mongo: AsyncIOMotorDatabase):
        self.bot = bot
        self.collection = mongo['BlueskySubs']

    @commands.has_permissions(manage_messages=True)
    @commands.command('subscribebluesky', aliases=['subbluesky', 'blueskysub', 'subbsky', 'bskysub', 'blueskysubscribe'])
    async def bluesky_sub(self, ctx: commands.Context, handle=None):
        """Bluesky
        Subscribe to a Bluesky user in this channel.
        +subscribebluesky <Handle>
        """
        usage = '+subscribebluesky <Handle>'

        if handle is None:
            await reply(ctx, usage)
            return
        
        handle = handle.lstrip('@')

        try:
            await bluesky_interface.get_user_feed(self.bot.aiohttp_sess, handle)
        except bluesky_interface.Bluesky400Error:
            await reply(ctx, 'This is not a valid Bluesky handle.\n' + usage)
            return
        
        timestamp = float(time.time())

        existing_doc = await self.collection.find_one({'server': ctx.guild.id, 'channel': ctx.channel.id, 'bsky_handle': handle})
        if existing_doc:
            await reply(ctx, 'A subscription for this Bluesky account already exists in this channel.')
            return

        await self.collection.insert_one({
            'server': ctx.guild.id, 'channel': ctx.channel.id, 'bsky_handle': handle, 'last_searched_time': timestamp})
        
        await reply(ctx, f'Successfully subscribed to {handle}.')


    @commands.has_permissions(manage_messages=True)
    @commands.command('unsubscribebluesky', aliases=['unsubbluesky', 'blueskyunsub', 'unsubbsky', 'bskyunsub', 'blueskyunsubscribe'])
    async def bluesky_unsub(self, ctx: commands.Context, handle=None):
        """Bluesky
        Unsubscribe from a Bluesky user in this channel.
        +unsubscribebluesky <Handle>
        """
        usage = '+unsubscribebluesky <Handle>'

        if handle is None:
            await reply(ctx, usage)
            return
        
        handle = handle.lstrip('@')

        existing_doc = await self.collection.find_one({'server': ctx.guild.id, 'channel': ctx.channel.id, 'bsky_handle': handle})
        if not existing_doc:
            await reply(ctx, 'A subscription for this Bluesky account does not exist in this channel.')
            return
        
        await self.collection.delete_one({'server': ctx.guild.id, 'channel': ctx.channel.id, 'bsky_handle': handle})

        await reply(ctx, 'Subscription deleted.')

    async def sub_loop(self):
        while True:
            await asyncio.sleep(self.subscription_cooldown)

            for doc in await (self.collection.find()).to_list(None):
                channel = self.bot.get_channel(int(doc['channel']))
                if channel is None:
                    await self.collection.delete_one(doc)
                    continue

                dt = datetime.fromtimestamp(float(doc['last_searched_time']), timezone.utc)

                try:
                    posts = await bluesky_interface.get_posts_after_time(self.bot.aiohttp_sess, doc['bsky_handle'], doc['last_searched_time'])
                except bluesky_interface.Bluesky400Error:
                    await channel.send(f'{doc["bsky_handle"]}\'s Bluesky account does not seem to exist. Deleted subscription.')
                    continue

                if len(posts) != 0:
                    await self.collection.update_one(doc, {'$set': {'last_searched_time': bluesky_interface.iso_to_unix(posts[-1]['record']['createdAt'])}})
                    for post in posts:
                        await channel.send(bsky_url_from_post(post))

    async def sub_to_posts_startup(self):
        await asyncio.sleep(5)
        await self.sub_loop()


def bsky_url_from_post(post: dict) -> str:
    handle = post['author']['handle']
    post_id = post['uri'].split('/')[-1]
    return f'https://bsky.app/profile/{handle}/post/{post_id}'

