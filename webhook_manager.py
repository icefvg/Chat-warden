import discord
import aiohttp
import asyncio
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class WebhookManager:
    """Manages webhooks for message spoofing"""
    
    def __init__(self, bot):
        self.bot = bot
        self.webhooks: Dict[int, discord.Webhook] = {}
        self.session = None
        self.webhook_cache_timeout = 3600  # 1 hour
        self.webhook_timestamps: Dict[int, float] = {}
    
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self.session
    
    async def get_webhook(self, channel: discord.TextChannel) -> Optional[discord.Webhook]:
        """Get or create webhook for channel"""
        current_time = asyncio.get_event_loop().time()
        
        # Check if cached webhook is still valid
        if channel.id in self.webhooks:
            webhook = self.webhooks[channel.id]
            
            # Check if webhook cache has expired
            if (channel.id in self.webhook_timestamps and 
                current_time - self.webhook_timestamps[channel.id] > self.webhook_cache_timeout):
                del self.webhooks[channel.id]
                del self.webhook_timestamps[channel.id]
            else:
                try:
                    # Test if webhook still exists
                    await webhook.fetch()
                    return webhook
                except (discord.NotFound, discord.HTTPException):
                    # Webhook was deleted, remove from cache
                    if channel.id in self.webhooks:
                        del self.webhooks[channel.id]
                    if channel.id in self.webhook_timestamps:
                        del self.webhook_timestamps[channel.id]
        
        # Check if bot has permission to create webhooks
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            logger.warning(f"Missing permission to create webhook in {channel.name}")
            return None
        
        # Look for existing webhook created by this bot
        try:
            existing_webhooks = await channel.webhooks()
            for webhook in existing_webhooks:
                if webhook.user == self.bot.user and "Censor Bot" in webhook.name:
                    self.webhooks[channel.id] = webhook
                    self.webhook_timestamps[channel.id] = current_time
                    return webhook
        except discord.Forbidden:
            logger.warning(f"Missing permission to list webhooks in {channel.name}")
            return None
        
        # Create new webhook
        try:
            webhook = await channel.create_webhook(
                name=f"Censor Bot - {channel.name}",
                avatar=await self._get_bot_avatar(),
                reason="Profanity filter webhook for message replacement"
            )
            self.webhooks[channel.id] = webhook
            self.webhook_timestamps[channel.id] = current_time
            logger.info(f"Created webhook for channel {channel.name}")
            return webhook
            
        except discord.Forbidden:
            logger.warning(f"Missing permission to create webhook in {channel.name}")
            return None
        except discord.HTTPException as e:
            logger.error(f"Failed to create webhook in {channel.name}: {e}")
            return None
    
    async def _get_bot_avatar(self) -> Optional[bytes]:
        """Get bot avatar for webhook"""
        try:
            if self.bot.user.avatar:
                return await self.bot.user.avatar.read()
        except:
            pass
        return None
    
    async def send_censored_message(
        self, 
        channel: discord.TextChannel, 
        author: discord.Member, 
        content: str,
        embeds: List[discord.Embed] = None,
        files: List[discord.File] = None,
        reference: discord.MessageReference = None
    ) -> bool:
        """Send censored message via webhook"""
        webhook = await self.get_webhook(channel)
        if not webhook:
            logger.warning(f"Could not get webhook for channel {channel.name}")
            return False
        
        try:
            # Get user avatar
            avatar_url = author.display_avatar.url
            
            # Prepare webhook parameters
            webhook_params = {
                'content': content[:2000] if content else None,  # Discord limit
                'username': author.display_name[:80],  # Discord limit
                'avatar_url': avatar_url,
                'wait': False,
                'allowed_mentions': discord.AllowedMentions.none()
            }
            
            # Add embeds if provided
            if embeds:
                webhook_params['embeds'] = embeds[:10]  # Discord limit
            
            # Add files if provided
            if files:
                webhook_params['files'] = files[:10]  # Discord limit
            
            # Add message reference for replies
            if reference:
                try:
                    # Get the referenced message
                    ref_message = await channel.fetch_message(reference.message_id)
                    if ref_message:
                        # Create a simple reply indicator
                        reply_content = f"↳ Replying to **{ref_message.author.display_name}**"
                        if webhook_params['content']:
                            webhook_params['content'] = f"{reply_content}\n{webhook_params['content']}"
                        else:
                            webhook_params['content'] = reply_content
                except:
                    pass  # Ignore if we can't fetch the referenced message
            
            # Send message via webhook
            message = await webhook.send(**webhook_params)
            
            # Log successful webhook usage
            logger.debug(f"Sent censored message via webhook in {channel.name}")
            return True
            
        except discord.HTTPException as e:
            logger.error(f"Failed to send webhook message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook message: {e}")
            return False
    
    async def send_embed_message(
        self,
        channel: discord.TextChannel,
        author: discord.Member,
        embed: discord.Embed
    ) -> bool:
        """Send an embed message via webhook"""
        return await self.send_censored_message(channel, author, None, embeds=[embed])
    
    async def cleanup_webhook(self, channel_id: int):
        """Remove webhook for channel"""
        if channel_id in self.webhooks:
            try:
                webhook = self.webhooks[channel_id]
                await webhook.delete(reason="Webhook cleanup")
                logger.info(f"Deleted webhook for channel ID {channel_id}")
            except Exception as e:
                logger.warning(f"Failed to delete webhook for channel ID {channel_id}: {e}")
            finally:
                if channel_id in self.webhooks:
                    del self.webhooks[channel_id]
                if channel_id in self.webhook_timestamps:
                    del self.webhook_timestamps[channel_id]
    
    async def cleanup_all_webhooks(self):
        """Clean up all webhooks"""
        for channel_id in list(self.webhooks.keys()):
            await self.cleanup_webhook(channel_id)
    
    async def cleanup_expired_webhooks(self):
        """Clean up expired webhook cache entries"""
        current_time = asyncio.get_event_loop().time()
        expired_channels = []
        
        for channel_id, timestamp in self.webhook_timestamps.items():
            if current_time - timestamp > self.webhook_cache_timeout:
                expired_channels.append(channel_id)
        
        for channel_id in expired_channels:
            if channel_id in self.webhooks:
                del self.webhooks[channel_id]
            if channel_id in self.webhook_timestamps:
                del self.webhook_timestamps[channel_id]
    
    async def get_webhook_count(self) -> int:
        """Get number of active webhooks"""
        return len(self.webhooks)
    
    async def verify_webhook(self, channel: discord.TextChannel) -> bool:
        """Verify that webhook exists and is functional"""
        webhook = await self.get_webhook(channel)
        if not webhook:
            return False
        
        try:
            await webhook.fetch()
            return True
        except:
            return False
    
    async def close(self):
        """Close the session and clean up"""
        if self.session and not self.session.closed:
            await self.session.close()
            
        # Clean up webhooks on shutdown if requested
        # Note: We don't auto-delete webhooks as they might be reused
        logger.info("Webhook manager closed")
