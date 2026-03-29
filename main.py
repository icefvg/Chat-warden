import discord
from discord.ext import commands
import os
import json
import asyncio
import logging
from config import Config
from database import Database
from webhook_manager import WebhookManager
from profanity_filter import ProfanityFilter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiscordModerationBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.moderation = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        self.config = Config()
        self.db = Database()
        self.webhook_manager = WebhookManager(self)
        self.profanity_filter = ProfanityFilter()
        
    async def get_prefix(self, message):
        """Get command prefix for guild"""
        if not message.guild:
            return ['!', '?', '/']
        
        guild_settings = await self.db.get_guild_settings(message.guild.id)
        return guild_settings.get('prefix', ['!', '?', '/'])
    
    async def setup_hook(self):
        """Load cogs and sync commands"""
        try:
            # Load all cogs
            cogs_to_load = [
                'cogs.admin',
                'cogs.moderation', 
                'cogs.profanity',
                'cogs.advanced_moderation',
                'cogs.utility',
                'cogs.help'
            ]
            
            for cog in cogs_to_load:
                try:
                    await self.load_extension(cog)
                    logger.info(f"Loaded cog: {cog}")
                except Exception as e:
                    logger.error(f"Failed to load cog {cog}: {e}")
            
            # Sync slash commands
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash command(s)")
            
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
    
    async def on_ready(self):
        """Bot ready event"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        logger.info(f'Bot can see {len(self.users)} users')
        
        # Set bot activity
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for bad words | Use /help or !help"
        )
        await self.change_presence(
            status=discord.Status.online,
            activity=activity
        )
        
        # Initialize data for existing guilds
        for guild in self.guilds:
            await self.db.get_guild_settings(guild.id)
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Initialize guild settings
        await self.db.get_guild_settings(guild.id)
        
        # Try to send welcome message to the first available text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="🛡️ Moderation Bot Added!",
                    description=(
                        "Thanks for adding me to your server!\n\n"
                        "**Key Features:**\n"
                        "• Advanced profanity filtering with bypass detection\n"
                        "• Complete moderation command suite\n"
                        "• Automatic message replacement via webhooks\n"
                        "• Comprehensive logging and tracking\n\n"
                        "**Quick Setup:**\n"
                        "• Use `/toggle_profanity` to enable/disable filtering\n"
                        "• Use `/set_channels` to configure active channels\n"
                        "• Use `/set_log_channel` for moderation logs\n\n"
                        "**Commands:** Use `/help` or `!help` to see all commands"
                    ),
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Pro tip: I work with both slash commands (/) and prefixes (!)")
                
                try:
                    await channel.send(embed=embed)
                    break
                except:
                    continue
    
    async def on_message(self, message):
        """Process messages for profanity filtering"""
        if message.author.bot:
            return
            
        if not message.guild:
            return
            
        # Check if profanity filter is enabled for this guild
        guild_settings = await self.db.get_guild_settings(message.guild.id)
        if not guild_settings.get('profanity_enabled', True):
            await self.process_commands(message)
            return
            
        # Check if channel is in enabled channels list
        enabled_channels = guild_settings.get('enabled_channels', [])
        if enabled_channels and message.channel.id not in enabled_channels:
            await self.process_commands(message)
            return
            
        # Check for profanity
        contains_profanity, censored_content = await self.profanity_filter.check_message(message.content)
        
        if contains_profanity:
            # Check cooldown
            if await self.profanity_filter.is_on_cooldown(message.author.id):
                await self.process_commands(message)
                return
                
            try:
                # Delete original message
                await message.delete()
                
                # Send censored message via webhook
                success = await self.webhook_manager.send_censored_message(
                    message.channel,
                    message.author,
                    censored_content
                )
                
                if not success:
                    # Fallback: send as embed if webhook fails
                    embed = discord.Embed(
                        description=f"**{message.author.display_name}:** {censored_content}",
                        color=discord.Color.blue()
                    )
                    embed.set_author(
                        name=message.author.display_name,
                        icon_url=message.author.display_avatar.url
                    )
                    embed.set_footer(text="⚠️ Message was filtered for profanity")
                    await message.channel.send(embed=embed)
                
                # Add to cooldown
                await self.profanity_filter.add_cooldown(message.author.id)
                
                # Log the action
                await self.log_profanity_action(message, censored_content)
                
            except discord.Forbidden:
                logger.warning(f"Missing permissions to delete message in {message.guild.name}")
            except Exception as e:
                logger.error(f"Error processing profanity: {e}")
        
        await self.process_commands(message)
    
    async def log_profanity_action(self, message, censored_content):
        """Log profanity filtering action"""
        guild_settings = await self.db.get_guild_settings(message.guild.id)
        log_channel_id = guild_settings.get('log_channel')
        
        if log_channel_id:
            log_channel = self.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="🚫 Profanity Filtered",
                    color=discord.Color.orange(),
                    timestamp=message.created_at
                )
                embed.add_field(name="User", value=f"{message.author} ({message.author.id})", inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                embed.add_field(name="Message ID", value=str(message.id), inline=True)
                embed.add_field(name="Original", value=f"```{message.content[:1000]}```", inline=False)
                embed.add_field(name="Censored", value=f"```{censored_content[:1000]}```", inline=False)
                embed.set_thumbnail(url=message.author.display_avatar.url)
                
                try:
                    await log_channel.send(embed=embed)
                except Exception as e:
                    logger.warning(f"Failed to send log message: {e}")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Missing Permissions", 
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ', '.join(error.missing_permissions)
            embed = discord.Embed(
                title="❌ Bot Missing Permissions", 
                description=f"I need the following permissions: {missing_perms}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Command on Cooldown", 
                description=f"Try again in {error.retry_after:.2f} seconds.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Argument", 
                description=f"Missing required argument: `{error.param.name}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Invalid Argument", 
                description=str(error),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            logger.error(f"Unhandled error in {ctx.command}: {error}", exc_info=error)
            embed = discord.Embed(
                title="❌ An Error Occurred", 
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    async def close(self):
        """Clean up when bot shuts down"""
        logger.info("Bot shutting down...")
        await self.webhook_manager.close()
        await super().close()

async def main():
    """Main function to run the bot"""
    bot = DiscordModerationBot()
    
    try:
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN environment variable not found!")
            return
            
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
