# 🤖 Media Download Bot

A powerful Discord bot for downloading and organizing media files from channels with smart categorization and Top.gg vote verification.

## ✨ Features

- 🎯 **Interactive Download Menu** - User-friendly button-based interface
- 🧠 **Smart File Organization** - Automatic categorization by content type
- 🗳️ **Top.gg Vote System** - Encourages community support
- 📊 **Progress Tracking** - Real-time download progress with visual indicators
- 🔄 **Resource Monitoring** - Automatic pausing when system resources are low
- 📁 **Multiple Download Options** - By date, type, or recent messages
- ☁️ **External Hosting** - Large files automatically uploaded to Catbox
- 🎨 **Beautiful Embeds** - Professional Discord embeds with progress bars

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Top.gg API Token (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/media-download-bot.git
   cd media-download-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your tokens
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Discord Bot Token | ✅ Yes |
| `TOP_GG_TOKEN` | Top.gg API Token | ❌ No |
| `LOGS_CHANNEL_ID` | Logs Channel ID | ❌ No |
| `WEBHOOK_URL` | Webhook URL | ❌ No |
| `GOFILE_TOKEN` | GoFile Token | ❌ No |

### Getting Your Tokens

#### Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section
4. Copy the token

#### Top.gg API Token
1. Go to [Top.gg](https://top.gg/bot/YOUR_BOT_ID)
2. Click "Edit Bot"
3. Go to "Webhooks" section
4. Copy your Authorization token

## 🎮 Usage

### Commands

- `/download` - Open interactive download menu

### Download Options

- **📥 Download All** - Download all media from the channel
- **📅 By Date** - Download media from specific date ranges
- **🎨 By Type** - Download only images or videos
- **🔄 Recent** - Download from last X messages

### Vote System

Users must vote on Top.gg to access download features:
- Vote is valid for 12 hours
- Automatic verification after voting
- Seamless download experience

## 🏗️ Project Structure

```
media-download-bot/
├── bot.py                 # Main bot file
├── config.py              # Configuration settings
├── cogs/                  # Bot commands
│   ├── download.py        # Download functionality
│   ├── help.py           # Help command
│   └── stats.py          # Statistics
├── utils/                 # Utility modules
│   ├── interactive_menu.py # Interactive menus
│   ├── topgg_checker.py   # Vote verification
│   ├── smart_classifier.py # File organization
│   └── catbox.py         # External hosting
├── requirements.txt       # Dependencies
├── env.example           # Environment template
└── README.md             # This file
```

## 🔧 Development

### Setting up Development Environment

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure local environment**
   ```bash
   cp env.example .env
   # Add your tokens to .env
   ```

### Testing

```bash
# Check environment variables
python check_env.py

# Test Top.gg API connection
python test_topgg.py
```

## 📚 Documentation

- [Environment Setup Guide](ENV_SETUP.md) - Complete environment configuration
- [GitHub Setup Guide](GITHUB_SETUP.md) - Quick GitHub Secrets setup
- [Top.gg Integration](TOPGG_SETUP.md) - Vote system documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues:

1. Check the [documentation](ENV_SETUP.md)
2. Verify your environment variables
3. Check the bot logs
4. Open an issue on GitHub

## 🙏 Acknowledgments

- [Discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [Top.gg](https://top.gg) - Bot listing and voting platform
- [Catbox](https://catbox.moe) - File hosting service

---

**Made with ❤️ for the Discord community**