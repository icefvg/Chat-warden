import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import has_permissions, create_embed, create_error_embed, create_success_embed, create_info_embed
import re

class AdminCommands(commands.Cog):
    """Administrative commands for bot configuration"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="toggle_profanity", description="Enable or disable profanity filtering")
    @app_commands.describe(enabled="Whether to enable profanity filtering")
    @has_permissions(manage_guild=True)
    async def toggle_profanity(self, ctx, enabled: bool = None):
        """Toggle profanity filtering for the guild"""
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        
        if enabled is None:
            current = guild_settings.get('profanity_enabled', True)
            enabled = not current
        
        await self.bot.db.update_guild_settings(ctx.guild.id, {'profanity_enabled': enabled})
        
        status = "enabled" if enabled else "disabled"
        embed = create_success_embed(f"Profanity filtering has been **{status}** for this server.")
        
        if enabled:
            embed.add_field(
                name="Next Steps",
                value=(
                    "• Use `/set_channels` to configure specific channels\n"
                    "• Use `/set_log_channel` to set up logging\n"
                    "• Use `/add_censor` to add custom words"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="set_channels", description="Set channels where profanity filtering is active")
    @app_commands.describe(channels="Channels to enable filtering in (leave empty for all channels)")
    @has_permissions(manage_guild=True)
    async def set_channels(self, ctx, channels: str = None):
        """Set channels where profanity filtering is active"""
        if not channels:
            # Enable for all channels
            await self.bot.db.update_guild_settings(ctx.guild.id, {'enabled_channels': []})
            embed = create_success_embed("Profanity filtering enabled for **all channels**.")
        else:
            # Parse channel mentions and names
            channel_ids = []
            channel_names = []
            
            # Split by spaces and commas
            channel_inputs = re.split(r'[,\s]+', channels)
            
            for channel_input in channel_inputs:
                channel_input = channel_input.strip()
                if not channel_input:
                    continue
                
                channel = None
                
                # Try mention format
                if channel_input.startswith('<#') and channel_input.endswith('>'):
                    try:
                        channel_id = int(channel_input[2:-1])
                        channel = ctx.guild.get_channel(channel_id)
                    except ValueError:
                        continue
                # Try channel name
                else:
                    channel = discord.utils.get(ctx.guild.text_channels, name=channel_input)
                
                if channel and isinstance(channel, discord.TextChannel):
                    channel_ids.append(channel.id)
                    channel_names.append(channel.mention)
            
            if not channel_ids:
                embed = create_error_embed("No valid channels found. Use channel mentions (#general) or channel names.")
                await ctx.send(embed=embed)
                return
            
            await self.bot.db.update_guild_settings(ctx.guild.id, {'enabled_channels': channel_ids})
            embed = create_success_embed(f"Profanity filtering enabled for: {', '.join(channel_names)}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="set_log_channel", description="Set the moderation log channel")
    @app_commands.describe(channel="Channel for moderation logs")
    @has_permissions(manage_guild=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the moderation log channel"""
        if channel is None:
            await self.bot.db.update_guild_settings(ctx.guild.id, {'log_channel': None})
            embed = create_success_embed("Moderation logging has been **disabled**.")
        else:
            # Check if bot can send messages in the channel
            if not channel.permissions_for(ctx.guild.me).send_messages:
                embed = create_error_embed(f"I don't have permission to send messages in {channel.mention}.")
                await ctx.send(embed=embed)
                return
            
            await self.bot.db.update_guild_settings(ctx.guild.id, {'log_channel': channel.id})
            embed = create_success_embed(f"Moderation logs will be sent to {channel.mention}.")
            
            # Send test message
            test_embed = create_info_embed("Moderation logging has been enabled for this channel.")
            test_embed.set_footer(text="This is a test message")
            try:
                await channel.send(embed=test_embed)
            except:
                embed.add_field(name="Warning", value="Could not send test message to channel.", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="add_censor", description="Add a word to the profanity filter")
    @app_commands.describe(word="Word to censor", replacement="Replacement text")
    @has_permissions(manage_messages=True)
    async def add_censor(self, ctx, word: str, replacement: str = None):
        """Add a word to the profanity filter"""
        if len(word) < 2:
            embed = create_error_embed("Word must be at least 2 characters long.")
            await ctx.send(embed=embed)
            return
        
        await self.bot.profanity_filter.add_word(word, 'custom', replacement)
        
        if replacement:
            embed = create_success_embed(f"Added `{word}` to filter with replacement `{replacement}`.")
        else:
            embed = create_success_embed(f"Added `{word}` to filter with default replacement.")
        
        embed.add_field(
            name="Tip",
            value="The filter will automatically detect variations like l33tspeak and obfuscation.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="remove_censor", description="Remove a word from the profanity filter")
    @app_commands.describe(word="Word to remove from filter")
    @has_permissions(manage_messages=True)
    async def remove_censor(self, ctx, word: str):
        """Remove a word from the profanity filter"""
        removed = await self.bot.profanity_filter.remove_word(word)
        
        if removed:
            embed = create_success_embed(f"Removed `{word}` from the profanity filter.")
        else:
            embed = create_error_embed(f"`{word}` was not found in the profanity filter.")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="list_censors", description="List all censored words")
    @has_permissions(manage_messages=True)
    async def list_censors(self, ctx):
        """List all censored words"""
        word_counts = self.bot.profanity_filter.get_word_count()
        
        embed = create_embed("📋 Profanity Filter Statistics", color=discord.Color.blue())
        
        total_words = sum(word_counts.values())
        embed.add_field(name="Total Words", value=f"{total_words:,}", inline=True)
        
        # Status
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        status = "🟢 Enabled" if guild_settings.get('profanity_enabled', True) else "🔴 Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Channel info
        enabled_channels = guild_settings.get('enabled_channels', [])
        if enabled_channels:
            channel_count = len(enabled_channels)
            embed.add_field(name="Active Channels", value=f"{channel_count} specific", inline=True)
        else:
            embed.add_field(name="Active Channels", value="All channels", inline=True)
        
        # Word breakdown
        if word_counts:
            breakdown = []
            for category, count in sorted(word_counts.items()):
                if count > 0:
                    emoji = {
                        'mild': '🟡',
                        'moderate': '🟠', 
                        'severe': '🔴',
                        'slurs': '⚫',
                        'custom': '🔵'
                    }.get(category, '⚪')
                    breakdown.append(f"{emoji} **{category.title()}:** {count:,}")
            
            if breakdown:
                embed.add_field(
                    name="Categories", 
                    value='\n'.join(breakdown), 
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="set_prefix", description="Set command prefix for this server")
    @app_commands.describe(prefix="New command prefix")
    @has_permissions(manage_guild=True)
    async def set_prefix(self, ctx, prefix: str):
        """Set command prefix for this server"""
        if len(prefix) > 5:
            embed = create_error_embed("Prefix cannot be longer than 5 characters.")
            await ctx.send(embed=embed)
            return
        
        if prefix in ['/', '@', '#']:
            embed = create_error_embed("That prefix is reserved and cannot be used.")
            await ctx.send(embed=embed)
            return
        
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        current_prefixes = guild_settings.get('prefix', ['!', '?', '/'])
        
        if prefix not in current_prefixes:
            current_prefixes.append(prefix)
        
        await self.bot.db.update_guild_settings(ctx.guild.id, {'prefix': current_prefixes})
        
        embed = create_success_embed(f"Added `{prefix}` as a command prefix.")
        embed.add_field(
            name="All Prefixes", 
            value=", ".join(f"`{p}`" for p in current_prefixes), 
            inline=False
        )
        embed.add_field(
            name="Note",
            value="Slash commands (/) always work regardless of prefix settings.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="remove_prefix", description="Remove a command prefix")
    @app_commands.describe(prefix="Prefix to remove")
    @has_permissions(manage_guild=True)
    async def remove_prefix(self, ctx, prefix: str):
        """Remove a command prefix"""
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        current_prefixes = guild_settings.get('prefix', ['!', '?', '/'])
        
        if prefix not in current_prefixes:
            embed = create_error_embed(f"`{prefix}` is not a current prefix.")
            await ctx.send(embed=embed)
            return
        
        if len(current_prefixes) == 1:
            embed = create_error_embed("Cannot remove the last prefix. Add another prefix first.")
            await ctx.send(embed=embed)
            return
        
        current_prefixes.remove(prefix)
        await self.bot.db.update_guild_settings(ctx.guild.id, {'prefix': current_prefixes})
        
        embed = create_success_embed(f"Removed `{prefix}` from command prefixes.")
        embed.add_field(
            name="Remaining Prefixes", 
            value=", ".join(f"`{p}`" for p in current_prefixes), 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="server_settings", description="Show current server settings")
    @has_permissions(manage_guild=True)
    async def server_settings(self, ctx):
        """Show current server settings"""
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        
        embed = create_embed(f"⚙️ Server Settings - {ctx.guild.name}", color=discord.Color.blue())
        
        # Profanity filter settings
        profanity_status = "🟢 Enabled" if guild_settings.get('profanity_enabled', True) else "🔴 Disabled"
        embed.add_field(name="Profanity Filter", value=profanity_status, inline=True)
        
        # Enabled channels
        enabled_channels = guild_settings.get('enabled_channels', [])
        if enabled_channels:
            channel_mentions = []
            for channel_id in enabled_channels[:3]:  # Show first 3
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channel_mentions.append(channel.mention)
            
            if len(enabled_channels) > 3:
                channel_text = f"{', '.join(channel_mentions)} +{len(enabled_channels) - 3} more"
            else:
                channel_text = ', '.join(channel_mentions) if channel_mentions else "None"
        else:
            channel_text = "All channels"
        
        embed.add_field(name="Active Channels", value=channel_text, inline=True)
        
        # Log channel
        log_channel_id = guild_settings.get('log_channel')
        if log_channel_id:
            log_channel = ctx.guild.get_channel(log_channel_id)
            log_text = log_channel.mention if log_channel else "Invalid channel"
        else:
            log_text = "Not set"
        
        embed.add_field(name="Log Channel", value=log_text, inline=True)
        
        # Prefixes
        prefixes = guild_settings.get('prefix', ['!', '?', '/'])
        embed.add_field(
            name="Command Prefixes", 
            value=", ".join(f"`{p}`" for p in prefixes), 
            inline=True
        )
        
        # Moderation settings
        max_warns = guild_settings.get('max_warns', 3)
        auto_ban = "🟢 Enabled" if guild_settings.get('auto_ban_enabled', False) else "🔴 Disabled"
        
        embed.add_field(name="Max Warnings", value=str(max_warns), inline=True)
        embed.add_field(name="Auto-ban", value=auto_ban, inline=True)
        
        # Additional features
        features = []
        if guild_settings.get('anti_spam_enabled', False):
            features.append("🟢 Anti-Spam")
        if guild_settings.get('anti_raid_enabled', False):
            features.append("🟢 Anti-Raid")
        if guild_settings.get('anti_link_enabled', False):
            features.append("🟢 Anti-Link")
        
        if features:
            embed.add_field(name="Additional Features", value="\n".join(features), inline=False)
        
        embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="chatwarden_info", description="Show bot information and statistics")
    async def chatwarden_info(self, ctx):
        """Show bot information and statistics"""
        embed = create_embed("🤖 Bot Information", color=discord.Color.blue())
        
        # Basic stats
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds):,}", inline=True)
        embed.add_field(name="Users", value=f"{len(self.bot.users):,}", inline=True)
        embed.add_field(name="Channels", value=f"{len(list(self.bot.get_all_channels())):,}", inline=True)
        
        # Filter stats
        word_counts = self.bot.profanity_filter.get_word_count()
        total_words = sum(word_counts.values())
        embed.add_field(name="Filtered Words", value=f"{total_words:,}", inline=True)
        
        # Webhook stats
        webhook_count = len(self.bot.webhook_manager.webhooks)
        embed.add_field(name="Active Webhooks", value=f"{webhook_count:,}", inline=True)
        
        # Database stats
        try:
            db_stats = await self.bot.db.get_stats()
            total_logs = db_stats.get('total_mod_logs', 0)
            embed.add_field(name="Mod Actions Logged", value=f"{total_logs:,}", inline=True)
        except:
            pass
        
        # Bot uptime (approximate)
        embed.add_field(
            name="Latency", 
            value=f"{round(self.bot.latency * 1000)}ms", 
            inline=True
        )
        
        # Features
        features = [
            "🔍 Advanced Profanity Detection",
            "🔄 Webhook Message Replacement", 
            "⚖️ Complete Moderation Suite",
            "📊 Comprehensive Logging",
            "🛡️ Anti-Spam & Anti-Raid",
            "🎯 Smart Bypass Detection"
        ]
        
        embed.add_field(name="Features", value="\n".join(features), inline=False)
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Bot ID: {self.bot.user.id} | Made with discord.py")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
