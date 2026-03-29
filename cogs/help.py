import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import create_embed, Paginator

class HelpCommand(commands.Cog):
    """Help command for the moderation bot"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Remove default help command
        bot.remove_command('help')
    
    @commands.hybrid_command(name="help", description="Show help information")
    @app_commands.describe(category="Specific category to show help for")
    async def help(self, ctx, category: str = None):
        """Show help information for the bot"""
        if category:
            await self.show_category_help(ctx, category.lower())
        else:
            await self.show_main_help(ctx)
    
    async def show_main_help(self, ctx):
        """Show the main help menu"""
        embed = create_embed(
            "🛡️ Moderation Bot Help",
            "A comprehensive Discord moderation bot with advanced features.",
            discord.Color.blue()
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # Categories
        categories = [
            {
                "name": "🔧 Admin Commands",
                "value": (
                    "• Server configuration\n"
                    "• Profanity filter settings\n"
                    "• Bot management\n"
                    "*Use: `/help admin`*"
                ),
                "inline": True
            },
            {
                "name": "⚖️ Moderation",
                "value": (
                    "• Kick, ban, mute, warn\n"
                    "• Message management\n"
                    "• Channel control\n"
                    "*Use: `/help moderation`*"
                ),
                "inline": True
            },
            {
                "name": "🔍 Profanity Filter",
                "value": (
                    "• Word management\n"
                    "• Filter testing\n"
                    "• Webhook controls\n"
                    "*Use: `/help profanity`*"
                ),
                "inline": True
            },
            {
                "name": "🛡️ Advanced Mod",
                "value": (
                    "• Anti-raid/spam/link\n"
                    "• Role management\n"
                    "• Infractions system\n"
                    "*Use: `/help advanced`*"
                ),
                "inline": True
            },
            {
                "name": "🎮 Utility",
                "value": (
                    "• Server information\n"
                    "• Announcements\n"
                    "• Polls and tools\n"
                    "*Use: `/help utility`*"
                ),
                "inline": True
            },
            {
                "name": "❓ Support",
                "value": (
                    "• Quick tips\n"
                    "• Common issues\n"
                    "• Best practices\n"
                    "*Use: `/help support`*"
                ),
                "inline": True
            }
        ]
        
        for category in categories:
            embed.add_field(**category)
        
        # Quick start
        embed.add_field(
            name="🚀 Quick Start",
            value=(
                "1. Use `/toggle_profanity` to enable filtering\n"
                "2. Use `/set_log_channel` for moderation logs\n"
                "3. Use `/server_settings` to view configuration\n"
                "4. Type `/help [category]` for detailed commands"
            ),
            inline=False
        )
        
        # Footer
        embed.set_footer(
            text=f"Bot supports both slash commands (/) and prefix commands (!,?,/) • Total Commands: {len([cmd for cmd in self.bot.commands])}"
        )
        
        await ctx.send(embed=embed)
    
    async def show_category_help(self, ctx, category):
        """Show help for a specific category"""
        categories = {
            'admin': self.get_admin_help(),
            'moderation': self.get_moderation_help(),
            'mod': self.get_moderation_help(),  # Alias
            'profanity': self.get_profanity_help(),
            'filter': self.get_profanity_help(),  # Alias
            'advanced': self.get_advanced_help(),
            'utility': self.get_utility_help(),
            'utils': self.get_utility_help(),  # Alias
            'support': self.get_support_help()
        }
        
        if category not in categories:
            embed = create_embed(
                "❌ Category Not Found",
                f"Category `{category}` not found. Use `/help` to see all categories.",
                discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        embed_data = categories[category]
        embed = create_embed(embed_data['title'], embed_data['description'], discord.Color.blue())
        
        for field in embed_data['fields']:
            embed.add_field(**field)
        
        embed.set_footer(text="Use /help to go back to the main menu")
        
        await ctx.send(embed=embed)
    
    def get_admin_help(self):
        """Get admin commands help"""
        return {
            'title': '🔧 Admin Commands',
            'description': 'Server configuration and bot management commands. Requires appropriate permissions.',
            'fields': [
                {
                    'name': 'Profanity Filter',
                    'value': (
                        '`/toggle_profanity [enabled]` - Enable/disable filtering\n'
                        '`/set_channels [channels]` - Set active channels\n'
                        '`/add_censor <word> [replacement]` - Add word to filter\n'
                        '`/remove_censor <word>` - Remove word from filter\n'
                        '`/list_censors` - Show filter statistics'
                    ),
                    'inline': False
                },
                {
                    'name': 'Server Settings',
                    'value': (
                        '`/set_log_channel [channel]` - Set moderation logs\n'
                        '`/set_prefix <prefix>` - Add command prefix\n'
                        '`/remove_prefix <prefix>` - Remove prefix\n'
                        '`/server_settings` - View current settings\n'
                        '`/bot_info` - Show bot statistics'
                    ),
                    'inline': False
                },
                {
                    'name': 'Required Permissions',
                    'value': 'Manage Server, Manage Messages, Manage Webhooks',
                    'inline': False
                }
            ]
        }
    
    def get_moderation_help(self):
        """Get moderation commands help"""
        return {
            'title': '⚖️ Moderation Commands',
            'description': 'Essential moderation tools for managing your server members and messages.',
            'fields': [
                {
                    'name': 'Member Actions',
                    'value': (
                        '`/kick <user> [reason]` - Kick a user\n'
                        '`/ban <user> [delete_days] [reason]` - Ban a user\n'
                        '`/unban <user_id> [reason]` - Unban a user\n'
                        '`/mute <user> [duration] [reason]` - Timeout a user\n'
                        '`/unmute <user> [reason]` - Remove timeout'
                    ),
                    'inline': False
                },
                {
                    'name': 'Warnings',
                    'value': (
                        '`/warn <user> [reason]` - Warn a user\n'
                        '`/warnings [user]` - View user warnings\n'
                        '`/clearwarnings <user>` - Clear all warnings'
                    ),
                    'inline': False
                },
                {
                    'name': 'Message Management',
                    'value': (
                        '`/clear <amount>` - Delete messages in bulk\n'
                        '`/purge <user> [amount]` - Delete user messages\n'
                        '`/slowmode <seconds>` - Set channel slowmode'
                    ),
                    'inline': False
                },
                {
                    'name': 'Channel Control',
                    'value': (
                        '`/lock` - Lock current channel\n'
                        '`/unlock` - Unlock current channel\n'
                        '`/nuke` - Delete and recreate channel'
                    ),
                    'inline': False
                }
            ]
        }
    
    def get_profanity_help(self):
        """Get profanity filter help"""
        return {
            'title': '🔍 Profanity Filter Commands',
            'description': 'Advanced profanity filtering with smart detection and webhook replacement.',
            'fields': [
                {
                    'name': 'Testing & Management',
                    'value': (
                        '`/test_filter <message>` - Test filter on text\n'
                        '`/filter_stats` - Show filter statistics\n'
                        '`/bypass_test` - Test common bypass methods\n'
                        '`/webhook_test` - Test webhook functionality'
                    ),
                    'inline': False
                },
                {
                    'name': 'Word Replacements',
                    'value': (
                        '`/add_replacement <word> <replacement>` - Set replacement\n'
                        '`/remove_replacement <word>` - Remove replacement\n'
                        '`/list_replacements` - View all replacements'
                    ),
                    'inline': False
                },
                {
                    'name': 'Webhook Management',
                    'value': (
                        '`/cleanup_webhooks` - Clean unused webhooks\n'
                        '*Webhooks preserve user identity when replacing messages*'
                    ),
                    'inline': False
                },
                {
                    'name': 'Features',
                    'value': (
                        '• Detects leetspeak (f*ck, 5h1t)\n'
                        '• Handles obfuscation (f.u.c.k)\n'
                        '• Unicode bypass protection\n'
                        '• 2-second user cooldown\n'
                        '• Comprehensive word database'
                    ),
                    'inline': False
                }
            ]
        }
    
    def get_advanced_help(self):
        """Get advanced moderation help"""
        return {
            'title': '🛡️ Advanced Moderation',
            'description': 'Advanced security features and automated protection systems.',
            'fields': [
                {
                    'name': 'Anti-Systems',
                    'value': (
                        '`/anti_raid <enable/disable> [threshold]` - Raid protection\n'
                        '`/anti_spam <enable/disable> [msgs] [time]` - Spam detection\n'
                        '`/anti_link <enable/disable>` - Link filtering\n'
                        '`/whitelist_domain <domain>` - Allow specific domains'
                    ),
                    'inline': False
                },
                {
                    'name': 'Role Management',
                    'value': (
                        '`/role add <user> <role>` - Add role to user\n'
                        '`/role remove <user> <role>` - Remove role from user'
                    ),
                    'inline': False
                },
                {
                    'name': 'Infractions System',
                    'value': (
                        '`/strike <user> [reason]` - Give user a strike\n'
                        '`/removestrike <user> <strike_id>` - Remove strike\n'
                        '`/infractions [user]` - View user infractions'
                    ),
                    'inline': False
                },
                {
                    'name': 'Logs & Info',
                    'value': (
                        '`/modlogs [user] [limit]` - View mod logs\n'
                        '`/banlist` - Show all banned users\n'
                        '`/reason <case_id> <reason>` - Update log reason'
                    ),
                    'inline': False
                }
            ]
        }
    
    def get_utility_help(self):
        """Get utility commands help"""
        return {
            'title': '🎮 Utility Commands',
            'description': 'Helpful tools for server communication and information.',
            'fields': [
                {
                    'name': 'Communication',
                    'value': (
                        '`/say <message>` - Make bot say something\n'
                        '`/embed <title> [description] [color]` - Send embed\n'
                        '`/announce <channel> <message>` - Send announcement\n'
                        '`/dm <user> <message>` - Send DM via bot'
                    ),
                    'inline': False
                },
                {
                    'name': 'Interactive',
                    'value': (
                        '`/poll <question> <options>` - Create reaction poll\n'
                        '*Separate options with commas, max 10 options*'
                    ),
                    'inline': False
                },
                {
                    'name': 'Information',
                    'value': (
                        '`/userinfo [user]` - Detailed user information\n'
                        '`/serverinfo` - Server statistics and info\n'
                        '`/avatar [user]` - Get user avatar\n'
                        '`/ping` - Check bot latency'
                    ),
                    'inline': False
                }
            ]
        }
    
    def get_support_help(self):
        """Get support and tips"""
        return {
            'title': '❓ Support & Tips',
            'description': 'Common questions, troubleshooting, and best practices.',
            'fields': [
                {
                    'name': 'Getting Started',
                    'value': (
                        '1. Run `/toggle_profanity` to enable filtering\n'
                        '2. Set a log channel with `/set_log_channel`\n'
                        '3. Test the filter with `/test_filter`\n'
                        '4. Configure channels with `/set_channels`\n'
                        '5. Add custom words with `/add_censor`'
                    ),
                    'inline': False
                },
                {
                    'name': 'Common Issues',
                    'value': (
                        '**Webhook not working?**\n'
                        '• Check "Manage Webhooks" permission\n'
                        '• Run `/webhook_test` to diagnose\n\n'
                        '**Filter not detecting?**\n'
                        '• Use `/test_filter` to check detection\n'
                        '• Ensure profanity is enabled\n'
                        '• Check if channel is configured'
                    ),
                    'inline': False
                },
                {
                    'name': 'Best Practices',
                    'value': (
                        '• Set up moderation logs for transparency\n'
                        '• Test custom words before adding them\n'
                        '• Configure anti-raid during quiet hours\n'
                        '• Regularly review `/server_settings`\n'
                        '• Use `/cleanup_webhooks` monthly'
                    ),
                    'inline': False
                },
                {
                    'name': 'Required Permissions',
                    'value': (
                        '**Essential:** Manage Messages, Manage Webhooks\n'
                        '**Moderation:** Kick Members, Ban Members, Moderate Members\n'
                        '**Advanced:** Manage Roles, Manage Channels, Manage Server'
                    ),
                    'inline': False
                }
            ]
        }
    
    @commands.hybrid_command(name="commands", description="List all available commands")
    async def commands_list(self, ctx):
        """List all available commands"""
        # Organize commands by cog
        cog_commands = {}
        
        for command in self.bot.commands:
            if command.hidden:
                continue
                
            cog_name = command.cog.qualified_name if command.cog else "No Category"
            if cog_name not in cog_commands:
                cog_commands[cog_name] = []
            
            # Format command with brief description
            desc = command.description or command.help or "No description"
            if len(desc) > 50:
                desc = desc[:47] + "..."
            
            cog_commands[cog_name].append(f"`/{command.name}` - {desc}")
        
        # Create paginated list
        pages = []
        for cog_name, commands in cog_commands.items():
            # Skip if no commands
            if not commands:
                continue
                
            page_content = f"**{cog_name}**\n" + "\n".join(commands)
            pages.append(page_content)
        
        if not pages:
            embed = create_embed("Commands List", "No commands available.", discord.Color.blue())
            await ctx.send(embed=embed)
            return
        
        def format_page(content, index):
            return content
        
        paginator = Paginator(ctx, pages, 1)  # One cog per page
        await paginator.paginate("📋 All Commands", format_page)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
