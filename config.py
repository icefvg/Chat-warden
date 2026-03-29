import os
import json
from typing import Dict, List, Any

class Config:
    """Configuration management for the Discord bot"""
    
    def __init__(self):
        self.cooldown_time = 2  # seconds
        self.max_message_length = 2000
        self.default_prefix = ['!', '?', '/']
        self.max_warnings = 3
        self.auto_ban_threshold = 5
        
        # Load configuration from environment variables
        self.load_env_config()
    
    def load_env_config(self):
        """Load configuration from environment variables"""
        self.cooldown_time = int(os.getenv('COOLDOWN_TIME', '2'))
        self.max_message_length = int(os.getenv('MAX_MESSAGE_LENGTH', '2000'))
        self.max_warnings = int(os.getenv('MAX_WARNINGS', '3'))
        self.auto_ban_threshold = int(os.getenv('AUTO_BAN_THRESHOLD', '5'))
        
    @staticmethod
    def get_default_guild_settings() -> Dict[str, Any]:
        """Get default settings for a new guild"""
        return {
            'profanity_enabled': True,
            'enabled_channels': [],  # Empty means all channels
            'log_channel': None,
            'announcement_channel': None,
            'prefix': ['!', '?', '/'],
            'auto_role': None,
            'welcome_channel': None,
            'mute_role': None,
            'anti_spam_enabled': False,
            'anti_raid_enabled': False,
            'anti_link_enabled': False,
            'max_warns': 3,
            'auto_ban_enabled': False,
            'raid_detection_threshold': 5,
            'spam_detection_count': 5,
            'spam_detection_time': 10,
            'link_whitelist': [],
            'automod_actions': {
                'spam': 'warn',
                'raid': 'kick',
                'links': 'delete'
            }
        }
    
    @staticmethod
    def get_required_permissions() -> Dict[str, List[str]]:
        """Get required permissions for different command categories"""
        return {
            'basic_mod': [
                'kick_members',
                'ban_members', 
                'manage_messages',
                'moderate_members'
            ],
            'advanced_mod': [
                'manage_channels',
                'manage_roles',
                'manage_guild'
            ],
            'webhook': [
                'manage_webhooks',
                'manage_messages'
            ],
            'admin': [
                'administrator'
            ]
        }
    
    @staticmethod
    def get_embed_colors() -> Dict[str, int]:
        """Get standard embed colors"""
        return {
            'success': 0x00ff00,    # Green
            'error': 0xff0000,      # Red  
            'warning': 0xffaa00,    # Orange
            'info': 0x0099ff,       # Blue
            'neutral': 0x36393f     # Dark gray
        }
