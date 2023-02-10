import tweepy
from discord.ext import commands
from yelobot_utils import reply, get_channel_from_input, formatted_exception
import time
from datetime import datetime
import asyncio
import requests

def handle_request_exceptions(exception, bad_request_message):
    if isinstance(exception, tweepy.TwitterServerError):
        return 'Looks like Twitter is having issues at the moment.'
    if isinstance(exception, tweepy.BadRequest) or isinstance(exception, tweepy.NotFound):
        return bad_request_message
    if isinstance(exception, tweepy.TooManyRequests):
        print('Rate limited on Twitter!!')
        return 'Looks like I\'ve made too many requests to Twitter recently and I\'m being rate limited. Whoops.'
    return f'There was an unexpected error when trying to make a request to Twitter: \n{formatted_exception(exception)}'

def tweet_url_from_id(id, username):
    return f'https://twitter.com/{username}/status/{id}'

class Twitter(commands.Cog):
    subscription_cooldown = 60 * 5

    def __init__(self, bot, mongo, bearer):
        self.bot = bot
        self.MONGO_DB = mongo
        self.client = tweepy.Client(bearer)

    @commands.has_permissions(manage_messages=True)
    @commands.command(name='subscribetwitter', aliases=['subscribetweets', 'twittersubscribe', 'tweetsubscribe'])
    async def twitter_subscribe(self, ctx, channel=None, username=None, *, media_only=None):
        """Twitter
        Subscribe to a Twitter user in this channel. If you only want posts that contain media, add "media" to the end.
        +subscribetwitter <Channel> <Twitter @> [media]
        """
        usage = '+subscribetwitter <channel> <twitter @> [media]'

        channel = get_channel_from_input(self.bot, channel)
        if not channel or not username or (media_only is not None and media_only.lower() != 'media'):
            await reply(ctx, usage)
        
        username = username.lstrip('@')
        try:
            twitter_user = self.client.get_user(username=username)
        except tweepy.TweepyException as e:
            await reply(ctx, handle_request_exceptions(e, 'Twitter user not found.'))
            return
        
        data = twitter_user.data
        
        collection = self.MONGO_DB['TwitterSubs']

        doc = collection.find_one({'channel': channel.id, 'twitter_user_id': data.id})
        if doc:
            await reply(ctx, 'A subscription for this Twitter account already exists in that channel.')
            return

        collection.insert_one({
            'server': ctx.guild.id, 'channel': channel.id, 'twitter_user_id': data.id, 'timeframe': int(time.time()), 'media_only': True if media_only else False})

        await reply(ctx, f'Subscribed to @{data.username} in {channel.mention}{" in media-only mode" if media_only else ""}.')

    @commands.has_permissions(manage_messages=True)
    @commands.command(name='unsubtwitter', aliases=['unsubscribetweets', 'twitterunsubscribe', 'tweetunsubscribe', 'unsubtweets', 'twitterunsub', 'tweetunsub'])
    async def twitter_unsub(self, ctx, channel=None, *, username=None):
        """Twitter
        Unsubscribe from a Twitter user in this channel.
        +unsubtwitter <Channel> <Twitter @>
        """
        usage = '+unsubtwitter <channel> <twitter @>'

        channel = get_channel_from_input(self.bot, channel)
        if not channel or not username:
            await reply(ctx, usage)
            return
        
        username = username.lstrip('@')

        try:
            twitter_user = self.client.get_user(username=username)
        except tweepy.TweepyException as e:
            await reply(ctx, handle_request_exceptions(e, 'Twitter user not found.'))
            return

        collection = self.MONGO_DB['TwitterSubs']
        
        if not collection.delete_one({'channel': channel.id, 'twitter_user_id': twitter_user.data.id}):
            await reply(f'{channel.mention} is not subscribed to @{username}.')
        else:
            await reply(ctx, f'Unsubscribed from @{username} in {channel.mention}.')

    async def sub_loop(self):
        collection = self.MONGO_DB['TwitterSubs']

        while True:
            await asyncio.sleep(self.subscription_cooldown)

            for doc in collection.find():
                channel = self.bot.get_channel(int(doc['channel']))
                if channel is None:
                    collection.delete_one(doc)
                    continue

                dt = datetime.utcfromtimestamp(float(doc['timeframe']))
                
                try:
                    twitter_user = self.client.get_user(id=int(doc['twitter_user_id']))
                except requests.ConnectionError:
                    continue
                except tweepy.TweepyException as e:
                    if isinstance(e, tweepy.BadRequest) or isinstance(e, tweepy.NotFound):
                        await channel.send(e, 'Could not access a Twitter subscription\'s profile (did their acount get suspended?). Deleting subscription.')
                        print(formatted_exception(e))
                        collection.delete_one(doc)
                    elif isinstance(e, tweepy.TooManyRequests):
                        raise
                    continue

                twitter_username = twitter_user.data.username

                try:
                    timeline = self.client.get_users_tweets(
                        int(doc['twitter_user_id']), start_time=dt.isoformat('T') + 'Z', tweet_fields='attachments', exclude='retweets')
                except requests.ConnectionError:
                    continue
                except tweepy.TweepyException as e:
                    handle_request_exceptions(e, f'Could not load {twitter_username}\'s timeline. Deleting subscription.')
                    if isinstance(e, tweepy.BadRequest) or isinstance(e, tweepy.NotFound):
                        print(formatted_exception(e))
                        collection.delete_one(doc)
                    elif isinstance(e, tweepy.TooManyRequests):
                        raise
                    continue

                collection.update_one(doc, {'$set': {'timeframe': int(time.time())}})

                if timeline.data is not None:
                    for tweet in reversed(timeline.data):
                        if (not doc['media_only']) or tweet.attachments is not None:
                            await channel.send(tweet_url_from_id(tweet.id, twitter_username))

    async def sub_to_tweets_startup(self):
        await asyncio.sleep(5)
        await self.sub_loop()