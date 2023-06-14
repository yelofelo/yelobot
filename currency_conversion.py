from discord.ext import commands
from yelobot_utils import reply, YeloBot
import time
import asyncio
import re

class CurrencyConversion(commands.Cog):
    BASE_CURRENCY = 'EUR'
    BASE_API_URL = 'http://api.exchangeratesapi.io/v1/latest'
    MAX_RETRIES = 3
    RETRY_INTERVAL = 5 * 60
    CURRENCY_RECACHE_INTERVAL = 24 * 60 * 60
    AMOUNT_RE = re.compile(r'(?P<integer>^\d+$)|(?P<decimal>^\d+\.\d\d$)')

    def __init__(self, bot: YeloBot, mongo_db, exchange_api_key: str):
        self.bot = bot
        self.collection = mongo_db['Currencies']
        self.api_key = exchange_api_key

    @commands.command('convertcurrency', aliases=['currency', 'convert'])
    async def convert_currency_cmd(self, ctx: commands.Context, amount: str=None, original_currency: str=None, new_currency: str=None):
        """Utility
        Convert between different currencies. Currency information is updated daily.
        +convertcurrency <Amount> <Original Currency> <New Currency>
        """
        usage = '+convertcurrency <Amount> <Original Currency> <New Currency>'

        if None in (amount, original_currency, new_currency):
            await reply(ctx, usage)
            return
        
        mo = re.match(self.AMOUNT_RE, amount)
        if not mo:
            await reply(ctx, usage + 
                        '\nMake sure the amount you enter is just a number with no commas, using ' + 
                        'a period as a decimal point (eg. 100 or 100.50).')
            return
        
        if mo.group('integer'):
            numeric_amt = int(amount)
        else:
            numeric_amt = float(amount)

        original_currency = original_currency.upper()
        new_currency = new_currency.upper()

        doc = await self.collection.find_one()
        rates = doc['rates']

        if original_currency not in rates:
            await reply(ctx, usage + f'\n{original_currency} is not a valid currency code.')
            return
        if new_currency not in rates:
            await reply(ctx, usage + f'\n{new_currency} is not a valid currency code.')
            return

        if new_currency == original_currency:
            await reply(ctx, 'good one')
            return
        
        converted_amount = self.convert_currencies(numeric_amt, original_currency, new_currency, rates)

        await reply(ctx, f'**{numeric_amt:.2f} {original_currency}** is equal to {converted_amount:.2f} {new_currency}**.')

    def convert_currencies(self, amount: int | float, original_currency: str, new_currency: str, rates: dict[str, float]) -> int | float:
        if original_currency == self.BASE_CURRENCY:
            return amount * rates[new_currency]
        elif new_currency == self.BASE_CURRENCY:
            return amount / rates[original_currency]
        else:
            amount_in_base = amount / rates[original_currency]
            return amount_in_base * rates[new_currency]

    async def update_currencies(self):
        await self.bot.wait_until_ready()

        while True:
            doc = await self.collection.find_one()
            if not doc:
                doc = await self.insert_initial_doc()

            last_updated = doc['last_updated']
            time_remaining = (last_updated + self.CURRENCY_RECACHE_INTERVAL) - time.time()

            if time_remaining <= 0:
                new_rates = self.fetch_exchange_rates()
                await self.collection.update_one(doc, {'rates': new_rates, 'last_updated': time.time()})
                await asyncio.sleep(self.CURRENCY_RECACHE_INTERVAL)
            else:
                await asyncio.sleep(time_remaining)
        

    async def insert_initial_doc(self):
        rates = await self.fetch_exchange_rates()

        to_insert = {'rates': rates, 'last_updated': time.time()}
        await self.collection.insert_one(to_insert)

        return to_insert

    async def fetch_exchange_rates(self):
        # This method will auto-retry
        retry_count = 0
        
        while True:
            async with self.bot.aiohttp_sess.get(self.BASE_API_URL,
                params={'access_key': self.api_key, 'base': self.BASE_CURRENCY}) as response:
                
                if response.status == 200:
                    json_data = await response.json()
                    break
                else:
                    print(await response.content.read())

                retry_count += 1
                if retry_count == self.MAX_RETRIES:
                    print(f'FAILED TO FETCH EXCHANGE RATES: {response.status}')
                    return
                
            await asyncio.sleep(self.RETRY_INTERVAL)

        return json_data['rates']
