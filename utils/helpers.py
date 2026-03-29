import discord
from discord.ext import commands
from typing import Union, Optional, List, Callable
import re
import asyncio
import time
from datetime import datetime, timedelta

def has_permissions(**permissions):
    """Check if user has required permissions"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        
        user_perms = ctx.author.guild_permissions
        for perm, value in permissions.items():
            if getattr(user_perms, perm) != value:
                return False
        return True
    
    return commands.check(predicate)

def is_moderator():
    """Check if user is a moderator"""
    async def predicate(ctx):
        return (ctx.author.guild_permissions.manage_messages or 
                ctx.author.guild_permissions.kick_members or
                ctx.author.guild_permissions.ban_members or
                ctx.author.guild_permissions.administrator)
    
    return commands.check(predicate)

def is_admin():
    """Check if user is an admin"""
    async def predicate(ctx):
        return (ctx.author.guild_permissions.administrator or
                ctx.author == ctx.guild.owner)
    
    return commands.check(predicate)

def parse_duration(duration_str: str) -> Optional[timedelta]:
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

def format_duration(delta: timedelta) -> str:
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

async def get_member_or_user(ctx, user_id: int) -> Optional[Union[discord.Member, discord.User]]:
    """Get member from guild or user from Discord"""
    try:
        # Try to get as member first
        member = ctx.guild.get_member(user_id)
        if member:
            return member
        
        # Try to fetch as user
        user = await ctx.bot.fetch_user(user_id)
        return user
    except:
        return None

async def safe_send(destination, *args, **kwargs):
    """Safely send a message, handling common errors"""
    try:
        return await destination.send(*args, **kwargs)
    except discord.Forbidden:
        # Try to send to author if channel send fails
        if hasattr(destination, 'author'):
            try:
                return await destination.author.send(*args, **kwargs)
            except discord.Forbidden:
                pass
    except discord.HTTPException:
        pass
    return None

def create_embed(title: str, description: str = None, color: discord.Color = None) -> discord.Embed:
    """Create a standard embed"""
    if color is None:
        color = discord.Color.blue()
    
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.utcnow()
    return embed

def create_error_embed(message: str) -> discord.Embed:
    """Create an error embed"""
    embed = create_embed("❌ Error", message, discord.Color.red())
    return embed

def create_success_embed(message: str) -> discord.Embed:
    """Create a success embed"""
    embed = create_embed("✅ Success", message, discord.Color.green())
    return embed

def create_warning_embed(message: str) -> discord.Embed:
    """Create a warning embed"""
    embed = create_embed("⚠️ Warning", message, discord.Color.orange())
    return embed

def create_info_embed(message: str) -> discord.Embed:
    """Create an info embed"""
    embed = create_embed("ℹ️ Information", message, discord.Color.blue())
    return embed

async def confirm_action(ctx, message: str, timeout: int = 30) -> bool:
    """Ask user to confirm an action"""
    embed = create_embed("Confirmation Required", message, discord.Color.orange())
    embed.add_field(name="React with:", value="✅ to confirm\n❌ to cancel", inline=False)
    embed.set_footer(text=f"This will timeout in {timeout} seconds")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return (user == ctx.author and 
                str(reaction.emoji) in ["✅", "❌"] and 
                reaction.message.id == msg.id)
    
    try:
        reaction, user = await ctx.bot.wait_for('reaction_add', timeout=timeout, check=check)
        await msg.delete()
        return str(reaction.emoji) == "✅"
    except asyncio.TimeoutError:
        try:
            await msg.delete()
        except:
            pass
        return False

def format_user(user: Union[discord.Member, discord.User]) -> str:
    """Format user for display"""
    if isinstance(user, discord.Member):
        return f"{user.display_name} ({user})"
    else:
        return str(user)

def format_timestamp(dt: datetime, format_type: str = "f") -> str:
    """Format timestamp for Discord"""
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:{format_type}>"

def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to fit within limits"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

class Paginator:
    """Simple paginator for long lists"""
    
    def __init__(self, ctx, items: list, per_page: int = 10, timeout: int = 300):
        self.ctx = ctx
        self.items = items
        self.per_page = per_page
        self.current_page = 0
        self.max_pages = max(1, (len(items) - 1) // per_page + 1) if items else 1
        self.timeout = timeout
    
    def get_page_items(self):
        """Get items for current page"""
        start = self.current_page * self.per_page
        end = start + self.per_page
        return self.items[start:end]
    
    def create_embed(self, title: str, formatter: Callable = None) -> discord.Embed:
        """Create embed for current page"""
        items = self.get_page_items()
        
        if not items:
            embed = create_embed(title, "No items to display.")
            embed.set_footer(text="Page 1/1")
            return embed
        
        if formatter:
            description = "\n".join(formatter(item, i + self.current_page * self.per_page) 
                                  for i, item in enumerate(items))
        else:
            description = "\n".join(str(item) for item in items)
        
        # Truncate if too long
        description = truncate_text(description, 2000)
        
        embed = create_embed(title, description)
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} • {len(self.items)} total items")
        return embed
    
    async def paginate(self, title: str, formatter: Callable = None):
        """Start pagination"""
        if self.max_pages <= 1:
            embed = self.create_embed(title, formatter)
            await self.ctx.send(embed=embed)
            return
        
        embed = self.create_embed(title, formatter)
        msg = await self.ctx.send(embed=embed)
        
        # Add reactions
        reactions = ["⏪", "⬅️", "➡️", "⏩", "❌"]
        for reaction in reactions:
            try:
                await msg.add_reaction(reaction)
            except:
                break
        
        def check(reaction, user):
            return (user == self.ctx.author and 
                    str(reaction.emoji) in reactions and 
                    reaction.message.id == msg.id)
        
        while True:
            try:
                reaction, user = await self.ctx.bot.wait_for('reaction_add', timeout=self.timeout, check=check)
                
                if str(reaction.emoji) == "❌":
                    await msg.delete()
                    break
                elif str(reaction.emoji) == "⏪" and self.current_page > 0:
                    self.current_page = 0
                elif str(reaction.emoji) == "⬅️" and self.current_page > 0:
                    self.current_page -= 1
                elif str(reaction.emoji) == "➡️" and self.current_page < self.max_pages - 1:
                    self.current_page += 1
                elif str(reaction.emoji) == "⏩" and self.current_page < self.max_pages - 1:
                    self.current_page = self.max_pages - 1
                
                embed = self.create_embed(title, formatter)
                await msg.edit(embed=embed)
                
                try:
                    await msg.remove_reaction(reaction.emoji, user)
                except:
                    pass
                
            except asyncio.TimeoutError:
                try:
                    await msg.clear_reactions()
                except:
                    pass
                break

class CooldownManager:
    """Manage cooldowns for various actions"""
    
    def __init__(self):
        self.cooldowns = {}
    
    def is_on_cooldown(self, key: str, cooldown_time: int) -> bool:
        """Check if key is on cooldown"""
        if key not in self.cooldowns:
            return False
        
        return time.time() - self.cooldowns[key] < cooldown_time
    
    def add_cooldown(self, key: str):
        """Add key to cooldown"""
        self.cooldowns[key] = time.time()
    
    def get_remaining_cooldown(self, key: str, cooldown_time: int) -> float:
        """Get remaining cooldown time"""
        if key not in self.cooldowns:
            return 0.0
        
        elapsed = time.time() - self.cooldowns[key]
        remaining = cooldown_time - elapsed
        return max(0.0, remaining)
    
    def cleanup_expired(self, max_age: int = 3600):
        """Remove expired cooldowns"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cooldowns.items()
            if current_time - timestamp > max_age
        ]
        
        for key in expired_keys:
            del self.cooldowns[key]

