import aiohttp
import asyncio
import time
import feedparser
import enum
import calendar


MAL_RSS_BASE_URL = 'https://myanimelist.net/rss.php'
SECONDS_TO_WAIT_BETWEEN_MAL_REQUESTS = 1

last_mal_request_time = 0


class MALContentType(enum.Enum):
    ANIME = enum.auto()
    MANGA = enum.auto()

async def get_mal_rss(aiohttp_sess: aiohttp.ClientSession, content_type: MALContentType, username: str) -> list[tuple[int, int, str, str]]:
    """Returns a list of tuples of anime/manga ID, publish timestamp, a title, and description of the status"""
    global last_mal_request_time

    if time.time() - SECONDS_TO_WAIT_BETWEEN_MAL_REQUESTS <= last_mal_request_time:
        await asyncio.sleep((last_mal_request_time + SECONDS_TO_WAIT_BETWEEN_MAL_REQUESTS) - time.time())

    async with aiohttp_sess.get(MAL_RSS_BASE_URL, params={'type': 'rm' if content_type == MALContentType.MANGA else 'rw', 'u': username}) as response:
        last_mal_request_time = time.time()

        if response.status != 200:
            raise MALRSSRequestException(response.status)
        
        resp_text = await response.text()

        fp_dict = feedparser.parse(resp_text)

        return [(int(entry.link.split('/')[4]), calendar.timegm(entry.published_parsed), entry.title, entry.description) for entry in fp_dict.entries]


class MALRSSRequestException(Exception):
    def __init__(self, status_code):
        self.status_code = status_code

    def __str__(self):
        return f'Request to MAL RSS returned status {self.status_code}'
