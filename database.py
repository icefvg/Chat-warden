import json
import asyncio
import os
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class Database:
    """Simple JSON-based database for storing bot data"""
    
    def __init__(self):
        self.data_dir = "data"
        self.guild_settings_file = "data/guild_settings.json"
        self.user_data_file = "data/user_data.json"
        self.mod_logs_file = "data/mod_logs.json"
        self.warnings_file = "data/warnings.json"
        self.infractions_file = "data/infractions.json"
        
        # Thread lock for file operations
        self._lock = threading.Lock()
        
        self._ensure_data_directory()
        self._load_data()
        
        # Auto-cleanup task
        self._schedule_cleanup()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _load_data(self):
        """Load all data from files"""
        self.guild_settings = self._load_json(self.guild_settings_file, {})
        self.user_data = self._load_json(self.user_data_file, {})
        self.mod_logs = self._load_json(self.mod_logs_file, {})
        self.warnings = self._load_json(self.warnings_file, {})
        self.infractions = self._load_json(self.infractions_file, {})
    
    def _load_json(self, filename: str, default: Any) -> Any:
        """Load JSON file with fallback"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default
    
    def _save_json(self, filename: str, data: Any):
        """Save data to JSON file with thread safety"""
        with self._lock:
            try:
                # Create backup
                backup_filename = f"{filename}.backup"
                if os.path.exists(filename):
                    os.rename(filename, backup_filename)
                
                # Write new data
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Remove backup on success
                if os.path.exists(backup_filename):
                    os.remove(backup_filename)
                    
            except Exception as e:
                print(f"Error saving {filename}: {e}")
                # Restore backup if it exists
                backup_filename = f"{filename}.backup"
                if os.path.exists(backup_filename):
                    os.rename(backup_filename, filename)
    
    async def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get settings for a guild"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.guild_settings:
            from config import Config
            self.guild_settings[guild_id_str] = Config.get_default_guild_settings()
            self._save_json(self.guild_settings_file, self.guild_settings)
        
        return self.guild_settings[guild_id_str].copy()
    
    async def update_guild_settings(self, guild_id: int, settings: Dict[str, Any]):
        """Update guild settings"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.guild_settings:
            from config import Config
            self.guild_settings[guild_id_str] = Config.get_default_guild_settings()
        
        self.guild_settings[guild_id_str].update(settings)
        self._save_json(self.guild_settings_file, self.guild_settings)
    
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        """Add a warning to a user"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str not in self.warnings:
            self.warnings[guild_id_str] = {}
        
        if user_id_str not in self.warnings[guild_id_str]:
            self.warnings[guild_id_str][user_id_str] = []
        
        warning_id = len(self.warnings[guild_id_str][user_id_str]) + 1
        warning = {
            'id': warning_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat(),
            'active': True
        }
        
        self.warnings[guild_id_str][user_id_str].append(warning)
        self._save_json(self.warnings_file, self.warnings)
        
        return warning_id
    
    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict]:
        """Get all active warnings for a user"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        warnings = self.warnings.get(guild_id_str, {}).get(user_id_str, [])
        return [w for w in warnings if w.get('active', True)]
    
    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Clear all warnings for a user"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str in self.warnings and user_id_str in self.warnings[guild_id_str]:
            warnings = self.warnings[guild_id_str][user_id_str]
            active_count = sum(1 for w in warnings if w.get('active', True))
            
            # Mark all warnings as inactive instead of deleting
            for warning in warnings:
                warning['active'] = False
                warning['cleared_at'] = datetime.utcnow().isoformat()
            
            self._save_json(self.warnings_file, self.warnings)
            return active_count
        
        return 0
    
    async def remove_warning(self, guild_id: int, user_id: int, warning_id: int) -> bool:
        """Remove a specific warning"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str in self.warnings and user_id_str in self.warnings[guild_id_str]:
            warnings = self.warnings[guild_id_str][user_id_str]
            for warning in warnings:
                if warning['id'] == warning_id and warning.get('active', True):
                    warning['active'] = False
                    warning['removed_at'] = datetime.utcnow().isoformat()
                    self._save_json(self.warnings_file, self.warnings)
                    return True
        
        return False
    
    async def add_mod_log(self, guild_id: int, action: str, user_id: int, moderator_id: int, reason: str = None, duration: str = None):
        """Add a moderation log entry"""
        guild_id_str = str(guild_id)
        
        if guild_id_str not in self.mod_logs:
            self.mod_logs[guild_id_str] = []
        
        log_entry = {
            'id': len(self.mod_logs[guild_id_str]) + 1,
            'action': action,
            'user_id': user_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.mod_logs[guild_id_str].append(log_entry)
        self._save_json(self.mod_logs_file, self.mod_logs)
        
        return log_entry['id']
    
    async def get_mod_logs(self, guild_id: int, limit: int = 50, user_id: int = None) -> List[Dict]:
        """Get recent moderation logs"""
        guild_id_str = str(guild_id)
        logs = self.mod_logs.get(guild_id_str, [])
        
        if user_id:
            logs = [log for log in logs if log['user_id'] == user_id]
        
        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return logs[:limit] if logs else []
    
    async def get_user_infractions(self, guild_id: int, user_id: int) -> Dict[str, int]:
        """Get user infraction counts"""
        guild_id_str = str(guild_id)
        
        # Count from mod logs
        logs = self.mod_logs.get(guild_id_str, [])
        infractions = {
            'warnings': 0,
            'kicks': 0,
            'bans': 0,
            'mutes': 0,
            'unbans': 0,
            'unmutes': 0
        }
        
        for log in logs:
            if log['user_id'] == user_id:
                action = log['action'].lower()
                if action in infractions:
                    infractions[action] += 1
                elif action == 'warn':
                    infractions['warnings'] += 1
                elif action in ['timeout', 'tempmute']:
                    infractions['mutes'] += 1
        
        # Add current active warnings
        warnings = await self.get_warnings(guild_id, user_id)
        infractions['active_warnings'] = len(warnings)
        
        return infractions
    
    async def add_infraction(self, guild_id: int, user_id: int, infraction_type: str, moderator_id: int, reason: str = None, duration: str = None):
        """Add an infraction record"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str not in self.infractions:
            self.infractions[guild_id_str] = {}
        
        if user_id_str not in self.infractions[guild_id_str]:
            self.infractions[guild_id_str][user_id_str] = []
        
        infraction = {
            'id': len(self.infractions[guild_id_str][user_id_str]) + 1,
            'type': infraction_type,
            'moderator_id': moderator_id,
            'reason': reason,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat(),
            'active': True
        }
        
        self.infractions[guild_id_str][user_id_str].append(infraction)
        self._save_json(self.infractions_file, self.infractions)
        
        return infraction['id']
    
    async def get_infractions(self, guild_id: int, user_id: int, active_only: bool = True) -> List[Dict]:
        """Get infractions for a user"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        infractions = self.infractions.get(guild_id_str, {}).get(user_id_str, [])
        
        if active_only:
            infractions = [i for i in infractions if i.get('active', True)]
        
        return infractions
    
    async def remove_infraction(self, guild_id: int, user_id: int, infraction_id: int) -> bool:
        """Remove a specific infraction"""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str in self.infractions and user_id_str in self.infractions[guild_id_str]:
            infractions = self.infractions[guild_id_str][user_id_str]
            for infraction in infractions:
                if infraction['id'] == infraction_id and infraction.get('active', True):
                    infraction['active'] = False
                    infraction['removed_at'] = datetime.utcnow().isoformat()
                    self._save_json(self.infractions_file, self.infractions)
                    return True
        
        return False
    
    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get user data across all guilds"""
        user_id_str = str(user_id)
        return self.user_data.get(user_id_str, {})
    
    async def update_user_data(self, user_id: int, data: Dict[str, Any]):
        """Update user data"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_data:
            self.user_data[user_id_str] = {}
        
        self.user_data[user_id_str].update(data)
        self._save_json(self.user_data_file, self.user_data)
    
    def _schedule_cleanup(self):
        """Schedule periodic cleanup of old data"""
        # This would be better implemented with a proper task scheduler
        # For now, we'll clean up when certain operations are performed
        pass
    
    async def cleanup_old_logs(self, days: int = 30):
        """Clean up old moderation logs"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        
        for guild_id in self.mod_logs:
            original_count = len(self.mod_logs[guild_id])
            self.mod_logs[guild_id] = [
                log for log in self.mod_logs[guild_id]
                if log['timestamp'] > cutoff_str
            ]
            
            removed_count = original_count - len(self.mod_logs[guild_id])
            if removed_count > 0:
                print(f"Cleaned up {removed_count} old logs for guild {guild_id}")
        
        self._save_json(self.mod_logs_file, self.mod_logs)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        total_guilds = len(self.guild_settings)
        total_users = len(self.user_data)
        total_warnings = sum(
            len(user_warnings) 
            for guild_warnings in self.warnings.values()
            for user_warnings in guild_warnings.values()
        )
        total_logs = sum(len(guild_logs) for guild_logs in self.mod_logs.values())
        
        return {
            'total_guilds': total_guilds,
            'total_users': total_users,
            'total_warnings': total_warnings,
            'total_mod_logs': total_logs,
            'total_infractions': sum(
                len(user_infractions)
                for guild_infractions in self.infractions.values()
                for user_infractions in guild_infractions.values()
            )
        }
