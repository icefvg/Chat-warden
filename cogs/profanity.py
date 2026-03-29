import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import has_permissions, create_embed, create_error_embed, create_success_embed

class ProfanityCommands(commands.Cog):
    """Commands for managing the profanity filter"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="test_filter", description="Test the profanity filter on a message")
    @app_commands.describe(message="Message to test")
    @has_permissions(manage_messages=True)
    async def test_filter(self, ctx, *, message: str):
        """Test the profanity filter on a message"""
        contains_profanity, censored_content = await self.bot.profanity_filter.check_message(message)
        
        embed = create_embed("Profanity Filter Test", color=discord.Color.blue())
        embed.add_field(name="Original Message", value=f"```{message}```", inline=False)
        embed.add_field(name="Contains Profanity", value="Yes" if contains_profanity else "No", inline=True)
        
        if contains_profanity:
            embed.add_field(name="Censored Message", value=f"```{censored_content}```", inline=False)
            embed.color = discord.Color.orange()
        else:
            embed.color = discord.Color.green()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="filter_stats", description="Show profanity filter statistics")
    async def filter_stats(self, ctx):
        """Show profanity filter statistics"""
        word_counts = self.bot.profanity_filter.get_word_count()
        guild_settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        
        embed = create_embed("Profanity Filter Statistics", color=discord.Color.blue())
        
        # Status
        status = "Enabled" if guild_settings.get('profanity_enabled', True) else "Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Enabled channels
        enabled_channels = guild_settings.get('enabled_channels', [])
        if enabled_channels:
            channel_mentions = []
            for channel_id in enabled_channels:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channel_mentions.append(channel.mention)
            channels_text = ", ".join(channel_mentions) if channel_mentions else "None"
        else:
            channels_text = "All channels"
        
        embed.add_field(name="Active Channels", value=channels_text, inline=True)
        
        # Word counts
        total_words = sum(word_counts.values())
        embed.add_field(name="Total Filtered Words", value=str(total_words), inline=True)
        
        if word_counts:
            word_breakdown = []
            for category, count in word_counts.items():
                if count > 0:
                    word_breakdown.append(f"**{category.title()}:** {count}")
            
            if word_breakdown:
                embed.add_field(name="Word Categories", value="\n".join(word_breakdown), inline=False)
        
        # Cooldown info
        embed.add_field(name="User Cooldown", value="2 seconds", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="add_replacement", description="Add or update a word replacement")
    @app_commands.describe(word="Word to replace", replacement="Replacement text")
    @has_permissions(manage_messages=True)
    async def add_replacement(self, ctx, word: str, replacement: str):
        """Add or update a word replacement"""
        # Add to replacements
        self.bot.profanity_filter.replacements[word.lower()] = replacement
        self.bot.profanity_filter.save_word_lists()
        
        embed = create_success_embed(f"Updated replacement: `{word}` → `{replacement}`")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="remove_replacement", description="Remove a word replacement")
    @app_commands.describe(word="Word to remove replacement for")
    @has_permissions(manage_messages=True)
    async def remove_replacement(self, ctx, word: str):
        """Remove a word replacement"""
        word_lower = word.lower()
        
        if word_lower in self.bot.profanity_filter.replacements:
            del self.bot.profanity_filter.replacements[word_lower]
            self.bot.profanity_filter.save_word_lists()
            embed = create_success_embed(f"Removed replacement for `{word}`")
        else:
            embed = create_error_embed(f"No replacement found for `{word}`")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="list_replacements", description="List all word replacements")
    @has_permissions(manage_messages=True)
    async def list_replacements(self, ctx):
        """List all word replacements"""
        replacements = self.bot.profanity_filter.replacements
        
        if not replacements:
            embed = create_embed("Word Replacements", "No custom replacements configured.")
            await ctx.send(embed=embed)
            return
        
        # Create paginated list
        replacement_list = []
        for word, replacement in sorted(replacements.items()):
            replacement_list.append(f"`{word}` → `{replacement}`")
        
        from utils.helpers import Paginator
        
        def format_replacement(item, index):
            return item
        
        paginator = Paginator(ctx, replacement_list, 15)
        await paginator.paginate("Word Replacements", format_replacement)
    
    @commands.hybrid_command(name="bypass_test", description="Test common bypass methods")
    @has_permissions(manage_messages=True)
    async def bypass_test(self, ctx):
        """Test common bypass methods against the filter"""
        test_cases = [
            "fuck",
            "f*ck",
            "f.u.c.k",
            "f__k",
            "f-ck",
            "fuk",
            "fück",
            "ƒuck",
            "f u c k",
            "F.U.C.K",
            "shit",
            "sh*t",
            "5h1t",
            "sh!t",
            "s.h.i.t",
            "bitch",
            "b1tch",
            "b*tch",
            "b.i.t.c.h"
        ]
        
        results = []
        for test_case in test_cases:
            contains_profanity, censored = await self.bot.profanity_filter.check_message(test_case)
            status = "🚫" if contains_profanity else "✅"
            results.append(f"{status} `{test_case}` → `{censored if contains_profanity else 'unchanged'}`")
        
        embed = create_embed("Bypass Detection Test", color=discord.Color.blue())
        embed.description = "\n".join(results)
        embed.add_field(
            name="Legend", 
            value="🚫 Detected and filtered\n✅ Not detected (potential bypass)", 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="webhook_test", description="Test webhook functionality")
    @has_permissions(manage_webhooks=True)
    async def webhook_test(self, ctx):
        """Test webhook functionality in current channel"""
        # Test webhook creation and message sending
        try:
            webhook = await self.bot.webhook_manager.get_webhook(ctx.channel)
            
            if webhook:
                await self.bot.webhook_manager.send_censored_message(
                    ctx.channel,
                    ctx.author,
                    "This is a test message sent via webhook! 🎉"
                )
                
                embed = create_success_embed("Webhook test successful! Check the message above.")
            else:
                embed = create_error_embed("Failed to create or access webhook. Check permissions.")
            
        except Exception as e:
            embed = create_error_embed(f"Webhook test failed: {str(e)}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="cleanup_webhooks", description="Clean up unused webhooks")
    @has_permissions(manage_webhooks=True)
    async def cleanup_webhooks(self, ctx):
        """Clean up unused webhooks created by the bot"""
        try:
            webhooks = await ctx.guild.webhooks()
            bot_webhooks = [w for w in webhooks if w.user == self.bot.user]
            
            deleted_count = 0
            for webhook in bot_webhooks:
                try:
                    await webhook.delete(reason="Cleanup command")
                    deleted_count += 1
                except:
                    pass
            
            # Clear webhook cache
            self.bot.webhook_manager.webhooks.clear()
            
            embed = create_success_embed(f"Cleaned up {deleted_count} webhook(s).")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = create_error_embed("I don't have permission to manage webhooks.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(f"An error occurred: {str(e)}")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ProfanityCommands(bot))
