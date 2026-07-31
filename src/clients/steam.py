import aiohttp

# Other things should be moved in here eventually. Some of the Steam fetch logic is still in bot.py.
# Also maybe this should just become a cog one day. That would make more sense.

STEAM_APPDETAILS_URL = 'https://store.steampowered.com/api/appdetails'



async def get_price_info(aiohttp_sess: aiohttp.ClientSession, app_id: str | int, currency: str) -> tuple[int, dict]:
    details_params = {'appids': app_id, 'l': 'en_us', 'cc': currency}
    async with aiohttp_sess.get(STEAM_APPDETAILS_URL, params=details_params) as response:
        if response.status != 200:
            return response.status, None
        return response.status, await response.json()
