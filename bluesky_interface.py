import aiohttp
import asyncio
from datetime import datetime


BASE_URL = 'https://public.api.bsky.app/'
GET_AUTHOR_FEED_PATH = 'xrpc/app.bsky.feed.getAuthorFeed'


def iso_to_unix(iso: str) -> float:
    return datetime.fromisoformat(iso.replace('Z', '+00:00')).timestamp()


async def get_posts_after_time(aiohttp_sess: aiohttp.ClientSession, handle: str, timestamp: int | float, include_replies: bool=False) -> list:
    posts_after_time = []

    feed_data = await get_user_feed(aiohttp_sess, handle, include_replies)

    for post_wrapper in feed_data['feed']:
        post = post_wrapper['post']

        if post['author']['handle'] != handle:
            # this is a repost
            continue

        created_unix = iso_to_unix(post['record']['createdAt'])
        if created_unix <= timestamp:
            break

        posts_after_time.append(post)
    
    return list(reversed(posts_after_time))


async def get_user_feed(aiohttp_sess: aiohttp.ClientSession, handle: str, include_replies: bool=False) -> dict:
    filter = 'posts_with_replies' if include_replies else 'posts_no_replies'
    response = await aiohttp_sess.get(BASE_URL + GET_AUTHOR_FEED_PATH, params={'actor': handle, 'filter': filter, 'includePins': 'false'})

    if response.status == 400:
        raise Bluesky400Error('Bluesky returned 400')
    elif response.status != 200:
        raise BlueskyNon200StatusError(f'Bluesky returned {response.status}')
    
    return await response.json()


class BlueskyNon200StatusError(Exception):
    pass


class Bluesky400Error(BlueskyNon200StatusError):
    pass


async def _test_main():
    aio_sess = aiohttp.ClientSession()

    handle = input('Enter handle: ')

    try:
        print(await get_user_feed(aio_sess, handle))
    except Bluesky400Error:
        print('400 error')


if __name__ == '__main__':
    # For testing
    asyncio.run(_test_main())
