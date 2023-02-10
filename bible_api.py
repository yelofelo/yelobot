import random
import re


BASE = 'https://api.scripture.api.bible/v1/'
BIBLE_ID = 'de4e12af7f28f599-01' # KJV

VERSE_TEXT_RE = re.compile(r'^[¶ ]*(?:\[\d*\])?[¶ ]*(.+)$')

async def get_books(aiohttp_sess, key, bible_id=BIBLE_ID):
    async with aiohttp_sess.get(f'{BASE}bibles/{bible_id}/books', headers={'api-key': key, 'accept': 'application/json'}) as resp:
        return (await resp.json())['data']

async def get_chapters(aiohttp_sess, book_id, key, bible_id=BIBLE_ID):
    async with aiohttp_sess.get(f'{BASE}bibles/{bible_id}/books/{book_id}/chapters', headers={'api-key': key, 'accept': 'application/json'}) as resp:
        return (await resp.json())['data']

async def get_verses(aiohttp_sess, chapter_id, key, bible_id=BIBLE_ID):
    async with aiohttp_sess.get(f'{BASE}bibles/{bible_id}/chapters/{chapter_id}/verses', headers={'api-key': key, 'accept': 'application/json'}) as resp:
        return (await resp.json())['data'][1:]

async def get_verse_ref_text(aiohttp_sess, verse_id, key, bible_id=BIBLE_ID):
    async with aiohttp_sess.get(f'{BASE}bibles/{bible_id}/verses/{verse_id}', params={'content-type': 'text'}, headers={'api-key': key, 'accept': 'application/json'}) as resp:
        data = (await resp.json())['data']
    raw_text = data['content']
    mo = re.match(VERSE_TEXT_RE, raw_text)
    return data['reference'], mo.group(1).strip()

async def get_random_verse(aiohttp_sess, key, bible_id=BIBLE_ID):
    while True: # API seems to just not work sometimes, infinite loop used with continues here
                #  as a hacky solution
        books = await get_books(aiohttp_sess, key, bible_id)
        if not books:
            continue
        book = random.choice(books)
        chapters = await get_chapters(aiohttp_sess, book['id'], key, bible_id)
        if not chapters:
            continue
        chapter = random.choice(chapters)
        verses = await get_verses(aiohttp_sess, chapter['id'], key, bible_id)
        if not verses:
            continue
        verse = random.choice(verses)
        return await get_verse_ref_text(aiohttp_sess, verse['id'], key, bible_id)
