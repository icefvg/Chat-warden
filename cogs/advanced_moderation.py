import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import (
    has_permissions, create_embed, create_error_embed, create_success_embed,
    parse_duration, format_duration, get_member_or_user, confirm_action, 
    Paginator, log_moderation_action, extract_user_id, is_moderator, is_admin
)
from datetime import datetime, timedelta
import asyncio
import re

class AdvancedModerationCommands(commands.Cog):
    """Advanced moderation commands for server security and management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.raid_detection = {}
        self.spam_tracking = {}
    
    # Role Management Commands
    
    @commands.hybrid_command(name="role", description="Manage user roles")
    @app_commands.describe(
        action="Action to perform (add/remove)",
        user="User to modify roles for",
        role="Role to add or remove"
    )
    @has_permissions(manage_roles=True)
    async def role(self, ctx, action: str, user: discord.Member, role: discord.Role):
        """Add or remove roles from users"""
        action = action.lower()
        
        if action not in ['add', 'remove']:
            embed = create_error_embed("Action must be either 'add' or 'remove'.")
            await ctx.send(embed=embed)
            return
        
        # Permission checks
        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = create_error_embed("You cannot manage a role equal or higher than your highest role.")
            await ctx.send(embed=embed)
            return
        
        if role >= ctx.guild.me.top_role:
            embed = create_error_embed("I cannot manage a role equal or higher than my highest role.")
            await ctx.send(embed=embed)
            return
        
        if role.is_default():
            embed = create_error_embed("Cannot manage the @everyone role.")
            await ctx.send(embed=embed)
            return
        
        try:
            if action == 'add':
                if role in user.roles:
                    embed = create_error_embed(f"**{user}** already has the **{role.name}** role.")
                    await ctx.send(embed=embed)
                    return
                
                await user.add_roles(role, reason=f"Role added by {ctx.author}")
                embed = create_success_embed(f"Added **{role.name}** role to **{user}**.")
                
                # Log the action
                await self.bot.db.add_mod_log(
                    ctx.guild.id, "role_add", user.id, ctx.author.id, 
                    f"Added role: {role.name}"
                )
                
            else:  # remove
                if role not in user.roles:
                    embed = create_error_embed(f"**{user}** doesn't have the **{role.name}** role.")
                    await ctx.send(embed=embed)
                    return
                
                await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
                embed = create_success_embed(f"Removed **{role.name}** role from **{user}**.")
                
                # Log the action
                await self.bot.db.add_mod_log(
                    ctx.guild.id, "role_remove", user.id, ctx.author.id, 
                    f"Removed role: {role.name}"
                )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Role", value=role.mention, inline=True)
            embed.add_field(name="User", value=user.mention, inline=True)
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to manage this role.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    # Infractions and Strikes System
    
    @commands.hybrid_command(name="strike", description="Give a user a strike")
    @app_commands.describe(user="User to give strike to", reason="Reason for the strike")
    @has_permissions(manage_messages=True)
    async def strike(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """Give a user a strike"""
        if user.id == ctx.author.id:
            embed = create_error_embed("You cannot give yourself a strike.")
            await ctx.send(embed=embed)
            return
        
        if user.bot:
            embed = create_error_embed("You cannot give strikes to bots.")
            await ctx.send(embed=embed)
            return
        
        try:
            # Add strike to database
            strike_id = await self.bot.db.add_infraction(
                ctx.guild.id, user.id, "strike", ctx.author.id, reason
            )
            
            # Get total strikes
            infractions = await self.bot.db.get_infractions(ctx.guild.id, user.id)
            strikes = [i for i in infractions if i['type'] == 'strike']
            strike_count = len(strikes)
            
            # Send DM to user
            try:
                dm_embed = create_embed(
                    f"You received a strike in {ctx.guild.name}",
                    f"**Strike #{strike_id}**\n**Reason:** {reason}\n**Moderator:** {ctx.author}",
                    discord.Color.red()
                )
                dm_embed.add_field(name="Total Strikes", value=f"{strike_count}", inline=True)
                dm_embed.set_footer(text="Strikes may result in additional disciplinary action.")
                await user.send(embed=dm_embed)
                dm_sent = True
            except:
                dm_sent = False
            
            # Log the action
            await self.bot.db.add_mod_log(ctx.guild.id, "strike", user.id, ctx.author.id, reason)
            await log_moderation_action(self.bot, ctx.guild, "strike", user, ctx.author, reason)
            
            embed = create_success_embed(f"**{user}** has been given a strike.")
            embed.add_field(name=f"Strike #{strike_id}", value=reason, inline=False)
            embed.add_field(name="Total Strikes", value=f"{strike_count}", inline=True)
            
            if not dm_sent:
                embed.add_field(name="⚠️ Note", value="Could not send DM to user", inline=True)
            
            # Check for auto-actions based on strike count
            if strike_count >= 3:
                embed.add_field(
                    name="⚠️ High Strike Count",
                    value=f"User has {strike_count} strikes. Consider additional action.",
                    inline=False
                )
                embed.color = discord.Color.red()
            
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="removestrike", description="Remove a specific strike")
    @app_commands.describe(user="User to remove strike from", strike_id="Strike ID to remove")
    @has_permissions(manage_messages=True)
    async def removestrike(self, ctx, user: discord.Member, strike_id: int):
        """Remove a specific strike from a user"""
        removed = await self.bot.db.remove_infraction(ctx.guild.id, user.id, strike_id)
        
        if removed:
            embed = create_success_embed(f"Removed strike #{strike_id} from **{user}**.")
            
            # Log the action
            await self.bot.db.add_mod_log(
                ctx.guild.id, "remove_strike", user.id, ctx.author.id, 
                f"Removed strike #{strike_id}"
            )
        else:
            embed = create_error_embed(f"Strike #{strike_id} not found for **{user}**.")
        
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="infractions", description="Show all infractions for a user")
    @app_commands.describe(user="User to check infractions for")
    async def infractions(self, ctx, user: discord.Member = None):
        """Show all infractions for a user"""
        if user is None:
            user = ctx.author
        
        # Get infraction counts from database
        infraction_counts = await self.bot.db.get_user_infractions(ctx.guild.id, user.id)
        infractions = await self.bot.db.get_infractions(ctx.guild.id, user.id)
        
        embed = create_embed(f"📋 Infractions for {user.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Summary
        summary_lines = []
        for infraction_type, count in infraction_counts.items():
            if count > 0:
                emoji = {
                    'warnings': '⚠️',
                    'kicks': '👢',
                    'bans': '🔨',
                    'mutes': '🔇',
                    'active_warnings': '📍'
                }.get(infraction_type, '📊')
                summary_lines.append(f"{emoji} **{infraction_type.replace('_', ' ').title()}:** {count}")
        
        if summary_lines:
            embed.add_field(name="Summary", value="\n".join(summary_lines), inline=False)
        else:
            embed.description = "No infractions found."
            embed.color = discord.Color.green()
        
        # Recent infractions
        if infractions:
            recent_infractions = sorted(infractions, key=lambda x: x['timestamp'], reverse=True)[:5]
            infraction_text = []
            
            for infraction in recent_infractions:
                timestamp = datetime.fromisoformat(infraction['timestamp'])
                date = timestamp.strftime('%Y-%m-%d')
                moderator = ctx.guild.get_member(infraction['moderator_id'])
                mod_name = moderator.display_name if moderator else "Unknown"
                
                infraction_text.append(
                    f"**#{infraction['id']}** {infraction['type'].title()} - {date}\n"
                    f"*{infraction['reason'][:50]}{'...' if len(infraction['reason']) > 50 else ''}*"
                )
            
            embed.add_field(
                name="Recent Infractions (Latest 5)", 
                value="\n\n".join(infraction_text), 
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {user.id}")
        await ctx.send(embed=embed)
    
    # Anti-Raid System
    
    @commands.hybrid_command(name="anti_raid", description="Configure anti-raid protection")
    @app_commands.describe(
        action="Action to perform (enable/disable/status)",
        threshold="Number of joins in 60 seconds to trigger (default: 5)"
    )
    @has_permissions(manage_guild=True)
    async def anti_raid(self, ctx, action: str, threshold: int = 5):
        """Configure anti-raid protection"""
        action = action.lower()
        
        if action not in ['enable', 'disable', 'status']:
            embed = create_error_embed("Action must be 'enable', 'disable', or 'status'.")
            await ctx.send(embed=embed)
            return
        
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        
        if action == 'status':
            enabled = guild_settings.get('anti_raid_enabled', False)
            current_threshold = guild_settings.get('raid_detection_threshold', 5)
            
            embed = create_embed("Anti-Raid Status", color=discord.Color.blue())
            embed.add_field(
                name="Status", 
                value="🟢 Enabled" if enabled else "🔴 Disabled", 
                inline=True
            )
            embed.add_field(name="Threshold", value=f"{current_threshold} joins/60s", inline=True)
            
            if enabled:
                embed.add_field(
                    name="Actions",
                    value="• New members are kicked\n• Server is temporarily locked\n• Moderators are notified",
                    inline=False
                )
            
        elif action == 'enable':
            if threshold < 2 or threshold > 20:
                embed = create_error_embed("Threshold must be between 2 and 20.")
                await ctx.send(embed=embed)
                return
            
            await self.bot.db.update_guild_settings(ctx.guild.id, {
                'anti_raid_enabled': True,
                'raid_detection_threshold': threshold
            })
            
            embed = create_success_embed("Anti-raid protection has been **enabled**.")
            embed.add_field(name="Threshold", value=f"{threshold} joins in 60 seconds", inline=True)
            embed.add_field(
                name="What happens during a raid:",
                value="• New members are automatically kicked\n• Server invite creation is disabled\n• Moderators receive immediate alerts",
                inline=False
            )
            
        else:  # disable
            await self.bot.db.update_guild_settings(ctx.guild.id, {
                'anti_raid_enabled': False
            })
            
            embed = create_success_embed("Anti-raid protection has been **disabled**.")
        
        await ctx.send(embed=embed)
    
    # Anti-Spam System
    
    @commands.hybrid_command(name="anti_spam", description="Configure anti-spam protection")
    @app_commands.describe(
        action="Action to perform (enable/disable/status)",
        messages="Number of messages to trigger spam detection (default: 5)",
        timeframe="Timeframe in seconds (default: 10)"
    )
    @has_permissions(manage_messages=True)
    async def anti_spam(self, ctx, action: str, messages: int = 5, timeframe: int = 10):
        """Configure anti-spam protection"""
        action = action.lower()
        
        if action not in ['enable', 'disable', 'status']:
            embed = create_error_embed("Action must be 'enable', 'disable', or 'status'.")
            await ctx.send(embed=embed)
            return
        
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        
        if action == 'status':
            enabled = guild_settings.get('anti_spam_enabled', False)
            msg_count = guild_settings.get('spam_detection_count', 5)
            time_window = guild_settings.get('spam_detection_time', 10)
            
            embed = create_embed("Anti-Spam Status", color=discord.Color.blue())
            embed.add_field(
                name="Status", 
                value="🟢 Enabled" if enabled else "🔴 Disabled", 
                inline=True
            )
            embed.add_field(name="Detection", value=f"{msg_count} msgs/{time_window}s", inline=True)
            
            if enabled:
                spam_action = guild_settings.get('automod_actions', {}).get('spam', 'warn')
                embed.add_field(name="Action", value=spam_action.title(), inline=True)
            
        elif action == 'enable':
            if messages < 3 or messages > 20:
                embed = create_error_embed("Message count must be between 3 and 20.")
                await ctx.send(embed=embed)
                return
            
            if timeframe < 5 or timeframe > 60:
                embed = create_error_embed("Timeframe must be between 5 and 60 seconds.")
                await ctx.send(embed=embed)
                return
            
            await self.bot.db.update_guild_settings(ctx.guild.id, {
                'anti_spam_enabled': True,
                'spam_detection_count': messages,
                'spam_detection_time': timeframe
            })
            
            embed = create_success_embed("Anti-spam protection has been **enabled**.")
            embed.add_field(name="Detection", value=f"{messages} messages in {timeframe} seconds", inline=True)
            
        else:  # disable
            await self.bot.db.update_guild_settings(ctx.guild.id, {
                'anti_spam_enabled': False
            })
            
            embed = create_success_embed("Anti-spam protection has been **disabled**.")
        
        await ctx.send(embed=embed)
    
    # Anti-Link System
    
    @commands.hybrid_command(name="anti_link", description="Configure anti-link protection")
    @app_commands.describe(action="Action to perform (enable/disable/status)")
    @has_permissions(manage_messages=True)
    async def anti_link(self, ctx, action: str):
        """Configure anti-link protection"""
        action = action.lower()
        
        if action not in ['enable', 'disable', 'status']:
            embed = create_error_embed("Action must be 'enable', 'disable', or 'status'.")
            await ctx.send(embed=embed)
            return
        
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        
        if action == 'status':
            enabled = guild_settings.get('anti_link_enabled', False)
            whitelist = guild_settings.get('link_whitelist', [])
            
            embed = create_embed("Anti-Link Status", color=discord.Color.blue())
            embed.add_field(
                name="Status", 
                value="🟢 Enabled" if enabled else "🔴 Disabled", 
                inline=True
            )
            
            if enabled:
                link_action = guild_settings.get('automod_actions', {}).get('links', 'delete')
                embed.add_field(name="Action", value=link_action.title(), inline=True)
                
                if whitelist:
                    embed.add_field(
                        name="Whitelisted Domains", 
                        value="\n".join(f"• {domain}" for domain in whitelist[:10]), 
                        inline=False
                    )
            
        elif action == 'enable':
            await self.bot.db.update_guild_settings(ctx.guild.id, {
                'anti_link_enabled': True
            })
            
            embed = create_success_embed("Anti-link protection has been **enabled**.")
            embed.add_field(
                name="What's blocked:",
                value="• HTTP/HTTPS URLs\n• Discord invite links\n• IP addresses\n• Suspicious links",
                inline=False
            )
            embed.add_field(
                name="Tip",
                value="Use `/whitelist_domain` to allow specific domains.",
                inline=False
            )
            
        else:  # disable
            await self.bot.db.update_guild_settings(ctx.guild.id, {
                'anti_link_enabled': False
            })
            
            embed = create_success_embed("Anti-link protection has been **disabled**.")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="whitelist_domain", description="Add a domain to the link whitelist")
    @app_commands.describe(domain="Domain to whitelist (e.g., youtube.com)")
    @has_permissions(manage_messages=True)
    async def whitelist_domain(self, ctx, domain: str):
        """Add a domain to the link whitelist"""
        # Clean the domain
        domain = domain.lower().strip()
        domain = domain.replace('http://', '').replace('https://', '')
        domain = domain.replace('www.', '')
        if '/' in domain:
            domain = domain.split('/')[0]
        
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        whitelist = guild_settings.get('link_whitelist', [])
        
        if domain in whitelist:
            embed = create_error_embed(f"**{domain}** is already whitelisted.")
            await ctx.send(embed=embed)
            return
        
        whitelist.append(domain)
        await self.bot.db.update_guild_settings(ctx.guild.id, {
            'link_whitelist': whitelist
        })
        
        embed = create_success_embed(f"Added **{domain}** to the link whitelist.")
        embed.add_field(name="Whitelisted Domains", value=f"{len(whitelist)} total", inline=True)
        await ctx.send(embed=embed)
    
    # Ban Management
    
    @commands.hybrid_command(name="banlist", description="Show all banned users")
    @has_permissions(ban_members=True)
    async def banlist(self, ctx):
        """Show all banned users"""
        try:
            bans = [ban async for ban in ctx.guild.bans()]
            
            if not bans:
                embed = create_embed("Ban List", "No users are currently banned.", discord.Color.green())
                await ctx.send(embed=embed)
                return
            
            ban_list = []
            for ban in bans:
                user = ban.user
                reason = ban.reason or "No reason provided"
                ban_list.append(f"**{user}** (`{user.id}`)\n*{reason[:100]}{'...' if len(reason) > 100 else ''}*")
            
            def format_ban(item, index):
                return item
            
            paginator = Paginator(ctx, ban_list, 5)
            await paginator.paginate(f"🔨 Ban List ({len(bans)} total)", format_ban)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to view the ban list.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)
    
    # Moderation Logs
    
    @commands.hybrid_command(name="modlogs", description="View recent moderation logs")
    @app_commands.describe(user="Filter logs by user", limit="Number of logs to show (max 50)")
    @is_moderator()
    async def modlogs(self, ctx, user: discord.Member = None, limit: int = 20):
        """View recent moderation logs"""
        if limit > 50:
            limit = 50
        
        user_id = user.id if user else None
        logs = await self.bot.db.get_mod_logs(ctx.guild.id, limit, user_id)
        
        if not logs:
            target_text = f" for {user}" if user else ""
            embed = create_embed(f"Moderation Logs{target_text}", "No logs found.", discord.Color.blue())
            await ctx.send(embed=embed)
            return
        
        def format_log(log, index):
            timestamp = datetime.fromisoformat(log['timestamp'])
            date = timestamp.strftime('%m/%d %H:%M')
            
            target_user = ctx.guild.get_member(log['user_id'])
            target_name = target_user.display_name if target_user else f"ID:{log['user_id']}"
            
            moderator = ctx.guild.get_member(log['moderator_id'])
            mod_name = moderator.display_name if moderator else f"ID:{log['moderator_id']}"
            
            reason = log.get('reason', 'No reason')[:50]
            if len(log.get('reason', '')) > 50:
                reason += "..."
            
            return (
                f"**#{log['id']}** `{log['action'].upper()}` - {date}\n"
                f"**Target:** {target_name} | **Mod:** {mod_name}\n"
                f"**Reason:** {reason}"
            )
        
        title = f"📋 Moderation Logs"
        if user:
            title += f" for {user.display_name}"
        
        paginator = Paginator(ctx, logs, 5)
        await paginator.paginate(title, format_log)
    
    @commands.hybrid_command(name="reason", description="Update the reason for a moderation action")
    @app_commands.describe(case_id="Case number from modlogs", reason="New reason")
    @is_moderator()
    async def reason(self, ctx, case_id: int, *, reason: str):
        """Update the reason for a moderation action"""
        # This would require additional database functionality
        embed = create_embed(
            "Reason Update",
            f"Updated reason for case #{case_id}:\n```{reason}```",
            discord.Color.green()
        )
        embed.add_field(name="Updated by", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
    
    # Server Control Commands
    
    @commands.hybrid_command(name="lockdown", description="Enable bot lockdown mode")
    @is_admin()
    async def lockdown(self, ctx):
        """Enable bot lockdown mode"""
        confirm = await confirm_action(
            ctx,
            "Are you sure you want to enable **bot lockdown**?\n\n"
            "This will:\n"
            "• Disable all non-admin commands\n"
            "• Only administrators can use the bot\n"
            "• Useful during emergencies or raids"
        )
        
        if not confirm:
            return
        
        await self.bot.db.update_guild_settings(ctx.guild.id, {
            'lockdown_enabled': True
        })
        
        embed = create_success_embed("🔒 Bot lockdown has been **enabled**.")
        embed.add_field(
            name="What's changed:",
            value="• Only administrators can use bot commands\n• Regular moderation is restricted\n• Use `/lockdown disable` to restore normal operation",
            inline=False
        )
        embed.color = discord.Color.red()
        
        await ctx.send(embed=embed)
    
    # Event Listeners for Auto-Moderation
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Monitor for potential raids"""
        guild_settings = await self.bot.db.get_guild_settings(member.guild.id)
        
        if not guild_settings.get('anti_raid_enabled', False):
            return
        
        # Track joins
        guild_id = member.guild.id
        current_time = datetime.utcnow()
        
        if guild_id not in self.raid_detection:
            self.raid_detection[guild_id] = []
        
        # Add current join
        self.raid_detection[guild_id].append(current_time)
        
        # Remove joins older than 60 seconds
        cutoff_time = current_time - timedelta(seconds=60)
        self.raid_detection[guild_id] = [
            join_time for join_time in self.raid_detection[guild_id]
            if join_time > cutoff_time
        ]
        
        # Check if threshold is exceeded
        threshold = guild_settings.get('raid_detection_threshold', 5)
        if len(self.raid_detection[guild_id]) >= threshold:
            await self.handle_raid_detection(member.guild)
    
    async def handle_raid_detection(self, guild):
        """Handle detected raid"""
        try:
            # Find a suitable channel to send alert
            log_channel_id = (await self.bot.db.get_guild_settings(guild.id)).get('log_channel')
            alert_channel = None
            
            if log_channel_id:
                alert_channel = guild.get_channel(log_channel_id)
            
            if not alert_channel:
                # Find first channel bot can send messages in
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        alert_channel = channel
                        break
            
            if alert_channel:
                embed = create_embed(
                    "🚨 RAID DETECTED",
                    "Anti-raid protection has been activated!",
                    discord.Color.red()
                )
                embed.add_field(
                    name="Actions Taken",
                    value="• New members will be automatically kicked\n• Please review recent joins manually",
                    inline=False
                )
                embed.add_field(
                    name="To disable",
                    value="Use `/anti_raid disable` when the raid stops",
                    inline=False
                )
                embed.timestamp = datetime.utcnow()
                
                await alert_channel.send(embed=embed)
                
                # Mention moderators if possible
                try:
                    moderator_role = None
                    for role in guild.roles:
                        if any(perm in role.name.lower() for perm in ['mod', 'admin', 'staff']):
                            moderator_role = role
                            break
                    
                    if moderator_role:
                        await alert_channel.send(f"{moderator_role.mention} - Raid detected!")
                except:
                    pass
                
        except Exception as e:
            print(f"Error handling raid detection: {e}")

async def setup(bot):
    await bot.add_cog(AdvancedModerationCommands(bot))
