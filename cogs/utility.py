import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import (
    has_permissions, create_embed, create_error_embed, create_success_embed,
    Paginator, format_timestamp
)
from datetime import datetime
import asyncio

class UtilityCommands(commands.Cog):
    """Utility commands for server management and fun features"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="say", description="Make the bot say something")
    @app_commands.describe(message="Message for the bot to say")
    @has_permissions(manage_messages=True)
    async def say(self, ctx, *, message: str):
        """Make the bot say something"""
        # Delete the command message if it's a text command
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except:
                pass
        
        # Send the message
        await ctx.send(message)
    
    @commands.hybrid_command(name="embed", description="Send a styled embed message")
    @app_commands.describe(
        title="Embed title",
        description="Embed description",
        color="Embed color (hex code like #ff0000)"
    )
    @has_permissions(manage_messages=True)
    async def embed(self, ctx, title: str, description: str = None, color: str = None):
        """Send a styled embed message"""
        # Parse color
        embed_color = discord.Color.blue()
        if color:
            try:
                if color.startswith('#'):
                    embed_color = discord.Color(int(color[1:], 16))
                elif color.lower() in ['red', 'green', 'blue', 'yellow', 'orange', 'purple']:
                    color_map = {
                        'red': discord.Color.red(),
                        'green': discord.Color.green(),
                        'blue': discord.Color.blue(),
                        'yellow': discord.Color.yellow(),
                        'orange': discord.Color.orange(),
                        'purple': discord.Color.purple()
                    }
                    embed_color = color_map[color.lower()]
            except:
                pass  # Use default color if parsing fails
        
        embed = discord.Embed(title=title, description=description, color=embed_color)
        embed.set_footer(text=f"Sent by {ctx.author.display_name}")
        embed.timestamp = datetime.utcnow()
        
        # Delete the command message if it's a text command
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except:
                pass
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="announce", description="Send an announcement to a channel")
    @app_commands.describe(
        channel="Channel to send announcement to",
        message="Announcement message"
    )
    @has_permissions(manage_messages=True)
    async def announce(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send an announcement to a channel"""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            embed = create_error_embed(f"I don't have permission to send messages in {channel.mention}.")
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=discord.Color.gold()
        )
        embed.set_author(
            name=f"Announcement by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        embed.timestamp = datetime.utcnow()
        
        try:
            await channel.send(embed=embed)
            
            confirmation = create_success_embed(f"Announcement sent to {channel.mention}!")
            await ctx.send(embed=confirmation, ephemeral=True)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to send messages in that channel.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="poll", description="Create a reaction-based poll")
    @app_commands.describe(
        question="Poll question",
        options="Poll options separated by commas (max 10)"
    )
    async def poll(self, ctx, question: str, *, options: str):
        """Create a reaction-based poll"""
        option_list = [opt.strip() for opt in options.split(',')]
        
        if len(option_list) < 2:
            embed = create_error_embed("A poll needs at least 2 options.")
            await ctx.send(embed=embed)
            return
        
        if len(option_list) > 10:
            embed = create_error_embed("A poll can have at most 10 options.")
            await ctx.send(embed=embed)
            return
        
        # Emoji numbers for options
        number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        embed = discord.Embed(
            title="📊 Poll",
            description=f"**{question}**",
            color=discord.Color.blue()
        )
        
        option_text = []
        for i, option in enumerate(option_list):
            option_text.append(f"{number_emojis[i]} {option}")
        
        embed.add_field(name="Options", value="\n".join(option_text), inline=False)
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
        embed.timestamp = datetime.utcnow()
        
        # Delete the command message if it's a text command
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except:
                pass
        
        poll_message = await ctx.send(embed=embed)
        
        # Add reactions
        for i in range(len(option_list)):
            await poll_message.add_reaction(number_emojis[i])
    
    @commands.hybrid_command(name="dm", description="Send a private message to a user")
    @app_commands.describe(user="User to send message to", message="Message to send")
    @has_permissions(manage_messages=True)
    async def dm(self, ctx, user: discord.Member, *, message: str):
        """Send a private message to a user via the bot"""
        try:
            embed = discord.Embed(
                title=f"Message from {ctx.guild.name}",
                description=message,
                color=discord.Color.blue()
            )
            embed.set_author(
                name=f"Sent by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            embed.set_footer(text=f"From server: {ctx.guild.name}")
            embed.timestamp = datetime.utcnow()
            
            await user.send(embed=embed)
            
            confirmation = create_success_embed(f"Message sent to **{user}**!")
            await ctx.send(embed=confirmation, ephemeral=True)
            
        except discord.Forbidden:
            embed = create_error_embed(f"**{user}** has DMs disabled or has blocked me.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="userinfo", description="Get information about a user")
    @app_commands.describe(user="User to get information about")
    async def userinfo(self, ctx, user: discord.Member = None):
        """Get detailed information about a user"""
        if user is None:
            user = ctx.author
        
        embed = discord.Embed(color=user.color or discord.Color.blue())
        embed.set_author(name=f"{user.display_name}", icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Basic info
        embed.add_field(name="Username", value=str(user), inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Bot", value="Yes" if user.bot else "No", inline=True)
        
        # Dates
        created_at = format_timestamp(user.created_at)
        joined_at = format_timestamp(user.joined_at) if user.joined_at else "Unknown"
        
        embed.add_field(name="Account Created", value=created_at, inline=True)
        embed.add_field(name="Joined Server", value=joined_at, inline=True)
        
        # Status
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡",
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫"
        }
        embed.add_field(
            name="Status", 
            value=f"{status_emoji.get(user.status, '⚫')} {user.status.name.title()}", 
            inline=True
        )
        
        # Roles
        if len(user.roles) > 1:  # Exclude @everyone
            roles = [role.mention for role in user.roles[1:]]  # Skip @everyone
            if len(roles) > 10:
                roles_text = ", ".join(roles[:10]) + f" (+{len(roles) - 10} more)"
            else:
                roles_text = ", ".join(roles)
            embed.add_field(name=f"Roles [{len(user.roles) - 1}]", value=roles_text, inline=False)
        
        # Permissions
        if user.guild_permissions.administrator:
            embed.add_field(name="Key Permissions", value="Administrator", inline=True)
        else:
            key_perms = []
            perm_checks = {
                'manage_guild': 'Manage Server',
                'manage_roles': 'Manage Roles', 
                'manage_channels': 'Manage Channels',
                'kick_members': 'Kick Members',
                'ban_members': 'Ban Members',
                'manage_messages': 'Manage Messages',
                'moderate_members': 'Timeout Members'
            }
            
            for perm, name in perm_checks.items():
                if getattr(user.guild_permissions, perm):
                    key_perms.append(name)
            
            if key_perms:
                embed.add_field(name="Key Permissions", value=", ".join(key_perms), inline=False)
        
        # Activity
        if user.activity:
            activity_type = {
                discord.ActivityType.playing: "Playing",
                discord.ActivityType.streaming: "Streaming",
                discord.ActivityType.listening: "Listening to",
                discord.ActivityType.watching: "Watching",
                discord.ActivityType.competing: "Competing in"
            }
            activity_name = activity_type.get(user.activity.type, "Custom Status")
            embed.add_field(name="Activity", value=f"{activity_name} {user.activity.name}", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, ctx):
        """Get detailed information about the server"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blue()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Created", value=format_timestamp(guild.created_at), inline=True)
        
        # Member stats
        member_count = guild.member_count
        bot_count = sum(1 for member in guild.members if member.bot)
        human_count = member_count - bot_count
        
        embed.add_field(name="Members", value=f"{human_count:,}", inline=True)
        embed.add_field(name="Bots", value=f"{bot_count:,}", inline=True)
        embed.add_field(name="Total", value=f"{member_count:,}", inline=True)
        
        # Channel stats
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(name="Text Channels", value=f"{text_channels:,}", inline=True)
        embed.add_field(name="Voice Channels", value=f"{voice_channels:,}", inline=True)
        embed.add_field(name="Categories", value=f"{categories:,}", inline=True)
        
        # Other stats
        embed.add_field(name="Roles", value=f"{len(guild.roles):,}", inline=True)
        embed.add_field(name="Emojis", value=f"{len(guild.emojis):,}", inline=True)
        embed.add_field(name="Boosts", value=f"{guild.premium_subscription_count:,}", inline=True)
        
        # Features
        features = []
        feature_names = {
            'COMMUNITY': 'Community Server',
            'VERIFIED': 'Verified',
            'PARTNERED': 'Partnered',
            'MORE_EMOJI': 'More Emoji',
            'VIP_REGIONS': 'VIP Voice Regions',
            'VANITY_URL': 'Vanity URL',
            'BANNER': 'Server Banner'
        }
        
        for feature in guild.features:
            if feature in feature_names:
                features.append(feature_names[feature])
        
        if features:
            embed.add_field(name="Features", value="\n".join(features), inline=False)
        
        # Verification level
        verification_levels = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium", 
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        
        embed.add_field(
            name="Verification Level", 
            value=verification_levels.get(guild.verification_level, "Unknown"), 
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="avatar", description="Get a user's avatar")
    @app_commands.describe(user="User to get avatar from")
    async def avatar(self, ctx, user: discord.Member = None):
        """Get a user's avatar in full resolution"""
        if user is None:
            user = ctx.author
        
        embed = discord.Embed(
            title=f"{user.display_name}'s Avatar",
            color=user.color or discord.Color.blue()
        )
        
        avatar_url = user.display_avatar.url
        embed.set_image(url=avatar_url)
        
        # Add download links
        formats = []
        if user.avatar:
            base_url = f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}"
            formats.append(f"[PNG]({base_url}.png?size=1024)")
            formats.append(f"[JPG]({base_url}.jpg?size=1024)")
            formats.append(f"[WEBP]({base_url}.webp?size=1024)")
            
            if user.avatar.startswith('a_'):  # Animated avatar
                formats.append(f"[GIF]({base_url}.gif?size=1024)")
        
        if formats:
            embed.add_field(name="Download", value=" | ".join(formats), inline=False)
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="ping", description="Check bot latency")
    async def ping(self, ctx):
        """Check bot latency and response time"""
        # Measure message round trip time
        start_time = datetime.utcnow()
        message = await ctx.send("🏓 Pinging...")
        end_time = datetime.utcnow()
        
        # Calculate times
        api_latency = round(self.bot.latency * 1000)
        message_latency = round((end_time - start_time).total_seconds() * 1000)
        
        embed = create_embed("🏓 Pong!", color=discord.Color.green())
        embed.add_field(name="API Latency", value=f"{api_latency}ms", inline=True)
        embed.add_field(name="Message Latency", value=f"{message_latency}ms", inline=True)
        
        # Status indicator
        if api_latency < 100:
            status = "🟢 Excellent"
        elif api_latency < 200:
            status = "🟡 Good"
        elif api_latency < 500:
            status = "🟠 Fair"
        else:
            status = "🔴 Poor"
        
        embed.add_field(name="Status", value=status, inline=True)
        
        await message.edit(embed=embed, content=None)

async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))
