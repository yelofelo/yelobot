from yelobot_utils import YeloBot
from typing import Callable
from datetime import datetime, timedelta
import asyncio
import discord


DELTARUNE_RELEASE = datetime(year=2025, month=6, day=5, hour=4, minute=0, second=0)
DELTARUNE_RELEASE_SUFFIX = 'until DELTARUNE releases!'


async def update_status(bot: YeloBot, get_status_message: Callable, calculate_refresh_time: Callable, base_game_status: str, end_condition: Callable):
    while True:
        if end_condition():
            await bot.change_presence(activity=discord.Game(name=base_game_status))
            return
        message = get_status_message()
        await bot.change_presence(activity=discord.CustomActivity(name=message))
        await asyncio.sleep(calculate_refresh_time())


def get_remaining_time_until_deltarune(td: timedelta) -> str:
    if td.days == 1:
        return f'1 day {DELTARUNE_RELEASE_SUFFIX}'
    elif td.days:
        return f'{td.days} days {DELTARUNE_RELEASE_SUFFIX}'
    elif (td.seconds > 60 * 60) and (td.seconds // (60 * 60)) == 1:
        return f'1 hour {DELTARUNE_RELEASE_SUFFIX}'
    elif td.seconds > 60 * 60:
        hours_remaining = td.seconds // (60 * 60)
        return f'{hours_remaining} hours {DELTARUNE_RELEASE_SUFFIX}'
    elif td.seconds // 60 == 1:
        return f'1 minute {DELTARUNE_RELEASE_SUFFIX}'
    else:
        minutes_remaining = td.seconds // 60
        return f'{minutes_remaining} minutes {DELTARUNE_RELEASE_SUFFIX}'



def generate_deltarune_status_message():
    now = datetime.now()
    diff = DELTARUNE_RELEASE - now
    return get_remaining_time_until_deltarune(diff)
    

def deltarune_status_end_condition():
    return datetime.now() >= DELTARUNE_RELEASE
