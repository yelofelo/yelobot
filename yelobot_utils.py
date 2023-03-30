import discord
from discord.ext import commands
import time
import asyncio
from functools import partial
import io
import aiohttp
import re

URL_RE = re.compile(r'https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)')
MIME_MEDIA_RE = re.compile(r'^((image)|(video)|(audio))/.+$')

class YeloBot(commands.Bot):
    def __init__(self, *args, **kargs):
        self.aiohttp_sess: aiohttp.ClientSession = None
        super().__init__(*args, **kargs)
    
    def set_aiohttp_sess(self, sess: aiohttp.ClientSession):
        self.aiohttp_sess = sess

def get(iterable, **kargs):
    """An alternate implementation of discord.utils.get"""
    for element in iterable:
        if all((getattr(element, attr) == kargs[attr] for attr in kargs)):
            return element

def get_all(iterable, **kargs):
    for element in iterable:
        if all((getattr(element, attr) == kargs[attr] for attr in kargs)):
            yield element

async def reply(messagable: discord.abc.Messageable, message=None, **kargs):
    await messagable.reply(message, mention_author=False, **kargs)

def search_for_user(ctx, name_given):
    name_given = name_given.rstrip('>').lstrip('<@').lstrip('<@!')

    for user in ctx.guild.members:
        if name_given.lower() == str(user).lower() or str(user.id) == name_given:
            return user
    for user in ctx.guild.members:
        if name_given.lower() == user.display_name.lower():
            return user
    for user in ctx.guild.members:
        if user.nick is not None and name_given.lower() == user.nick.lower():
            return user
    for user in ctx.guild.members:
        if name_given.lower() in str(user).lower():
            return user
    for user in ctx.guild.members:
        if user.nick is not None and name_given.lower() in user.nick.lower():
            return user

def discord_timestamp(unix_time):
    return f'<t:{int(unix_time)}>'

def contains_url(text):
    return bool(re.search(URL_RE, text))

def get_urls_from_text(text):
    for url in re.findall(URL_RE, text):
        yield url

async def url_is_media(aiohttp_sess, url):
    async with aiohttp_sess.get(url) as resp:
        if resp.status != 200 or 'content-type' not in resp.headers:
            return False
        
        return bool(re.match(MIME_MEDIA_RE, resp.headers['content-type']))

def time_remaining(unix_time):
    time_conversions = [(604800, 'weeks'), (86400, 'days'), (3600, 'hours'), (60, 'minutes'), (1, 'seconds')]
    current_timestamp = time.time()

    out_str = ''
    remaining = unix_time - current_timestamp

    for secs, unit in time_conversions:
        time_for_unit, remaining = divmod(remaining, secs)
        if time_for_unit == 1:
            out_str += f'1 {unit.rstrip("s")} '
        elif time_for_unit != 0:
            out_str += f'{int(time_for_unit)} {unit} '
        
        if remaining == 0:
            break
    
    return out_str.strip()

async def send_image(messagable, content, img_data, filename, send_as_reply=True):
    with io.BytesIO(img_data) as img_data_bytes:
        if send_as_reply:
            await reply(messagable, content, file=discord.File(img_data_bytes, filename=filename))
        else:
            await messagable.send(content, file=discord.File(img_data_bytes, filename=filename))

def get_channel_from_input(bot, input_text):
    try:
        channel_id = int(input_text.lstrip('<#').rstrip('>'))
        channel = bot.get_channel(channel_id)
    except:
        channel = None
    
    return channel


def formatted_exception(exception):
    return str(type(exception)).lstrip('<class \'').rstrip('\'>') + f': {exception}'

class PaginationButton(discord.ui.Button):
    def __init__(self, **kargs):
        self.pagination_callback_fn = None
        super().__init__(**kargs)

    def set_callback(self, callback):
        self.pagination_callback_fn = callback

    def set_message_data(self, message_data):
        self.callback = partial(self.pagination_callback_fn, message_data)