def extract_user_id(user_input: str) -> Optional[int]:
    """Extract user ID from mention or string"""
    # Remove mention formatting
    user_input = user_input.strip('<@!>')
    
    try:
        return int(user_input)
    except ValueError:
        return None

def format_permissions(permissions: discord.Permissions) -> List[str]:
    """Format permissions into readable list"""
    permission_names = {
        'administrator': 'Administrator',
        'manage_guild': 'Manage Server',
        'manage_roles': 'Manage Roles',
        'manage_channels': 'Manage Channels',
        'kick_members': 'Kick Members',
        'ban_members': 'Ban Members',
        'manage_messages': 'Manage Messages',
        'manage_webhooks': 'Manage Webhooks',
        'moderate_members': 'Timeout Members',
        'view_audit_log': 'View Audit Log'
    }
    
    active_perms = []
    for perm, value in permissions:
        if value and perm in permission_names:
            active_perms.append(permission_names[perm])
    
    return active_perms

async def log_moderation_action(bot, guild: discord.Guild, action: str, target: discord.User, moderator: discord.User, reason: str = None, duration: str = None):
    """Log a moderation action to the configured log channel"""
    try:
        guild_settings = await bot.db.get_guild_settings(guild.id)
        log_channel_id = guild_settings.get('log_channel')
        
        if not log_channel_id:
            return
        
        log_channel = bot.get_channel(log_channel_id)
        if not log_channel:
            return
        
        # Create log embed
        color_map = {
            'kick': discord.Color.orange(),
            'ban': discord.Color.red(),
            'unban': discord.Color.green(),
            'mute': discord.Color.yellow(),
            'unmute': discord.Color.green(),
            'warn': discord.Color.orange(),
            'timeout': discord.Color.yellow()
        }
        
        embed = discord.Embed(
            title=f"🔨 {action.title()} Action",
            color=color_map.get(action.lower(), discord.Color.blue()),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Target", value=f"{target} ({target.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator} ({moderator.id})", inline=True)
        
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason[:1000], inline=False)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await log_channel.send(embed=embed)
        
    except Exception as e:
        print(f"Failed to log moderation action: {e}")
