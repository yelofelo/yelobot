from discord.ext import commands
from utils.yelobot_utils import reply, YeloBot
import twscrape
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
import time
import traceback
import os


TWEET_LOOKBACK_COUNT = 20


class Twitter(commands.Cog):
    subscription_cooldown = 45
    def __init__(self, bot: YeloBot, mongo: AsyncIOMotorDatabase):
        self.bot = bot
        self.collection = mongo['TwitterSubs']
        self.api = twscrape.API()

    async def init_twscrape(self, auth_token: str, ct0: str):
        await self.api.pool.add_account_cookies('yelobot_twitter_acc', f'auth_token={auth_token}; ct0={ct0}')

    @commands.has_permissions(manage_messages=True)
    @commands.command('subscribetwitter', aliases=['subtwitter', 'twittersub', 'subx', 'xsub', 'twittersubscribe'])
    async def twitter_sub(self, ctx: commands.Context, handle=None):
        """Twitter
        Subscribe to a Twitter user in this channel.
        +subscribetwitter <Handle>
        """
        usage = '+subscribetwitter <Handle>'

        if handle is None:
            await reply(ctx, usage)
            return
        
        handle = handle.lstrip('@')

        tw_user = await self.api.user_by_login(handle)
        if tw_user is None:
            await reply(ctx, 'This is not a valid Twitter handle.\n' + usage)
            return
        
        timestamp = float(time.time())

        existing_doc = await self.collection.find_one({'server': ctx.guild.id, 'channel': ctx.channel.id, 'twitter_id': tw_user.id})
        if existing_doc:
            await reply(ctx, 'A subscription for this Twitter account already exists in this channel.')
            return

        await self.collection.insert_one({
            'server': ctx.guild.id, 'channel': ctx.channel.id, 'twitter_id': tw_user.id, 'last_searched_time': timestamp, 'replies': False})
        
        await reply(ctx, f'Successfully subscribed to {handle}.')


    # TODO refactor this so that we're not just coping code 
    #  ironic because I'm copying this *again* from the bsky module to twitter
    @commands.has_permissions(manage_messages=True)
    @commands.command('subscribetwitterwithreplies', aliases=['subtwitterwithreplies', 'twittersubwithreplies', 'subxwithreplies', 'xsubwithreplies', 'twittersubscribewithreplies'])
    async def twitter_sub_with_replies(self, ctx: commands.Context, handle=None):
        """Twitter
        Subscribe to a Twitter user in this channel; include their replies.
        +subscribetwitterwithreplies <Handle>
        """
        usage = '+subscribetwitterwithreplies <Handle>'

        if handle is None:
            await reply(ctx, usage)
            return
        
        handle = handle.lstrip('@')

        tw_user = await self.api.user_by_login(handle)
        if tw_user is None:
            await reply(ctx, 'This is not a valid Twitter handle.\n' + usage)
            return
        
        timestamp = float(time.time())

        existing_doc = await self.collection.find_one({'server': ctx.guild.id, 'channel': ctx.channel.id, 'twitter_id': tw_user.id})
        if existing_doc:
            await reply(ctx, 'A subscription for this Twitter account already exists in this channel.')
            return

        await self.collection.insert_one({
            'server': ctx.guild.id, 'channel': ctx.channel.id, 'twitter_id': tw_user.id, 'last_searched_time': timestamp, 'replies': True})
        
        await reply(ctx, f'Successfully subscribed to {handle}.')


    @commands.has_permissions(manage_messages=True)
    @commands.command('unsubscribetwitter', aliases=['unsubtwitter', 'twitterunsub', 'unsubx', 'xunsub', 'twitterunsubscribe'])
    async def twitter_unsub(self, ctx: commands.Context, handle=None):
        """Twitter
        Unsubscribe from a Twitter user in this channel.
        +unsubscribetwitter <Handle>
        """
        usage = '+unsubscribetwitter <Handle>'

        if handle is None:
            await reply(ctx, usage)
            return
        
        handle = handle.lstrip('@')

        tw_user = await self.api.user_by_login(handle)
        if tw_user is None:
            await reply(ctx, 'This is not a valid Twitter handle.\n' + usage)
            return

        existing_doc = await self.collection.find_one({'server': ctx.guild.id, 'channel': ctx.channel.id, 'twitter_id': tw_user.id})
        if not existing_doc:
            await reply(ctx, 'A subscription for this Twitter account does not exist in this channel.')
            return
        
        await self.collection.delete_one({'server': ctx.guild.id, 'channel': ctx.channel.id, 'twitter_id': tw_user.id})

        await reply(ctx, 'Subscription deleted.')

    async def get_tweets(self, twitter_user_id: int | str, last_searched_time: int, replies: bool, lookback_count: int=TWEET_LOOKBACK_COUNT) -> list[twscrape.Tweet]:
        tweets_to_return = []

        if replies:
            tweets = await twscrape.gather(self.api.user_tweets_and_replies(twitter_user_id, limit=lookback_count))
        else:
            tweets = await twscrape.gather(self.api.user_tweets(twitter_user_id, limit=lookback_count))

        for tweet in tweets:
            if tweet.user.id != twitter_user_id:
                continue # repost?

            created_unix = tweet.date.timestamp()

            if created_unix <= last_searched_time:
                break

            tweets_to_return.append(tweet)

        return list(reversed(tweets_to_return))

    async def sub_loop(self):
        while True:
            await asyncio.sleep(self.subscription_cooldown)

            for doc in await (self.collection.find()).to_list(None):
                channel = self.bot.get_channel(int(doc['channel']))
                if channel is None:
                    await self.collection.delete_one(doc)
                    continue

                try:
                    tweets = await self.get_tweets(int(doc['twitter_id']), doc['last_searched_time'], 'replies' in doc and doc['replies'])
                except Exception:
                    traceback.print_exc()
                    await asyncio.sleep(self.subscription_cooldown * 5)
                    continue

                if len(tweets) != 0:
                    await self.collection.update_one(doc, {'$set': {'last_searched_time': tweets[-1].date.timestamp()}})
                    for tweet in tweets:
                        await channel.send(twitter_url_from_tweet(tweet))

    async def sub_to_tweets_startup(self):
        await asyncio.sleep(5)
        await self.sub_loop()


def twitter_url_from_tweet(tweet: twscrape.Tweet) -> str:
    return tweet.url.replace('x.com', 'fixupx.com')

