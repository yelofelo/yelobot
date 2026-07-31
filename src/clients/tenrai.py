import aiohttp
import asyncio
from cachetools import TTLCache
from cachetools.keys import hashkey
from asyncache import cached
import time

TENRAI_BASE_URL = 'https://api.tenrai.org/v1'
SECONDS_TO_WAIT_BETWEEN_TENRAI_REQUESTS = 0.5

last_tenrai_request_time = 0


# Size of this can be trimmed down if necessary but these records are not large
ANIME_DETAILS_CACHE = TTLCache(maxsize=10_000, ttl=24 * 60 * 60)  # TTL is in seconds, so 24 hours

@cached(ANIME_DETAILS_CACHE, key=lambda aiohttp_sess, anime_id: hashkey(anime_id))
async def get_anime_details(aiohttp_sess: aiohttp.ClientSession, anime_id: int) -> dict:
    """Schema returned: https://api.tenrai.org/documentation#tag/anime/GET/anime/{id}"""
    global last_tenrai_request_time

    if time.time() - SECONDS_TO_WAIT_BETWEEN_TENRAI_REQUESTS <= last_tenrai_request_time:
        await asyncio.sleep((last_tenrai_request_time + SECONDS_TO_WAIT_BETWEEN_TENRAI_REQUESTS) - time.time())

    async with aiohttp_sess.get(f'{TENRAI_BASE_URL}/anime/{anime_id}') as response:
        last_tenrai_request_time = time.time()

        if response.status != 200:
            raise TenraiRequestException(response.status)
        
        return await response.json()
    

# Size of this can be trimmed down if necessary but these records are not large
MANGA_DETAILS_CACHE = TTLCache(maxsize=10_000, ttl=24 * 60 * 60)  # TTL is in seconds, so 24 hours

@cached(MANGA_DETAILS_CACHE, key=lambda aiohttp_sess, manga_id: hashkey(manga_id))
async def get_manga_details(aiohttp_sess: aiohttp.ClientSession, manga_id: int) -> dict:
    """Schema returned: https://api.tenrai.org/documentation#tag/manga/GET/manga/{id}"""
    global last_tenrai_request_time

    if time.time() - SECONDS_TO_WAIT_BETWEEN_TENRAI_REQUESTS <= last_tenrai_request_time:
        await asyncio.sleep((last_tenrai_request_time + SECONDS_TO_WAIT_BETWEEN_TENRAI_REQUESTS) - time.time())

    async with aiohttp_sess.get(f'{TENRAI_BASE_URL}/manga/{manga_id}') as response:
        last_tenrai_request_time = time.time()

        if response.status != 200:
            raise TenraiRequestException(response.status)
        
        return await response.json()


class TenraiRequestException(Exception):
    def __init__(self, status_code):
        self.status_code = status_code

    def __str__(self):
        return f'Request to Tenrai returned status {self.status_code}'
