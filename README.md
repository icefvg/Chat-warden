# Discord Moderation Bot

A comprehensive Discord moderation bot with advanced profanity filtering, webhook message replacement, and full moderation command suite.

## Features

### 🔍 Advanced Profanity Filter
- Real-time message monitoring across all channels
- Smart detection of obfuscated words (f*ck, f.u.c.k, f__k, etc.)
- Leetspeak and unicode bypass protection
- Webhook message replacement preserving user identity
- Customizable word dictionary with easy management
- Channel-specific activation controls

### ⚖️ Complete Moderation Suite
- **Basic Commands**: kick, ban, unban, warn, mute, unmute
- **Message Management**: clear, purge, slowmode
- **Channel Control**: lock, unlock, nuke
- **Advanced Features**: infractions tracking, auto-ban on warnings
- **Logging**: Comprehensive moderation logs

### 🛠️ Administrative Controls
- Toggle profanity filtering per server
- Set specific channels for filtering
- Add/remove words from filter
- Manage word replacements
- Configure auto-moderation settings

## Setup

### Prerequisites
- Python 3.8+
- Discord bot token
- Required permissions: Manage Messages, Manage Webhooks, Kick Members, Ban Members, Moderate Members

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd discord-moderation-bot