class Pagination:
    TIMEOUT = 180
    message_data = dict()
    prev_label = None
    next_label = None

    @staticmethod
    async def set_emojis(guild, prev_name, next_name):
        Pagination.prev_label = discord.utils.get(guild.emojis, name=prev_name)
        Pagination.next_label = discord.utils.get(guild.emojis, name=next_name)

    @staticmethod
    async def send_paginated_embed(ctx, fields, title=None, color=None, fields_on_page=15, read_data_fn=lambda x: x, read_data_async_fn=None, additional_buttons=None):
        if additional_buttons is None:
            additional_buttons = []

        description = ''

        if len(fields) == 0:
            reply(ctx, 'No results.')
            return
        
        if read_data_async_fn is not None:
            if fields_on_page == 1:
                description = await read_data_async_fn(fields[0])
            elif len(fields) <= fields_on_page:
                description = '\n'.join([await read_data_async_fn(field) for field in fields])
            else:
                description = '\n'.join([await read_data_async_fn(field) for field in fields[:fields_on_page]])
        else:
            if fields_on_page == 1:
                description = read_data_fn(fields[0])
            elif len(fields) <= fields_on_page:
                description = '\n'.join([read_data_fn(field) for field in fields])
            else:
                description = '\n'.join([read_data_fn(field) for field in fields[:fields_on_page]])

        max_page = ((len(fields) - 1) // fields_on_page) + 1

        prev_button = discord.ui.Button(style=discord.ButtonStyle.primary, emoji=Pagination.prev_label, disabled=True)
        next_button = discord.ui.Button(style=discord.ButtonStyle.primary, emoji=Pagination.next_label, disabled=max_page == 1)

        prev_button.callback = Pagination.generate_callback('prev')
        next_button.callback = Pagination.generate_callback('next')

        message_data = {
            'author': ctx.author.id, 'fields': fields, 'on_page': 1, 'fields_on_page': fields_on_page, 'max_page': max_page,
            'next_button': next_button, 'prev_button': prev_button, 'title': title, 'color': color, 'field_idx': 0, 'time': time.time(),
            'read_data_fn': read_data_fn, 'read_data_async_fn': read_data_async_fn, 'additional_buttons': additional_buttons
            }

        buttons = [prev_button, next_button]

        for button in additional_buttons:
            button.set_message_data(message_data)
            buttons.append(button)

        view = discord.ui.View(timeout=Pagination.TIMEOUT)

        for button in buttons:
            view.add_item(button)

        embed = discord.Embed(title=title, color=color, description=description)
        embed.set_footer(text=f'Page 1/{max_page}')

        message = await ctx.reply(embed=embed, view=view, mention_author=False)
        Pagination.message_data[message.id] = message_data
        await Pagination.deletion_thread(message)
    
    @staticmethod
    def generate_callback(cb_type='next'):
        async def callback(interaction: discord.Interaction):
            data = Pagination.message_data[interaction.message.id]
            if data['author'] != interaction.user.id:
                await interaction.response.defer()
                return
            
            if cb_type == 'next':
                data['on_page'] += 1
                data['field_idx'] += data['fields_on_page']
                data['prev_button'].disabled = False
                if data['on_page'] == data['max_page']:
                    data['next_button'].disabled = True
            elif cb_type == 'prev':
                data['on_page'] -= 1
                data['field_idx'] -= data['fields_on_page']
                data['next_button'].disabled = False
                if data['on_page'] == 1:
                    data['prev_button'].disabled = True
            else:
                raise ValueError(f'Invalid callback type {cb_type}')

            if data['read_data_async_fn'] is not None:
                if data['fields_on_page'] == 1:
                    desc = await (data['read_data_async_fn'])(data['fields'][data['field_idx']])
                elif data['field_idx'] + data['fields_on_page'] >= len(data['fields']):
                    desc = '\n'.join([await (data['read_data_async_fn'])(field) for field in data['fields'][data['field_idx']:]])
                else:
                    desc = '\n'.join([await (data['read_data_async_fn'])(field) for field in data['fields'][data['field_idx']:(data['field_idx'] + data['fields_on_page'])]])
            else:
                if data['fields_on_page'] == 1:
                    desc = data['read_data_fn'](data['fields'][data['field_idx']])
                elif data['field_idx'] + data['fields_on_page'] >= len(data['fields']):
                    desc = '\n'.join([data['read_data_fn'](field) for field in data['fields'][data['field_idx']:]])
                else:
                    desc = '\n'.join([data['read_data_fn'](field) for field in data['fields'][data['field_idx']:(data['field_idx'] + data['fields_on_page'])]])
            
            embed = discord.Embed(description=desc, title=data['title'], color=data['color'])
            embed.set_footer(text=f'Page {data["on_page"]}/{data["max_page"]}')

            new_view = discord.ui.View(timeout=Pagination.TIMEOUT - (time.time() - data['time']))
            new_view.add_item(data['prev_button'])
            new_view.add_item(data['next_button'])
            for button in data['additional_buttons']:
                new_view.add_item(button)

            await interaction.response.edit_message(
                embed=embed,
                view=new_view
                )

        return callback

    @staticmethod
    async def deletion_thread(message):
        await asyncio.sleep(Pagination.TIMEOUT)

        prev_button = discord.ui.Button(style=discord.ButtonStyle.primary, emoji=Pagination.prev_label, disabled=True)
        next_button = discord.ui.Button(style=discord.ButtonStyle.primary, emoji=Pagination.next_label, disabled=True)

        buttons = [prev_button, next_button]

        for button in Pagination.message_data[message.id]['additional_buttons']:
            buttons.append(discord.ui.Button(style=button.style, emoji=button.emoji, label=button.label, disabled=True))

        new_view = discord.ui.View()

        for button in buttons:
            new_view.add_item(button)

        await message.edit(view=new_view)
        del Pagination.message_data[message.id]
