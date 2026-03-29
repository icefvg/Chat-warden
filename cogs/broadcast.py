import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging

logger = logging.getLogger(__name__)

class BroadcastCommand(commands.Cog):
    """Broadcast command for bot owners to send announcements to all servers"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="broadcast", description="Broadcast a message to all servers (Owner Only)")
    @app_commands.describe(message="The message to broadcast")
    @commands.is_owner()
    async def broadcast(self, ctx, *, message: str):
        """Broadcast an announcement to all servers the bot is in"""

        # Confirmation step
        confirm_embed = discord.Embed(
            title="⚠️ Broadcast Confirmation",
            description=f"Are you sure you want to broadcast this message to **all {len(self.bot.guilds)} servers**?\n\n**Preview:**\n{message}",
            color=discord.Color.orange()
        )
        confirm_embed.set_footer(text="Type 'yes' to confirm or 'no' to cancel. Request times out in 30 seconds.")

        await ctx.send(embed=confirm_embed, ephemeral=True)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("Broadcast cancelled due to timeout.", ephemeral=True)
            return

        if msg.content.lower() == 'no':
            await ctx.send("Broadcast cancelled.", ephemeral=True)
            return

        # Acknowledge start
        progress_msg = await ctx.send("🚀 Starting broadcast... This may take a while.", ephemeral=True)

        success_count = 0
        failed_count = 0

        # Create broadcast embed
        broadcast_embed = discord.Embed(
            title="📢 Global Announcement",
            description=message,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        broadcast_embed.set_footer(text=f"From {self.bot.user.name} Developer")

        # Start broadcasting
        for guild in self.bot.guilds:
            try:
                # 1. Database announcement_channel
                guild_settings = await self.bot.db.get_guild_settings(guild.id)
                announcement_channel_id = guild_settings.get('announcement_channel')

                target_channel = None

                if announcement_channel_id:
                    target_channel = guild.get_channel(announcement_channel_id)

                # 2. Channel named "announcements"
                if not target_channel or not self._can_send(target_channel, guild.me):
                    target_channel = discord.utils.get(guild.text_channels, name="announcements")

                # 3. Channel named "general"
                if not target_channel or not self._can_send(target_channel, guild.me):
                    target_channel = discord.utils.get(guild.text_channels, name="general")

                # 4. Fallback to first available text channel
                if not target_channel or not self._can_send(target_channel, guild.me):
                    for channel in guild.text_channels:
                        if self._can_send(channel, guild.me):
                            target_channel = channel
                            break

                if target_channel:
                    try:
                        await target_channel.send(embed=broadcast_embed)
                        success_count += 1
                        logger.info(f"Broadcast successful in guild: {guild.name} (ID: {guild.id})")
                    except discord.Forbidden:
                        failed_count += 1
                        logger.warning(f"Forbidden to send broadcast in guild: {guild.name} (ID: {guild.id})")
                    except discord.HTTPException as e:
                        failed_count += 1
                        logger.error(f"HTTP Exception while broadcasting in guild: {guild.name} (ID: {guild.id}): {e}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Unknown error while broadcasting in guild: {guild.name} (ID: {guild.id}): {e}")
                else:
                    failed_count += 1
                    logger.warning(f"No valid channel found for broadcast in guild: {guild.name} (ID: {guild.id})")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing guild {guild.name} for broadcast: {e}")

            # Rate limiting delay
            await asyncio.sleep(1)

        # Send final report
        report_embed = discord.Embed(
            title="✅ Broadcast Completed",
            description=f"**Results:**\n✅ {success_count} successful\n❌ {failed_count} failed",
            color=discord.Color.green() if failed_count == 0 else discord.Color.orange()
        )
        await ctx.send(embed=report_embed, ephemeral=True)

    def _can_send(self, channel, member):
        """Check if bot has permissions to send messages and embeds in the channel"""
        if not channel or not isinstance(channel, discord.TextChannel):
            return False
        perms = channel.permissions_for(member)
        return perms.send_messages and perms.embed_links

async def setup(bot):
    await bot.add_cog(BroadcastCommand(bot))
