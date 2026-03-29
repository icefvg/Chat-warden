import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import (
    has_permissions, create_embed, create_error_embed, create_success_embed,
    parse_duration, format_duration, get_member_or_user, confirm_action, 
    Paginator, log_moderation_action, extract_user_id
)
from datetime import datetime, timedelta
import asyncio
import re

class ModerationCommands(commands.Cog):
    """Moderation commands for server management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # Basic Moderation Commands
    
    @commands.hybrid_command(name="kick", description="Kick a user from the server")
    @app_commands.describe(user="User to kick", reason="Reason for kick")
    @has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """Kick a user from the server"""
        if user.id == ctx.author.id:
            embed = create_error_embed("You cannot kick yourself.")
            await ctx.send(embed=embed)
            return
            
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = create_error_embed("You cannot kick someone with a role equal or higher than yours.")
            await ctx.send(embed=embed)
            return
        
        if user == ctx.guild.owner:
            embed = create_error_embed("Cannot kick the server owner.")
            await ctx.send(embed=embed)
            return
        
        if user.top_role >= ctx.guild.me.top_role:
            embed = create_error_embed("I cannot kick someone with a role equal or higher than mine.")
            await ctx.send(embed=embed)
            return
        
        try:
            # Send DM before kicking
            try:
                dm_embed = create_embed(
                    f"You have been kicked from {ctx.guild.name}",
                    f"**Reason:** {reason}\n**Moderator:** {ctx.author}",
                    discord.Color.orange()
                )
                dm_embed.set_footer(text="You can rejoin this server with a new invite.")
                await user.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            await user.kick(reason=f"{reason} | Moderator: {ctx.author}")
            
            # Log the action
            await self.bot.db.add_mod_log(ctx.guild.id, "kick", user.id, ctx.author.id, reason)
            await log_moderation_action(self.bot, ctx.guild, "kick", user, ctx.author, reason)
            
            embed = create_success_embed(f"**{user}** has been kicked.")
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to kick this user.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="User to ban", 
        reason="Reason for ban", 
        delete_days="Days of messages to delete (0-7)"
    )
    @has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.Member, delete_days: int = 0, *, reason: str = "No reason provided"):
        """Ban a user from the server"""
        if delete_days < 0 or delete_days > 7:
            embed = create_error_embed("Delete days must be between 0 and 7.")
            await ctx.send(embed=embed)
            return
        
        if user.id == ctx.author.id:
            embed = create_error_embed("You cannot ban yourself.")
            await ctx.send(embed=embed)
            return
            
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = create_error_embed("You cannot ban someone with a role equal or higher than yours.")
            await ctx.send(embed=embed)
            return
        
        if user == ctx.guild.owner:
            embed = create_error_embed("Cannot ban the server owner.")
            await ctx.send(embed=embed)
            return
        
        if user.top_role >= ctx.guild.me.top_role:
            embed = create_error_embed("I cannot ban someone with a role equal or higher than mine.")
            await ctx.send(embed=embed)
            return
        
        try:
            # Send DM before banning
            try:
                dm_embed = create_embed(
                    f"You have been banned from {ctx.guild.name}",
                    f"**Reason:** {reason}\n**Moderator:** {ctx.author}",
                    discord.Color.red()
                )
                dm_embed.set_footer(text="This ban may be appealed by contacting the server moderators.")
                await user.send(embed=dm_embed)
            except:
                pass
            
            await user.ban(reason=f"{reason} | Moderator: {ctx.author}", delete_message_days=delete_days)
            
            # Log the action
            await self.bot.db.add_mod_log(ctx.guild.id, "ban", user.id, ctx.author.id, reason)
            await log_moderation_action(self.bot, ctx.guild, "ban", user, ctx.author, reason)
            
            embed = create_success_embed(f"**{user}** has been banned.")
            embed.add_field(name="Reason", value=reason, inline=False)
            if delete_days > 0:
                embed.add_field(name="Messages Deleted", value=f"{delete_days} day(s)", inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to ban this user.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="ID of user to unban", reason="Reason for unban")
    @has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str, *, reason: str = "No reason provided"):
        """Unban a user by ID"""
        try:
            user_id_int = extract_user_id(user_id)
            if not user_id_int:
                embed = create_error_embed("Invalid user ID format.")
                await ctx.send(embed=embed)
                return
        except ValueError:
            embed = create_error_embed("Invalid user ID format.")
            await ctx.send(embed=embed)
            return
        
        try:
            # Check if user is actually banned
            ban_entry = None
            async for ban in ctx.guild.bans():
                if ban.user.id == user_id_int:
                    ban_entry = ban
                    break
            
            if not ban_entry:
                embed = create_error_embed("User is not banned or user ID not found.")
                await ctx.send(embed=embed)
                return
            
            user = ban_entry.user
            await ctx.guild.unban(user, reason=f"{reason} | Moderator: {ctx.author}")
            
            # Log the action
            await self.bot.db.add_mod_log(ctx.guild.id, "unban", user.id, ctx.author.id, reason)
            await log_moderation_action(self.bot, ctx.guild, "unban", user, ctx.author, reason)
            
            embed = create_success_embed(f"**{user}** has been unbanned.")
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Original Ban Reason", value=ban_entry.reason or "No reason", inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            
        except discord.NotFound:
            embed = create_error_embed("User not found or not banned.")
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to unban users.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="mute", description="Mute a user (timeout)")
    @app_commands.describe(
        user="User to mute", 
        duration="Duration (e.g., 10m, 1h, 1d)", 
        reason="Reason for mute"
    )
    @has_permissions(moderate_members=True)
    async def mute(self, ctx, user: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
        """Mute a user using Discord's timeout feature"""
        if user.id == ctx.author.id:
            embed = create_error_embed("You cannot mute yourself.")
            await ctx.send(embed=embed)
            return
            
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = create_error_embed("You cannot mute someone with a role equal or higher than yours.")
            await ctx.send(embed=embed)
            return
        
        if user.top_role >= ctx.guild.me.top_role:
            embed = create_error_embed("I cannot mute someone with a role equal or higher than mine.")
            await ctx.send(embed=embed)
            return
        
        # Parse duration
        duration_delta = parse_duration(duration)
        if not duration_delta:
            embed = create_error_embed("Invalid duration format. Use formats like: 10m, 1h, 2d")
            embed.add_field(
                name="Valid Formats",
                value="• `10m` - 10 minutes\n• `1h30m` - 1 hour 30 minutes\n• `2d` - 2 days\n• `1w` - 1 week",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        if duration_delta > timedelta(days=28):
            embed = create_error_embed("Mute duration cannot exceed 28 days due to Discord limitations.")
            await ctx.send(embed=embed)
            return
        
        if duration_delta < timedelta(seconds=60):
            embed = create_error_embed("Mute duration must be at least 1 minute.")
            await ctx.send(embed=embed)
            return
        
        try:
            until = discord.utils.utcnow() + duration_delta
            await user.timeout(until, reason=f"{reason} | Moderator: {ctx.author}")
            
            # Log the action
            duration_str = format_duration(duration_delta)
            await self.bot.db.add_mod_log(ctx.guild.id, "mute", user.id, ctx.author.id, reason, duration_str)
            await log_moderation_action(self.bot, ctx.guild, "mute", user, ctx.author, reason, duration_str)
            
            embed = create_success_embed(f"**{user}** has been muted for {duration_str}.")
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Expires", value=f"<t:{int(until.timestamp())}:R>", inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to mute this user.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unmute", description="Unmute a user")
    @app_commands.describe(user="User to unmute", reason="Reason for unmute")
    @has_permissions(moderate_members=True)
    async def unmute(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """Unmute a user"""
        if not user.is_timed_out():
            embed = create_error_embed(f"**{user}** is not currently muted.")
            await ctx.send(embed=embed)
            return
            
        try:
            await user.timeout(None, reason=f"{reason} | Moderator: {ctx.author}")
            
            # Log the action
            await self.bot.db.add_mod_log(ctx.guild.id, "unmute", user.id, ctx.author.id, reason)
            await log_moderation_action(self.bot, ctx.guild, "unmute", user, ctx.author, reason)
            
            embed = create_success_embed(f"**{user}** has been unmuted.")
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to unmute this user.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="warn", description="Warn a user")
    @app_commands.describe(user="User to warn", reason="Reason for warning")
    @has_permissions(manage_messages=True)
    async def warn(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """Warn a user"""
        if user.id == ctx.author.id:
            embed = create_error_embed("You cannot warn yourself.")
            await ctx.send(embed=embed)
            return
            
        if user.bot:
            embed = create_error_embed("You cannot warn bots.")
            await ctx.send(embed=embed)
            return
            
        try:
            # Add warning to database
            warning_id = await self.bot.db.add_warning(ctx.guild.id, user.id, ctx.author.id, reason)
            
            # Send DM to user
            try:
                dm_embed = create_embed(
                    f"You have been warned in {ctx.guild.name}",
                    f"**Warning #{warning_id}**\n**Reason:** {reason}\n**Moderator:** {ctx.author}",
                    discord.Color.orange()
                )
                dm_embed.set_footer(text="Please review the server rules to avoid future warnings.")
                await user.send(embed=dm_embed)
                dm_sent = True
            except:
                dm_sent = False
            
            # Get total warnings
            warnings = await self.bot.db.get_warnings(ctx.guild.id, user.id)
            warning_count = len(warnings)
            
            # Log the action
            await self.bot.db.add_mod_log(ctx.guild.id, "warn", user.id, ctx.author.id, reason)
            await log_moderation_action(self.bot, ctx.guild, "warn", user, ctx.author, reason)
            
            embed = create_success_embed(f"**{user}** has been warned.")
            embed.add_field(name=f"Warning #{warning_id}", value=reason, inline=False)
            embed.add_field(name="Total Warnings", value=f"{warning_count}", inline=True)
            
            if not dm_sent:
                embed.add_field(name="⚠️ Note", value="Could not send DM to user", inline=True)
            
            embed.set_thumbnail(url=user.display_avatar.url)
            
            # Check for auto-actions based on warning count
            guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
            max_warns = guild_settings.get('max_warns', 3)
            
            if warning_count >= max_warns:
                if guild_settings.get('auto_ban_enabled', False):
                    try:
                        await user.ban(reason=f"Automatic ban: {max_warns} warnings reached")
                        embed.add_field(
                            name="🔨 Auto-Ban Triggered",
                            value=f"User was automatically banned for reaching {max_warns} warnings.",
                            inline=False
                        )
                        embed.color = discord.Color.red()
                    except:
                        embed.add_field(
                            name="⚠️ Auto-Ban Failed",
                            value="Could not automatically ban user. Please review manually.",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="⚠️ Warning Threshold Reached",
                        value=f"User has reached {max_warns} warnings. Consider manual action.",
                        inline=False
                    )
                    embed.color = discord.Color.red()
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="warnings", description="Show warnings for a user")
    @app_commands.describe(user="User to check warnings for")
    async def warnings(self, ctx, user: discord.Member = None):
        """Show warnings for a user"""
        if user is None:
            user = ctx.author
        
        warnings = await self.bot.db.get_warnings(ctx.guild.id, user.id)
        
        if not warnings:
            embed = create_embed(
                f"📋 Warnings for {user.display_name}", 
                "No warnings found.", 
                discord.Color.green()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            return
        
        def format_warning(warning, index):
            timestamp = datetime.fromisoformat(warning['timestamp'])
            date = timestamp.strftime('%Y-%m-%d %H:%M UTC')
            moderator = ctx.guild.get_member(warning['moderator_id'])
            mod_name = moderator.display_name if moderator else "Unknown Moderator"
            
            return (
                f"**#{warning['id']}** - {date}\n"
                f"**Reason:** {warning['reason']}\n"
                f"**Moderator:** {mod_name}\n"
                f"────────────────"
            )
        
        paginator = Paginator(ctx, warnings, 5)
        await paginator.paginate(f"📋 Warnings for {user.display_name}", format_warning)
    
    @commands.hybrid_command(name="clearwarnings", description="Clear all warnings for a user")
    @app_commands.describe(user="User to clear warnings for")
    @has_permissions(manage_messages=True)
    async def clearwarnings(self, ctx, user: discord.Member):
        """Clear all warnings for a user"""
        count = await self.bot.db.clear_warnings(ctx.guild.id, user.id)
        
        if count == 0:
            embed = create_embed(
                "📋 No Warnings", 
                f"**{user.display_name}** has no warnings to clear."
            )
        else:
            embed = create_success_embed(f"Cleared **{count}** warning(s) for **{user.display_name}**.")
            
            # Log the action
            await self.bot.db.add_mod_log(
                ctx.guild.id, 
                "clear_warnings", 
                user.id, 
                ctx.author.id, 
                f"Cleared {count} warnings"
            )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)
    
    # Message Management Commands
    
    @commands.hybrid_command(name="clear", description="Delete messages in bulk")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """Delete messages in bulk"""
        if amount < 1 or amount > 100:
            embed = create_error_embed("Amount must be between 1 and 100.")
            await ctx.send(embed=embed)
            return
        
        try:
            # Delete the command message if it's a text command
            if ctx.interaction is None:
                deleted = await ctx.channel.purge(limit=amount + 1)
                deleted_count = len(deleted) - 1
            else:
                deleted = await ctx.channel.purge(limit=amount)
                deleted_count = len(deleted)
            
            embed = create_success_embed(f"Deleted **{deleted_count}** message(s).")
            embed.set_footer(text="This message will be deleted in 5 seconds")
            
            msg = await ctx.send(embed=embed, ephemeral=True)
            
            # Delete confirmation message after 5 seconds (if not ephemeral)
            if not ctx.interaction:
                await asyncio.sleep(5)
                try:
                    await msg.delete()
                except:
                    pass
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to delete messages in this channel.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="purge", description="Delete messages from a specific user")
    @app_commands.describe(user="User whose messages to delete", amount="Number of messages to check (1-100)")
    @has_permissions(manage_messages=True)
    async def purge(self, ctx, user: discord.Member, amount: int = 50):
        """Delete messages from a specific user"""
        if amount < 1 or amount > 100:
            embed = create_error_embed("Amount must be between 1 and 100.")
            await ctx.send(embed=embed)
            return
        
        try:
            def check(message):
                return message.author == user
            
            deleted = await ctx.channel.purge(limit=amount, check=check)
            deleted_count = len(deleted)
            
            embed = create_success_embed(f"Deleted **{deleted_count}** message(s) from **{user.display_name}**.")
            embed.set_footer(text="This message will be deleted in 5 seconds")
            
            msg = await ctx.send(embed=embed, ephemeral=True)
            
            # Delete confirmation message after 5 seconds (if not ephemeral)
            if not ctx.interaction:
                await asyncio.sleep(5)
                try:
                    await msg.delete()
                except:
                    pass
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to delete messages in this channel.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    # Channel Management Commands
    
    @commands.hybrid_command(name="slowmode", description="Set slowmode for the current channel")
    @app_commands.describe(seconds="Slowmode delay in seconds (0-21600)")
    @has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        """Set slowmode for the current channel"""
        if seconds < 0 or seconds > 21600:  # 6 hours max
            embed = create_error_embed("Slowmode must be between 0 and 21600 seconds (6 hours).")
            await ctx.send(embed=embed)
            return
        
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                embed = create_success_embed("Slowmode has been **disabled**.")
            else:
                duration_str = format_duration(timedelta(seconds=seconds))
                embed = create_success_embed(f"Slowmode set to **{duration_str}**.")
            
            embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to edit this channel.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="lock", description="Lock the current channel")
    @has_permissions(manage_channels=True)
    async def lock(self, ctx):
        """Lock the current channel"""
        try:
            overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
            
            if overwrite.send_messages is False:
                embed = create_error_embed("This channel is already locked.")
                await ctx.send(embed=embed)
                return
            
            overwrite.send_messages = False
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            
            embed = create_success_embed(f"🔒 **{ctx.channel.name}** has been locked.")
            embed.add_field(name="Locked by", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to edit this channel.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unlock", description="Unlock the current channel")
    @has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Unlock the current channel"""
        try:
            overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
            
            if overwrite.send_messages is not False:
                embed = create_error_embed("This channel is not currently locked.")
                await ctx.send(embed=embed)
                return
            
            overwrite.send_messages = None  # Reset to default
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            
            embed = create_success_embed(f"🔓 **{ctx.channel.name}** has been unlocked.")
            embed.add_field(name="Unlocked by", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to edit this channel.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="nuke", description="Delete and recreate the current channel")
    @has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        """Delete and recreate the current channel"""
        confirm = await confirm_action(
            ctx, 
            f"Are you sure you want to nuke **{ctx.channel.name}**?\n\n"
            "⚠️ **This will:**\n"
            "• Delete the channel and recreate it\n"
            "• Remove **ALL** messages permanently\n" 
            "• Reset all channel permissions\n"
            "• This action **CANNOT** be undone!"
        )
        
        if not confirm:
            return
        
        try:
            # Store channel properties
            channel = ctx.channel
            position = channel.position
            category = channel.category
            overwrites = channel.overwrites
            topic = channel.topic
            nsfw = channel.nsfw
            slowmode_delay = channel.slowmode_delay
            
            # Create new channel
            new_channel = await ctx.guild.create_text_channel(
                name=channel.name,
                category=category,
                overwrites=overwrites,
                topic=topic,
                nsfw=nsfw,
                slowmode_delay=slowmode_delay,
                position=position,
                reason=f"Channel nuked by {ctx.author}"
            )
            
            # Delete old channel
            await channel.delete(reason=f"Channel nuked by {ctx.author}")
            
            embed = create_success_embed(f"💥 **{new_channel.name}** has been nuked and recreated!")
            embed.add_field(name="Nuked by", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value="Channel cleanup", inline=True)
            embed.set_footer(text="All previous messages have been permanently deleted")
            
            await new_channel.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to manage channels.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ModerationCommands(bot))
