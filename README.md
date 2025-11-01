# 🏁 Trackmania Exchange Browser

A modern, customizable overlay browser for **Trackmania Exchange** maps and mappacks. Search, download, and play maps directly from the game with an intuitive GUI interface.

## ✨ Features

- **🔍 Advanced Map Search** - Filter by name, author, environment, difficulty, length, and more
- **📦 Mappack Support** - Browse and manage official/custom mappacks with map selection
- **⭐ Favorites System** - Save favorite maps and mappacks with persistent JSON storage
- **🎮 Direct Launch** - Play maps directly from the browser (configurable hotkey overlay)
- **🖼️ Thumbnail Caching** - Auto-download and cache map/mappack preview images
- **⚙️ Fully Customizable** - `config.ini` based configuration with file browse dialogs
- **🌐 API v2 Support** - Full integration with Trackmania Exchange API v2
- **🔐 SSL Verification** - Configurable SSL settings for different network environments

## 📋 Requirements

- **Python** 3.9+
- **PySide6** - GUI Framework
- **requests** - HTTP client
- **keyboard** - Hotkey support
- **Trackmania** - Installed on your system (for launching maps)

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/trackmania-exchange-browser.git
cd trackmania-exchange-browser
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python tmx_browser_production.py
```

On first launch, the application will:
- Create `config.ini` with default settings
- Create `maps/` and `cache/` directories
- Set up favorites storage

## ⚙️ Configuration

Edit `config.ini` to customize:

```ini
[Paths]
trackmania_exe = C:\Program Files\Trackmania\Trackmania.exe
maps_directory = ./maps
cache_directory = ./cache

[API]
base_url = https://trackmania.exchange
timeout = 10
verify_ssl = true

[UI]
hotkey = ctrl+shift+l
window_width = 900
window_height = 700
maps_per_page = 25

[Behavior]
auto_cache_thumbnails = true
launch_hidden = true
```

Or use Settings tab in the application with file browse dialogs.

## 🎮 Usage

### Browsing Maps
1. Select **"Maps"** radio button
2. Enter search criteria (name, author, filters)
3. Choose sort order (Newest, Most Downloaded, etc.)
4. Click **"🔍 Search"**
5. Select a map and click **"⬇️ Download"** then **"▶️ Launch"**

### Browsing Mappacks
1. Select **"Mappacks"** radio button
2. Search for mappack or click **"🎮 Official Packs"**
3. Click **"🗺️ Show Maps in Mappack"** to see maps
4. Launch any map from the mappack

### Managing Favorites
1. Click **"⭐ Add to Favorites"** on any map/mappack
2. Go to **"⭐ Favorites"** tab
3. Click to select and **"▶️ Launch"**
   - For maps: Launches directly
   - For mappacks: Shows map list for selection

### Overlay Hotkey
- Default: `Ctrl+Shift+L` (customizable in config.ini)
- Toggles browser visibility while in-game
- Auto-hides when launching maps (configurable)

## 🔧 Advanced Features

### API Integration
- Full Trackmania Exchange API v2 support
- Automatic field mapping and response parsing
- Configurable timeout and SSL verification
- Support for maps and mappacks endpoints

### Search Options
- **Sort by**: Uploaded, Updated, Name, Awards, Difficulty, Length, Downloads, Rating
- **Filter by**: Environment (Stadium, Snow, Rally, Desert)
- **Difficulty**: Beginner to Expert+
- **Length**: 0-30s to 5+ minutes

### Thumbnail Handling
- Auto-cache with configurable directory
- Fallback "No image" display
- Support for map and mappack thumbnails
- Disable caching in config for offline use

## 🛠️ Development

### Code Structure
- `ConfigManager` - Configuration file handling
- `MapInfo` / `MappackInfo` - Data models
- Worker threads for async operations
- Qt-based GUI with responsive design

### Adding Features
1. Extend `MapInfo`/`MappackInfo` classes for new data
2. Add API parameters to search workers
3. Update UI tabs in `create_*_tab()` methods
4. Add config options to `ConfigManager`

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Trackmania.exe not found" | Update path in Settings tab or config.ini |
| Maps won't download | Check internet connection, verify API URL in config.ini |
| Hotkey not working | Ensure keyboard module has admin rights on Windows |
| SSL errors | Set `verify_ssl = false` in config.ini (not recommended) |

## 📝 License

MIT License - Feel free to fork and modify!

## 🤝 Contributing

Pull requests welcome! For major changes:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📧 Support

- **Issues**: Open GitHub issue with details
- **Suggestions**: Create discussion or issue with `[FEATURE]` tag
- **API Issues**: Check [Trackmania Exchange API Docs](https://api2.mania.exchange)

## 🙏 Credits

- **Trackmania Exchange** - Map hosting platform
- **PySide6** - Qt Python bindings
- **requests** - HTTP library
- **AI** - Entire community
---

**Made with ❤️ for the Trackmania community**

Latest Version: **4.1 (Production Ready)**
