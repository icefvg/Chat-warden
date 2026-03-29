"""
Standalone moderation commands module for Discord bot
This file provides an alternative implementation of moderation commands
that can be used independently or as a reference.
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import re
from typing import Optional, Union

class ModerationCommands:
    """Standalone moderation commands class"""
    
    def __init__(self, bot):
        self.bot = bot
        self.setup_commands()
    
    def setup_commands(self):
        """Register all moderation commands"""
        
        @self.bot.command(name='kick_user')
        @commands.has_permissions(kick_members=True)
        async def kick_user(ctx, user: discord.Member, *, reason="No reason provided"):
            """Kick a user from the server"""
            if user.id == ctx.author.id:
                await ctx.send("❌ You cannot kick yourself.")
                return
                
            if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ You cannot kick someone with a role equal or higher than yours.")
                return
            
            if user == ctx.guild.owner:
                await ctx.send("❌ Cannot kick the server owner.")
                return
            
            try:
                # Send DM before kicking
                try:
                    embed = discord.Embed(
                        title=f"You have been kicked from {ctx.guild.name}",
                        description=f"**Reason:** {reason}\n**Moderator:** {ctx.author}",
                        color=discord.Color.orange()
                    )
                    embed.set_footer(text="You can rejoin this server with a new invite.")
                    await user.send(embed=embed)
                except:
                    pass  # User has DMs disabled
                
                await user.kick(reason=f"{reason} | Moderator: {ctx.author}")
                
                embed = discord.Embed(
                    title="✅ User Kicked",
                    description=f"**{user}** has been kicked.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.set_thumbnail(url=user.display_avatar.url)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to kick this user.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
        
        @self.bot.command(name='ban_user')
        @commands.has_permissions(ban_members=True)
        async def ban_user(ctx, user: discord.Member, delete_days: int = 0, *, reason="No reason provided"):
            """Ban a user from the server"""
            if delete_days < 0 or delete_days > 7:
                await ctx.send("❌ Delete days must be between 0 and 7.")
                return
            
            if user.id == ctx.author.id:
                await ctx.send("❌ You cannot ban yourself.")
                return
                
            if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ You cannot ban someone with a role equal or higher than yours.")
                return
            
            if user == ctx.guild.owner:
                await ctx.send("❌ Cannot ban the server owner.")
                return
            
            try:
                # Send DM before banning
                try:
                    embed = discord.Embed(
                        title=f"You have been banned from {ctx.guild.name}",
                        description=f"**Reason:** {reason}\n**Moderator:** {ctx.author}",
                        color=discord.Color.red()
                    )
                    embed.set_footer(text="This ban may be appealed by contacting the server moderators.")
                    await user.send(embed=embed)
                except:
                    pass
                
                await user.ban(reason=f"{reason} | Moderator: {ctx.author}", delete_message_days=delete_days)
                
                embed = discord.Embed(
                    title="🔨 User Banned",
                    description=f"**{user}** has been banned.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                if delete_days > 0:
                    embed.add_field(name="Messages Deleted", value=f"{delete_days} day(s)", inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to ban this user.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
        
        @self.bot.command(name='unban_user')
        @commands.has_permissions(ban_members=True)
        async def unban_user(ctx, user_id: int, *, reason="No reason provided"):
            """Unban a user by ID"""
            try:
                # Check if user is actually banned
                ban_entry = None
                async for ban in ctx.guild.bans():
                    if ban.user.id == user_id:
                        ban_entry = ban
                        break
                
                if not ban_entry:
                    await ctx.send("❌ User is not banned or user ID not found.")
                    return
                
                user = ban_entry.user
                await ctx.guild.unban(user, reason=f"{reason} | Moderator: {ctx.author}")
                
                embed = discord.Embed(
                    title="✅ User Unbanned",
                    description=f"**{user}** has been unbanned.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Original Ban Reason", value=ban_entry.reason or "No reason", inline=False)
                embed.set_thumbnail(url=user.display_avatar.url)
                await ctx.send(embed=embed)
                
            except discord.NotFound:
                await ctx.send("❌ User not found or not banned.")
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to unban users.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
        
        @self.bot.command(name='mute_user')
        @commands.has_permissions(moderate_members=True)
        async def mute_user(ctx, user: discord.Member, duration="10m", *, reason="No reason provided"):
            """Mute a user using Discord's timeout feature"""
            if user.id == ctx.author.id:
                await ctx.send("❌ You cannot mute yourself.")
                return
                
            if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ You cannot mute someone with a role equal or higher than yours.")
                return
            
            # Parse duration
            duration_delta = self.parse_duration(duration)
            if not duration_delta:
                await ctx.send("❌ Invalid duration format. Use formats like: 10m, 1h, 2d")
                return
            
            if duration_delta > timedelta(days=28):
                await ctx.send("❌ Mute duration cannot exceed 28 days due to Discord limitations.")
                return
            
            if duration_delta < timedelta(seconds=60):
                await ctx.send("❌ Mute duration must be at least 1 minute.")
                return
            
            try:
                until = discord.utils.utcnow() + duration_delta
                await user.timeout(until, reason=f"{reason} | Moderator: {ctx.author}")
                
                duration_str = self.format_duration(duration_delta)
                
                embed = discord.Embed(
                    title="🔇 User Muted",
                    description=f"**{user}** has been muted for {duration_str}.",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Expires", value=f"<t:{int(until.timestamp())}:R>", inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to mute this user.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
        
        @self.bot.command(name='unmute_user')
        @commands.has_permissions(moderate_members=True)
        async def unmute_user(ctx, user: discord.Member, *, reason="No reason provided"):
            """Unmute a user"""
            if not user.is_timed_out():
                await ctx.send(f"❌ **{user}** is not currently muted.")
                return
                
            try:
                await user.timeout(None, reason=f"{reason} | Moderator: {ctx.author}")
                
                embed = discord.Embed(
                    title="🔊 User Unmuted",
                    description=f"**{user}** has been unmuted.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.set_thumbnail(url=user.display_avatar.url)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to unmute this user.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
        
        @self.bot.command(name='clear_messages')
        @commands.has_permissions(manage_messages=True)
        async def clear_messages(ctx, amount: int):
            """Delete messages in bulk"""
            if amount < 1 or amount > 100:
                await ctx.send("❌ Amount must be between 1 and 100.")
                return
            
            try:
                deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for command message
                deleted_count = len(deleted) - 1
                
                embed = discord.Embed(
                    title="🗑️ Messages Cleared",
                    description=f"Deleted **{deleted_count}** message(s).",
                    color=discord.Color.green()
                )
                embed.set_footer(text="This message will be deleted in 5 seconds")
                
                msg = await ctx.send(embed=embed)
                
                # Delete confirmation message after 5 seconds
                await asyncio.sleep(5)
                try:
                    await msg.delete()
                except:
                    pass
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to delete messages in this channel.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
        
        @self.bot.command(name='purge_user')
        @commands.has_permissions(manage_messages=True)
        async def purge_user(ctx, user: discord.Member, amount: int = 50):
            """Delete messages from a specific user"""
            if amount < 1 or amount > 100:
                await ctx.send("❌ Amount must be between 1 and 100.")
                return
            
            try:
                def check(message):
                    return message.author == user
                
                deleted = await ctx.channel.purge(limit=amount, check=check)
                deleted_count = len(deleted)
                
                embed = discord.Embed(
                    title="🗑️ User Messages Purged",
                    description=f"Deleted **{deleted_count}** message(s) from **{user.display_name}**.",
                    color=discord.Color.green()
                )
                embed.set_footer(text="This message will be deleted in 5 seconds")
                
                msg = await ctx.send(embed=embed)
                
                # Delete confirmation message after 5 seconds
                await asyncio.sleep(5)
                try:
                    await msg.delete()
                except:
                    pass
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to delete messages in this channel.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
        
        @self.bot.command(name='slowmode')
        @commands.has_permissions(manage_channels=True)
        async def slowmode(ctx, seconds: int):
            """Set slowmode for the current channel"""
            if seconds < 0 or seconds > 21600:  # 6 hours max
                await ctx.send("❌ Slowmode must be between 0 and 21600 seconds (6 hours).")
                return
            
            try:
                await ctx.channel.edit(slowmode_delay=seconds)
                
                if seconds == 0:
                    embed = discord.Embed(
                        title="⏱️ Slowmode Disabled",
                        description="Slowmode has been **disabled**.",
                        color=discord.Color.green()
                    )
                else:
                    duration_str = self.format_duration(timedelta(seconds=seconds))
                    embed = discord.Embed(
                        title="⏱️ Slowmode Enabled",
                        description=f"Slowmode set to **{duration_str}**.",
                        color=discord.Color.blue()
                    )
                
                embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to edit this channel.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")
    
    def parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parse duration string into timedelta"""
        if not duration_str:
            return None
        
        # Regex to match time patterns like "1h30m", "5d", "2w3d"
        pattern = r'(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
        match = re.match(pattern, duration_str.lower().strip())
        
        if not match:
            # Try simple number (assume minutes)
            try:
                minutes = int(duration_str)
                return timedelta(minutes=minutes)
            except ValueError:
                return None
        
        weeks, days, hours, minutes, seconds = match.groups()
        
        total_seconds = 0
        if weeks:
            total_seconds += int(weeks) * 604800  # 7 * 24 * 60 * 60
        if days:
            total_seconds += int(days) * 86400    # 24 * 60 * 60
        if hours:
            total_seconds += int(hours) * 3600    # 60 * 60
        if minutes:
            total_seconds += int(minutes) * 60
        if seconds:
            total_seconds += int(seconds)
        
        return timedelta(seconds=total_seconds) if total_seconds > 0 else None
    
    def format_duration(self, delta: timedelta) -> str:
        """Format timedelta into readable string"""
        if isinstance(delta, str):
            return delta
            
        total_seconds = int(delta.total_seconds())
        
        if total_seconds <= 0:
            return "0 seconds"
        
        units = [
            ('week', 604800),
            ('day', 86400),
            ('hour', 3600),
            ('minute', 60),
            ('second', 1)
        ]
        
        parts = []
        for unit_name, unit_seconds in units:
            if total_seconds >= unit_seconds:
                unit_count = total_seconds // unit_seconds
                total_seconds %= unit_seconds
                unit_str = f"{unit_count} {unit_name}"
                if unit_count != 1:
                    unit_str += "s"
                parts.append(unit_str)
        
        if len(parts) == 0:
            return "0 seconds"
        elif len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        else:
            return f"{', '.join(parts[:-1])}, and {parts[-1]}"

# Usage example:
# To use this standalone moderation commands module:
# 
# from moderation_commands import ModerationCommands
# 
# # In your bot setup:
# moderation = ModerationCommands(bot)
#
# This provides alternative command implementations that can be used
# alongside or instead of the cog-based approach in cogs/moderation.py
