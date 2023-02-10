import discord
from discord.ext import commands
from yelobot_utils import reply, get_channel_from_input, contains_url, discord_timestamp, YeloBot
import io
import time


class ArchivePins(commands.Cog):
    def __init__(self, bot: YeloBot, mongo) -> None:
        self.bot = bot
        self.collection = mongo['PinArchives']

    @commands.command('archivepins', aliases=['archive', 'archivechannel'])
    @commands.has_guild_permissions(kick_members=True)
    async def archive_pins(self, ctx: commands.Context, *, archive_channel=None):
        """Server Configuration
        Enabled archiving of the current channel's pins in the target channel.
        If archiving pins is currently on, use this command with no arguments to turn it off.
        +archivepins [Target Channel]
        """
        usage = '+archivepins [archive channel]\nThis will archive the current channel\'s pins inside the channel specified in the command. ' \
            'If archiving pins is currently on, calling this command with no arguments will turn it off.'

        if not archive_channel:
            if self.archiving_is_on(ctx.channel.id):
                self.toggle_archiving(ctx.channel.id)
                await reply(ctx, 'Archiving turned off.')
                return

            await reply(ctx, usage)
            return
        
        channel = get_channel_from_input(self.bot, archive_channel)
        if not channel:
            await reply(ctx, usage)
            return

        if self.archiving_is_on(ctx.channel.id):
            await reply(ctx, 'Archiving is already on in this channel.')
            return
        
        self.toggle_archiving(ctx.channel.id, channel.id)
        await reply(ctx, f'Now archiving {self.bot.get_channel(ctx.channel.id).mention} in {channel.mention}.')

    @commands.command('dontarchive', aliases=['permanent', 'noarchive'])
    @commands.has_permissions(manage_messages=True)
    async def dont_archive(self, ctx: commands.Context):
        """Server Configuration
        Disable pin archiving for the message that you are replying to. You can re-enable it by running this command again.
        +dontarchive
        """
        if not ctx.message.reference:
            await reply(ctx, 'Just reply to the message that you don\'t want to be archived while calling this command.')
            return
        
        if not discord.utils.get(await ctx.channel.pins(), id=ctx.message.reference.message_id):
            await reply(ctx, 'This message is not currently pinned.')
            return
        
        if not self.will_archive_message(ctx.channel.id, ctx.message.reference.message_id):
            self.remove_permanent_message(ctx.channel.id, ctx.message.reference.message_id)
            await reply(ctx, 'I will now archive this message when archiving pins.')
        else:
            self.add_permanent_message(ctx.channel.id, ctx.message.reference.message_id)
            await reply(ctx, 'I will keep this message pinned when archiving pins.')

    @commands.command('manualarchive')
    @commands.has_permissions(kick_members=True)
    async def manual_archive(self, ctx: commands.Context):
        """Server Configuration
        Start an archive of the pins in this channel.
        +manualarchive
        """
        if not self.archiving_is_on(ctx.channel.id):
            await reply(ctx, 'This channel does not currently archive its pins.')
            return
        
        await reply(ctx, 'Archiving pins...')
        await self.commence_archive(ctx.channel)
        await reply(ctx, 'Done.')

    async def commence_archive(self, channel: discord.TextChannel):
        if not self.archiving_is_on(channel.id):
            return
        
        doc = self.collection.find_one({'channel': channel.id})
        archive_channel = self.bot.get_channel(int(doc['archive_channel']))
        permanent_message_ids = {int(mid) for mid in doc['permanent']}

        to_unpin = []
        media_was_last = False

        for message in sorted(await channel.pins(), key=lambda msg: msg.created_at)[:-1]:
            media_was_last = False
            if message.id in permanent_message_ids:
                continue

            if sum((a.size for a in message.attachments)) > 5 * (10 ** 7):
                await reply(message, 'Cannot archive this message -- the attachments are too large.')
            else:
                if not (contains_url(message.content) or message.attachments):
                    continue

                files = []

                skip_msg = False
                for att in message.attachments:
                    async with self.bot.aiohttp_sess.get(att.url) as att_resp:
                        if att_resp.status != 200:
                            await reply(message, 'Cannot archive this message -- at least one attachment is no longer accessible.')
                            skip_msg = True
                            break
                        files.append(discord.File(io.BytesIO(await att_resp.content.read()), filename=att.filename))
                
                if skip_msg:
                    continue

                to_unpin.append((message, files))
                media_was_last = True
        
        if media_was_last:
            for file in to_unpin[-1][1]:
                file.fp.close()
            del to_unpin[-1]
            
        for message, files in to_unpin:
            await archive_channel.send(
                f'{message.author.name}#{message.author.discriminator}, {discord_timestamp(time.mktime(message.created_at.timetuple()))}:\n{message.content}'.replace('@everyone', '@-everyone'),
                files=files
                )
            for file in files:
                file.fp.close()
            await message.unpin(reason='Archived.')

    def archiving_is_on(self, channel_id: int) -> bool:
        doc = self.collection.find_one({'channel': channel_id})
        return doc and doc['active']

    def toggle_archiving(self, channel_id: int, archive_channel_id: int=0) -> bool: # returns True if turned on, False if turned off
        doc = self.collection.find_one({'channel': channel_id})
        if doc:
            new_state = not doc['active']
            self.collection.update_one(doc, {'$set': {'active': new_state, 'archive_channel': archive_channel_id}})
            return new_state
        else:
            self.collection.insert_one({'channel': channel_id, 'active': True, 'permanent': [], 'archive_channel': archive_channel_id})
            return True

    def add_permanent_message(self, channel_id: int, message_id: int):
        doc = self.collection.find_one({'channel': channel_id})
        if not doc:
            self.collection.insert_one({'channel': channel_id, 'active': False, 'permanent': [], 'archive_channel': 0})

        self.collection.update_one({'channel': channel_id}, {'$push': {'permanent': message_id}})

    def remove_permanent_message(self, channel_id: int, message_id: int) -> bool: # True if exists, False if doesn't
        doc = self.collection.find_one({'channel': channel_id})
        if not doc:
            return False

        if message_id not in tuple(int(msg_id) for msg_id in doc['permanent']):
            return False
        self.collection.update_one({'channel': channel_id}, {'$pull': {'permanent': message_id}})
        return True

    def will_archive_message(self, channel_id: int, message_id: int) -> bool:
        doc = self.collection.find_one({'channel': channel_id})
        if not doc:
            return False
        
        return message_id not in tuple(int(mid) for mid in doc['permanent'])
