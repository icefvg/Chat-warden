# Discord Moderation Bot

## Overview

This is a comprehensive Discord moderation bot built with Python using discord.py. The bot features advanced profanity filtering with webhook message replacement, a complete moderation command suite, and administrative controls for server management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: discord.py for Discord API interaction
- **Language**: Python 3.8+
- **Architecture Pattern**: Cog-based modular design with separate components for different functionalities
- **Data Storage**: JSON-based file system (transitional, ready for database upgrade)
- **Async Processing**: Full async/await pattern for Discord operations

### Core Components
- **Main Bot Class**: `DiscordModerationBot` - Central bot instance with intents and component initialization
- **Cogs System**: Modular command organization (admin, moderation, profanity, utility, help)
- **Configuration Management**: Environment-based config with guild-specific settings
- **Database Layer**: JSON file-based storage with thread-safe operations

## Key Components

### 1. Profanity Filter System
- **Advanced Detection**: Handles obfuscated words, leetspeak, unicode bypasses
- **Smart Replacement**: Uses webhook system to replace messages while preserving user identity
- **Customizable Dictionary**: Tiered word lists (mild, moderate, severe, slurs, custom)
- **Bypass Protection**: Multiple pattern detection including separators and character substitution

### 2. Webhook Management
- **Message Spoofing**: Replaces filtered messages maintaining original user appearance
- **Caching System**: Webhook caching with timeout and validation
- **Session Management**: aiohttp session handling for webhook operations
- **Error Handling**: Comprehensive fallback for webhook failures

### 3. Moderation Commands
- **Basic Actions**: kick, ban, unban, warn, mute, unmute
- **Message Management**: clear, purge, slowmode
- **Channel Control**: lock, unlock, nuke
- **Advanced Features**: timed actions, infraction tracking, auto-moderation

### 4. Administrative Controls
- **Guild Settings**: Per-server configuration storage
- **Channel Management**: Specific channel targeting for filters
- **Role Management**: Automated role assignment and moderation
- **Logging System**: Comprehensive action logging

## Data Flow

### Message Processing Flow
1. Message received → Profanity filter check
2. If profanity detected → Generate webhook → Send replacement → Delete original
3. Log action if enabled → Update statistics

### Moderation Action Flow
1. Command received → Permission validation
2. Target validation → Action execution
3. Logging → Notification (DM + channel)
4. Database update → Infraction tracking

### Configuration Flow
1. Admin command → Validation → Database update
2. Real-time application → Confirmation response

## External Dependencies

### Core Libraries
- **discord.py**: Discord API interactions
- **aiohttp**: Async HTTP client for webhooks
- **fuzzywuzzy**: Fuzzy string matching for profanity detection

### Data Processing
- **unicodedata**: Unicode normalization for text processing
- **re**: Regular expression pattern matching
- **json**: Data serialization and storage

### System Libraries
- **asyncio**: Asynchronous programming
- **threading**: Thread-safe file operations
- **logging**: Comprehensive logging system
- **datetime**: Time-based operations and scheduling

## Deployment Strategy

### File Structure
- **Modular Design**: Separate cogs for different command categories
- **Data Directory**: JSON files for persistent storage in `/data/` folder
- **Utility Layer**: Helper functions in `/utils/` for common operations
- **Configuration**: Environment variable support with defaults

### Storage Architecture
- **Current**: JSON file-based storage with thread safety
- **Migration Ready**: Database abstraction layer prepared for PostgreSQL integration
- **Backup Strategy**: File-based storage allows easy backup and version control

### Scalability Considerations
- **Cog System**: Easy addition of new features without core modifications
- **Database Abstraction**: Ready for migration to proper database (PostgreSQL)
- **Async Design**: Handles multiple servers and high message volumes
- **Caching Layer**: Webhook and settings caching for performance

### Security Features
- **Permission Validation**: Comprehensive permission checking
- **Rate Limiting**: Cooldown systems to prevent abuse
- **Input Sanitization**: Safe handling of user input and commands
- **Role Hierarchy**: Proper role-based access control

### Monitoring and Logging
- **File Logging**: bot.log for persistent logging
- **Console Output**: Real-time monitoring capability
- **Moderation Logs**: Per-guild action tracking
- **Error Handling**: Comprehensive try-catch blocks with logging

The architecture is designed for easy maintenance, feature expansion, and eventual database migration while providing robust moderation capabilities and advanced profanity filtering.