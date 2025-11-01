import sys
import os
import json
import requests
import subprocess
from datetime import datetime
from typing import Optional, List, Dict
import traceback
import configparser
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout,
    QComboBox, QSpinBox, QTextEdit, QTabWidget, QScrollArea,
    QFrame, QGridLayout, QCheckBox, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage
import keyboard

# --- CONFIGURATION MANAGER ---
class ConfigManager:
    def __init__(self):
        self.config_file = "config.ini"
        self.config = configparser.ConfigParser()

        if not os.path.exists(self.config_file):
            self.create_default_config()
        else:
            self.config.read(self.config_file)

    def create_default_config(self):
        """Create default configuration file"""
        self.config['Paths'] = {
            'trackmania_exe': 'C:\\Program Files\\Trackmania\\Trackmania.exe',
            'maps_directory': './maps',
            'cache_directory': './cache',
            'favorites_file': './favorites.json'
        }

        self.config['API'] = {
            'base_url': 'https://trackmania.exchange',
            'timeout': '10',
            'verify_ssl': 'true'
        }

        self.config['UI'] = {
            'hotkey': 'ctrl+shift+l',
            'window_width': '900',
            'window_height': '700',
            'maps_per_page': '25',
            'theme': 'dark'
        }

        self.config['Behavior'] = {
            'auto_cache_thumbnails': 'true',
            'remember_last_search': 'true',
            'launch_hidden': 'true'
        }

        self.save_config()

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            print(f"[CONFIG] Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")

    def get(self, section: str, key: str, fallback=None):
        """Get config value"""
        try:
            return self.config.get(section, key)
        except:
            return fallback

    def set(self, section: str, key: str, value: str):
        """Set config value"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)
        self.save_config()

# Initialize config
config_mgr = ConfigManager()

# Read configuration
TRACKMANIA_EXE = config_mgr.get('Paths', 'trackmania_exe')
MAPS_DIR = config_mgr.get('Paths', 'maps_directory')
CACHE_DIR = config_mgr.get('Paths', 'cache_directory')
FAVORITES_FILE = config_mgr.get('Paths', 'favorites_file')

API_BASE = config_mgr.get('API', 'base_url')
API_TIMEOUT = int(config_mgr.get('API', 'timeout', '10'))
VERIFY_SSL = config_mgr.get('API', 'verify_ssl', 'true').lower() == 'true'

DEFAULT_HOTKEY = config_mgr.get('UI', 'hotkey')
WINDOW_WIDTH = int(config_mgr.get('UI', 'window_width', '900'))
WINDOW_HEIGHT = int(config_mgr.get('UI', 'window_height', '700'))
DEFAULT_LIMIT = int(config_mgr.get('UI', 'maps_per_page', '25'))

AUTO_CACHE = config_mgr.get('Behavior', 'auto_cache_thumbnails', 'true').lower() == 'true'
LAUNCH_HIDDEN = config_mgr.get('Behavior', 'launch_hidden', 'true').lower() == 'true'

# Create directories
os.makedirs(MAPS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# API URLs
API_SEARCH = f"{API_BASE}/api/maps"
API_MAP_INFO = f"{API_BASE}/api/maps"
API_DOWNLOAD = f"{API_BASE}/maps/download"
API_THUMBNAIL = f"{API_BASE}/mapthumb"
API_MAPPACK_SEARCH = f"{API_BASE}/api/mappacks"
API_MAPPACK_THUMBNAIL = f"{API_BASE}/mappackthumb"

print(f"[CONFIG] Loaded from {config_mgr.config_file}")
print(f"[CONFIG] Trackmania EXE: {TRACKMANIA_EXE}")
print(f"[CONFIG] Maps Directory: {MAPS_DIR}")
print(f"[CONFIG] API Base: {API_BASE}")

# Common fields
COMMON_FIELDS = [
    "MapId", "Name", "GbxMapName", "Uploader.UserId", "Uploader.Name",
    "Environment", "Difficulty", "Length", "Vehicle", "MapType",
    "CommentCount", "DownloadCount", "ReplayCount", "AwardCount",
    "UploadedAt", "UpdatedAt", "ActivityAt", "HasThumbnail",
    "HasImages", "TrackValue", "OnlineWR", "TitlePack",
    "Style", "Mood", "Routes", "Type", "Authors", "Tags"
]

MAPPACK_FIELDS = [
    "MappackId", "Name", "Owner.UserId", "Owner.Name", "Description", "DownloadCount"
]

# --- Favorites Config ---
class Config:
    def __init__(self):
        self.favorites = self.load_favorites()
    
    def load_favorites(self) -> Dict:
        """Load favorites (maps and mappacks) with names"""
        try:
            if os.path.exists(FAVORITES_FILE):
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        "maps": data.get("maps", []),
                        "mappacks": data.get("mappacks", [])
                    }
        except Exception as e:
            print(f"[ERROR] Favorites loading error: {e}")
        return {"maps": [], "mappacks": []}
    
    def save_favorites(self, favorites: Dict):
        """Save favorites to file"""
        try:
            with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
                json.dump(favorites, f, indent=2, ensure_ascii=False)
            print("[CONFIG] Favorites saved")
        except Exception as e:
            print(f"[ERROR] Favorites saving error: {e}")

# --- MapInfo class ---
class MapInfo:
    def __init__(self, json_data):
        self.TrackID = json_data.get("MapId")
        self.Name = json_data.get("Name", "")
        self.GbxMapName = json_data.get("GbxMapName", "")

        uploader = json_data.get("Uploader", {})
        self.Username = uploader.get("Name", "") if isinstance(uploader, dict) else ""
        self.UserID = uploader.get("UserId") if isinstance(uploader, dict) else None

        authors = json_data.get("Authors", [])
        self.AuthorLogin = ""
        if authors and len(authors) > 0:
            author_user = authors[0].get("User", {})
            if isinstance(author_user, dict):
                self.AuthorLogin = author_user.get("Name", "")

        self.EnvironmentName = self.get_enum_name(json_data.get("Environment"), "environment")
        self.DifficultyName = self.get_enum_name(json_data.get("Difficulty"), "difficulty")
        self.VehicleName = json_data.get("VehicleName", "")
        self.MapType = json_data.get("MapType", "")
        self.TitlePack = json_data.get("TitlePack", "")
        self.Mood = json_data.get("Mood", "")

        self.Length = json_data.get("Length", 0)
        self.LengthName = self.get_length_name(self.Length)

        self.AwardCount = json_data.get("AwardCount", 0)
        self.CommentCount = json_data.get("CommentCount", 0)
        self.DownloadCount = json_data.get("DownloadCount", 0)
        self.ReplayCount = json_data.get("ReplayCount", 0)
        self.TrackValue = json_data.get("TrackValue", 0)

        online_wr = json_data.get("OnlineWR", {})
        if isinstance(online_wr, dict):
            self.ReplayWRTime = online_wr.get("RecordTime", 0)
            wr_user = online_wr.get("User", {})
            self.ReplayWRUsername = wr_user.get("Name", "") if isinstance(wr_user, dict) else ""
        else:
            self.ReplayWRTime = 0
            self.ReplayWRUsername = ""

        self.UploadedAt = json_data.get("UploadedAt", "")
        self.UpdatedAt = json_data.get("UpdatedAt", "")
        self.HasThumbnail = json_data.get("HasThumbnail", False)
        self.HasImages = json_data.get("HasImages", False)
        self.Downloadable = True

        print(f"[MAP] Loaded: {self.Name} (ID: {self.TrackID})")

    def get_enum_name(self, value, enum_type):
        enum_map = {
            "environment": {0: "Stadium", 1: "Snow", 2: "Rally", 3: "Desert"},
            "difficulty": {0: "Beginner", 1: "Intermediate", 2: "Advanced", 3: "Expert", 4: "Expert+"}
        }
        if enum_type in enum_map and value in enum_map[enum_type]:
            return enum_map[enum_type][value]
        return str(value)

    def get_length_name(self, length_ms):
        if length_ms == 0:
            return "0-30 sec"
        seconds = length_ms // 1000
        if seconds < 30:
            return "0-30 sec"
        elif seconds < 60:
            return "30-60 sec"
        elif seconds < 120:
            return "1-2 min"
        elif seconds < 300:
            return "2-5 min"
        else:
            return "5+ min"

    def format_time(self, ms: int) -> str:
        if ms == 0:
            return "---"
        seconds = ms // 1000
        milliseconds = ms % 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def get_info_text(self) -> str:
        info = f"📋 {self.Name}\n"
        info += f"🆔 ID: {self.TrackID}\n"
        info += f"👤 Author: {self.Username}\n"
        info += f"🏆 Environment: {self.EnvironmentName}\n"
        info += f"⏱️ Length: {self.format_time(self.Length)}\n"

        if self.ReplayWRTime and self.ReplayWRTime > 0:
            info += f"🏅 World Record: {self.format_time(self.ReplayWRTime)} by {self.ReplayWRUsername}\n"

        info += f"📏 Length: {self.LengthName}\n"
        info += f"⚡ Difficulty: {self.DifficultyName}\n"
        info += f"⭐ Awards: {self.AwardCount}\n"
        info += f"💬 Comments: {self.CommentCount}\n"
        info += f"⬇️ Downloads: {self.DownloadCount}\n"
        info += f"📊 Value: {self.TrackValue}\n"
        info += f"📤 Uploaded: {self.UploadedAt[:10]}\n"

        return info

# --- MappackInfo class ---
class MappackInfo:
    def __init__(self, json_data):
        self.ID = json_data.get("MappackId")
        self.Name = json_data.get("Name", "")

        owner = json_data.get("Owner", {})
        self.Username = owner.get("Name", "") if isinstance(owner, dict) else ""

        self.TrackCount = json_data.get("TrackCount", 0)
        self.Description = json_data.get("Description", "")
        self.DownloadCount = json_data.get("DownloadCount", 0)

        print(f"[MAPPACK] Loaded: {self.Name} (ID: {self.ID}, Maps: {self.TrackCount})")

    def get_info_text(self) -> str:
        info = f"📦 {self.Name}\n"
        info += f"🆔 ID: {self.ID}\n"
        info += f"👤 Author: {self.Username}\n"
        info += f"🗺️ Map Count: {self.TrackCount}\n"
        info += f"⬇️ Downloads: {self.DownloadCount}\n"

        if self.Description:
            info += f"\n💭 Description:\n{self.Description}\n"

        return info

# --- Workers ---
class MapInfoWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, map_id: int):
        super().__init__()
        self.map_id = map_id

    def run(self):
        try:
            params = {
                "id": self.map_id,
                "fields": ','.join(COMMON_FIELDS)
            }

            print(f"[MAP_INFO] Fetching map ID: {self.map_id}")
            response = requests.get(API_MAP_INFO, params=params, timeout=API_TIMEOUT, verify=VERIFY_SSL)
            print(f"[MAP_INFO] Status: {response.status_code}")
            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict) and "Results" in data and len(data["Results"]) > 0:
                map_info = MapInfo(data["Results"][0])
                self.finished.emit(map_info)
            else:
                self.error.emit("Map not found")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            self.error.emit(error_msg)

class SearchWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, params: Dict):
        super().__init__()
        self.params = params

    def run(self):
        try:
            self.params['fields'] = ','.join(COMMON_FIELDS)

            print(f"[SEARCH] Parameters: {self.params}")
            response = requests.get(API_SEARCH, params=self.params, timeout=API_TIMEOUT, verify=VERIFY_SSL)

            print(f"[SEARCH] Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "Results" in data:
                maps = [MapInfo(m) for m in data["Results"]]
                print(f"[SEARCH] Found {len(maps)} maps")
                self.finished.emit(maps)
            else:
                self.finished.emit([])

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            self.error.emit(error_msg)

class DownloadWorker(QThread):
    finished = Signal(str)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, map_id: int):
        super().__init__()
        self.map_id = map_id

    def run(self):
        url = f"{API_DOWNLOAD}/{self.map_id}"
        map_file = os.path.join(MAPS_DIR, f"{self.map_id}.Map.Gbx")

        try:
            print(f"[DOWNLOAD] Downloading map {self.map_id}")
            response = requests.get(url, stream=True, timeout=30, verify=VERIFY_SSL)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(map_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)

            print(f"[DOWNLOAD] Complete: {map_file}")
            self.finished.emit(map_file)
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            self.error.emit(error_msg)

class MappackSearchWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, params: Dict):
        super().__init__()
        self.params = params

    def run(self):
        try:
            self.params['fields'] = ','.join(MAPPACK_FIELDS)

            print(f"[MAPPACK_SEARCH] Parameters: {self.params}")
            response = requests.get(API_MAPPACK_SEARCH, params=self.params, timeout=API_TIMEOUT, verify=VERIFY_SSL)

            print(f"[MAPPACK_SEARCH] Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "Results" in data:
                mappacks = [MappackInfo(m) for m in data["Results"]]
                print(f"[MAPPACK_SEARCH] Found {len(mappacks)} mappacks")
                self.finished.emit(mappacks)
            else:
                self.finished.emit([])

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            self.error.emit(error_msg)

class MappackMapsWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, mappack_id: int):
        super().__init__()
        self.mappack_id = mappack_id

    def run(self):
        try:
            params = {
                "mappackid": self.mappack_id,
                "fields": ','.join(COMMON_FIELDS),
                "count": 100
            }

            print(f"[MAPPACK_MAPS] Loading maps from mappack {self.mappack_id}")
            response = requests.get(API_SEARCH, params=params, timeout=API_TIMEOUT, verify=VERIFY_SSL)

            print(f"[MAPPACK_MAPS] Status: {response.status_code}")
            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict) and "Results" in data:
                maps = [MapInfo(m) for m in data["Results"]]
                print(f"[MAPPACK_MAPS] Found {len(maps)} maps in mappack")
                self.finished.emit(maps)
            else:
                self.finished.emit([])

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            self.error.emit(error_msg)

# --- Main window ---
class TrackmaniaExchangeBrowser(QWidget):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.current_maps: List[MapInfo] = []
        self.selected_map: Optional[MapInfo] = None
        self.current_mappacks: List[MappackInfo] = []
        self.selected_mappack: Optional[MappackInfo] = None
        self.mappack_maps: List[MapInfo] = []
        self.favorites: Dict = self.config.favorites  # ZMIANA: teraz dict
        
        print("[INIT] Starting browser")
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.setWindowTitle("Trackmania Exchange Browser")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 5, 5, 5)
        title_label = QLabel("🏁 Trackmania Exchange Browser")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.clicked.connect(self.hide)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close_application)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(minimize_btn)
        title_layout.addWidget(close_btn)
        title_widget.setLayout(title_layout)
        main_layout.addWidget(title_widget)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_browse_tab(), "📚 Browse")
        self.tabs.addTab(self.create_favorites_tab(), "⭐ Favorites")
        self.tabs.addTab(self.create_settings_tab(), "⚙️ Settings")

        main_layout.addWidget(self.tabs)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def create_browse_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Search:"))

        self.search_type_group = QButtonGroup()
        self.map_radio = QRadioButton("Maps")
        self.mappack_radio = QRadioButton("Mappacks")
        self.map_radio.setChecked(True)
        self.search_type_group.addButton(self.map_radio, 0)
        self.search_type_group.addButton(self.mappack_radio, 1)
        self.map_radio.toggled.connect(self.on_search_type_changed)

        type_layout.addWidget(self.map_radio)
        type_layout.addWidget(self.mappack_radio)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        self.map_filters_frame = QFrame()
        self.map_filters_frame.setFrameStyle(QFrame.StyledPanel)
        map_filters_layout = QGridLayout()

        map_filters_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Part of name...")
        map_filters_layout.addWidget(self.name_input, 0, 1)

        map_filters_layout.addWidget(QLabel("Author:"), 0, 2)
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Author name...")
        map_filters_layout.addWidget(self.author_input, 0, 3)

        map_filters_layout.addWidget(QLabel("Sort by:"), 1, 0)
        self.sort_combo = QComboBox()
        self.sort_options = {
            "Uploaded (Newest)": 6,
            "Uploaded (Oldest)": 5,
            "Updated (Newest)": 8,
            "Name (A-Z)": 1,
            "Name (Z-A)": 2,
            "Awards (Most)": 12,
            "Awards (Least)": 11,
            "Difficulty (Hardest)": 16,
            "Difficulty (Easiest)": 15,
            "Length (Longest)": 18,
            "Length (Shortest)": 17,
            "Downloads (Most)": 20,
            "Downloads (Least)": 19,
            "Rating (Most)": 30,
            "Rating (Least)": 29,
        }
        self.sort_combo.addItems(self.sort_options.keys())
        map_filters_layout.addWidget(self.sort_combo, 1, 1)

        map_filters_layout.addWidget(QLabel("Environment:"), 1, 2)
        self.env_combo = QComboBox()
        self.env_combo.addItems(["All", "Stadium", "Snow", "Rally", "Desert"])
        map_filters_layout.addWidget(self.env_combo, 1, 3)

        map_filters_layout.addWidget(QLabel("Difficulty:"), 2, 0)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["All", "Beginner", "Intermediate", "Advanced", "Expert"])
        map_filters_layout.addWidget(self.difficulty_combo, 2, 1)

        map_filters_layout.addWidget(QLabel("Length:"), 2, 2)
        self.length_combo = QComboBox()
        self.length_combo.addItems(["All", "0-30 sec", "30-60 sec", "1-2 min", "2-5 min", "5+ min"])
        map_filters_layout.addWidget(self.length_combo, 2, 3)

        map_filters_layout.addWidget(QLabel("Limit:"), 3, 0)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 100)
        self.limit_spin.setValue(DEFAULT_LIMIT)
        self.limit_spin.setSuffix(" maps")
        map_filters_layout.addWidget(self.limit_spin, 3, 1)

        self.browse_btn = QPushButton("🔍 Search")
        self.browse_btn.clicked.connect(self.search_browse)
        map_filters_layout.addWidget(self.browse_btn, 3, 2, 1, 2)

        self.map_filters_frame.setLayout(map_filters_layout)
        layout.addWidget(self.map_filters_frame)

        self.mappack_filters_frame = QFrame()
        self.mappack_filters_frame.setFrameStyle(QFrame.StyledPanel)
        self.mappack_filters_frame.hide()
        mappack_filters_layout = QHBoxLayout()

        mappack_filters_layout.addWidget(QLabel("Search:"))
        self.mappack_search_input = QLineEdit()
        self.mappack_search_input.setPlaceholderText("Mappack name or author...")
        mappack_filters_layout.addWidget(self.mappack_search_input)

        self.mappack_browse_btn = QPushButton("🔍 Search")
        self.mappack_browse_btn.clicked.connect(self.search_mappacks)
        mappack_filters_layout.addWidget(self.mappack_browse_btn)

        self.official_packs_btn = QPushButton("🎮 Official Packs")
        self.official_packs_btn.clicked.connect(self.load_official_packs)
        mappack_filters_layout.addWidget(self.official_packs_btn)

        self.mappack_filters_frame.setLayout(mappack_filters_layout)
        layout.addWidget(self.mappack_filters_frame)

        self.browse_results = QListWidget()
        self.browse_results.itemClicked.connect(self.on_browse_item_selected)
        layout.addWidget(self.browse_results)

        details_layout = QHBoxLayout()

        self.browse_details = QTextEdit()
        self.browse_details.setReadOnly(True)
        self.browse_details.setMaximumHeight(200)
        details_layout.addWidget(self.browse_details, 2)

        self.browse_thumbnail = QLabel()
        self.browse_thumbnail.setFixedSize(200, 150)
        self.browse_thumbnail.setAlignment(Qt.AlignCenter)
        self.browse_thumbnail.setStyleSheet("border: 1px solid #555;")
        self.browse_thumbnail.setText("Image")
        details_layout.addWidget(self.browse_thumbnail)
        layout.addLayout(details_layout)

        action_layout = QHBoxLayout()

        self.browse_download_btn = QPushButton("⬇️ Download")
        self.browse_download_btn.clicked.connect(self.download_selected)
        self.browse_download_btn.setEnabled(False)

        self.browse_launch_btn = QPushButton("▶️ Launch")
        self.browse_launch_btn.clicked.connect(self.launch_selected)
        self.browse_launch_btn.setEnabled(False)

        self.fav_add_btn = QPushButton("⭐ Add to Favorites")
        self.fav_add_btn.clicked.connect(self.add_to_favorites)
        self.fav_add_btn.setEnabled(False)

        # DODAJ TEN PRZYCISK
        self.fav_mappack_btn = QPushButton("⭐ Add Mappack to Favorites")
        self.fav_mappack_btn.clicked.connect(self.add_mappack_to_favorites)
        self.fav_mappack_btn.setEnabled(False)
        self.fav_mappack_btn.hide()

        self.show_maps_btn = QPushButton("🗺️ Show Maps in Mappack")
        self.show_maps_btn.clicked.connect(self.show_mappack_maps)
        self.show_maps_btn.setEnabled(False)
        self.show_maps_btn.hide()

        action_layout.addWidget(self.browse_download_btn)
        action_layout.addWidget(self.browse_launch_btn)
        action_layout.addWidget(self.fav_add_btn)
        action_layout.addWidget(self.fav_mappack_btn)  # DODAJ
        action_layout.addWidget(self.show_maps_btn)
        layout.addLayout(action_layout)

        widget.setLayout(layout)
        return widget

    def create_favorites_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel("💾 Your favorite maps:")
        layout.addWidget(label)

        self.favorites_list = QListWidget()
        layout.addWidget(self.favorites_list)

        btn_layout = QHBoxLayout()
        self.fav_launch_btn = QPushButton("▶️ Launch")
        self.fav_launch_btn.clicked.connect(self.launch_favorite)
        self.fav_remove_btn = QPushButton("🗑️ Remove")
        self.fav_remove_btn.clicked.connect(self.remove_favorite)
        btn_layout.addWidget(self.fav_launch_btn)
        btn_layout.addWidget(self.fav_remove_btn)
        layout.addLayout(btn_layout)

        self.load_favorites()
        widget.setLayout(layout)
        return widget

    def create_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("⚙️ Configuration"))

        tm_layout = QHBoxLayout()
        tm_layout.addWidget(QLabel("Trackmania.exe:"))
        self.tm_path_input = QLineEdit(TRACKMANIA_EXE)
        tm_layout.addWidget(self.tm_path_input)
        tm_browse_btn = QPushButton("Browse...")
        tm_browse_btn.clicked.connect(self.browse_trackmania_exe)
        tm_layout.addWidget(tm_browse_btn)
        layout.addLayout(tm_layout)

        maps_layout = QHBoxLayout()
        maps_layout.addWidget(QLabel("Maps Directory:"))
        self.maps_dir_input = QLineEdit(MAPS_DIR)
        maps_layout.addWidget(self.maps_dir_input)
        maps_browse_btn = QPushButton("Browse...")
        maps_browse_btn.clicked.connect(self.browse_maps_dir)
        maps_layout.addWidget(maps_browse_btn)
        layout.addLayout(maps_layout)

        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("API Base URL:"))
        self.api_input = QLineEdit(API_BASE)
        api_layout.addWidget(self.api_input)
        layout.addLayout(api_layout)

        hotkey_layout = QHBoxLayout()
        hotkey_layout.addWidget(QLabel("Hotkey:"))
        self.hotkey_input = QLineEdit(DEFAULT_HOTKEY)
        hotkey_layout.addWidget(self.hotkey_input)
        layout.addLayout(hotkey_layout)

        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(250)
        info_text.setText(
            "ℹ️ Configuration\n\n"
            "Settings are saved to config.ini\n"
            "All paths can be absolute or relative\n"
            "API Base URL must include protocol (https://)\n"
            "\n"
            "Version: 4.1 (Production Ready)"
        )
        layout.addWidget(info_text)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: Segoe UI;
                font-size: 11px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #0d7377;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14FFEC;
                color: #000;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #0d7377;
            }
            QTextEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
        """)

    def browse_trackmania_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Trackmania.exe", "", "Executable (*.exe)")
        if file_path:
            self.tm_path_input.setText(file_path)

    def browse_maps_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Maps Directory")
        if dir_path:
            self.maps_dir_input.setText(dir_path)

    def on_search_type_changed(self):
        is_maps = self.map_radio.isChecked()
        self.map_filters_frame.setVisible(is_maps)
        self.mappack_filters_frame.setVisible(not is_maps)
        self.browse_results.clear()
        self.browse_details.clear()
        self.browse_thumbnail.setText("Image")
        self.browse_download_btn.setEnabled(False)
        self.browse_launch_btn.setEnabled(False)
        self.fav_add_btn.setEnabled(False)
        self.show_maps_btn.setEnabled(False)

    def search_browse(self):
        print("[BROWSE] Starting map search")
        self.status_label.setText("🔍 Searching...")
        self.browse_btn.setEnabled(False)

        params = {}

        name = self.name_input.text().strip()
        if name:
            params["name"] = name

        author = self.author_input.text().strip()
        if author:
            params["author"] = author

        sort_text = self.sort_combo.currentText()
        if sort_text in self.sort_options:
            params["order1"] = self.sort_options[sort_text]

        env = self.env_combo.currentText()
        if env != "All":
            env_map = {"Stadium": 0, "Snow": 1, "Rally": 2, "Desert": 3}
            if env in env_map:
                params["environment"] = env_map[env]

        diff = self.difficulty_combo.currentText()
        if diff != "All":
            diff_map = {"Beginner": 0, "Intermediate": 1, "Advanced": 2, "Expert": 3}
            if diff in diff_map:
                params["difficulty"] = diff_map[diff]

        length = self.length_combo.currentText()
        if length != "All":
            length_map = {
                "0-30 sec": (0, 30000),
                "30-60 sec": (30000, 60000),
                "1-2 min": (60000, 120000),
                "2-5 min": (120000, 300000),
                "5+ min": (300000, 999999999)
            }
            if length in length_map:
                min_len, max_len = length_map[length]
                params["lengthmin"] = min_len
                params["lengthmax"] = max_len

        params["count"] = self.limit_spin.value()

        self.search_worker = SearchWorker(params)
        self.search_worker.finished.connect(self.on_browse_finished)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()

    def search_mappacks(self):
        query = self.mappack_search_input.text().strip()
        if not query:
            self.status_label.setText("⚠️ Enter mappack name")
            return

        print(f"[MAPPACK_SEARCH] Query: {query}")
        self.status_label.setText("🔍 Searching mappacks...")
        self.mappack_browse_btn.setEnabled(False)

        params = {
            "name": query,
            "count": 25,
            "order1": 6
        }

        self.mappack_worker = MappackSearchWorker(params)
        self.mappack_worker.finished.connect(self.on_mappack_search_finished)
        self.mappack_worker.error.connect(self.on_search_error)
        self.mappack_worker.start()

    def load_official_packs(self):
        print("[OFFICIAL_PACKS] Loading official packs")
        self.status_label.setText("🔍 Loading official packs...")
        self.official_packs_btn.setEnabled(False)

        params = {
            "manager": "Ubisoft Nadeo",
            "count": 100,
            "order1": 6
        }

        self.mappack_worker = MappackSearchWorker(params)
        self.mappack_worker.finished.connect(self.on_official_packs_loaded)
        self.mappack_worker.error.connect(self.on_search_error)
        self.mappack_worker.start()

    def on_browse_finished(self, maps: List[MapInfo]):
        print(f"[BROWSE] Found {len(maps)} maps")
        self.browse_results.clear()
        self.current_maps = maps

        if not maps:
            self.status_label.setText("❌ No maps found")
            self.browse_btn.setEnabled(True)
            return

        for map_info in maps:
            item_text = f"🏁 {map_info.Name} | 👤 {map_info.Username}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, map_info)
            self.browse_results.addItem(item)

        self.status_label.setText(f"✅ Found {len(maps)} maps")
        self.browse_btn.setEnabled(True)

    def on_mappack_search_finished(self, mappacks: List[MappackInfo]):
        print(f"[MAPPACK_SEARCH] Found {len(mappacks)} mappacks")
        self.browse_results.clear()
        self.current_mappacks = mappacks

        if not mappacks:
            self.status_label.setText("❌ No mappacks found")
            self.mappack_browse_btn.setEnabled(True)
            self.official_packs_btn.setEnabled(True)
            return

        for mappack in mappacks:
            item_text = f"📦 {mappack.Name} | 👤 {mappack.Username} | 🗺️ {mappack.TrackCount}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, mappack)
            item.setData(Qt.UserRole + 1, "mappack")
            self.browse_results.addItem(item)

        self.status_label.setText(f"✅ Found {len(mappacks)} mappacks")
        self.mappack_browse_btn.setEnabled(True)
        self.official_packs_btn.setEnabled(True)

    def on_official_packs_loaded(self, mappacks: List[MappackInfo]):
        print(f"[OFFICIAL_PACKS] Found {len(mappacks)} official packs")
        self.browse_results.clear()
        self.current_mappacks = mappacks

        if not mappacks:
            self.status_label.setText("❌ No official packs found")
            self.official_packs_btn.setEnabled(True)
            return

        for mappack in mappacks:
            item_text = f"🎮 {mappack.Name} | 🗺️ {mappack.TrackCount} maps"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, mappack)
            item.setData(Qt.UserRole + 1, "mappack")
            self.browse_results.addItem(item)

        self.status_label.setText(f"✅ Found {len(mappacks)} official packs")
        self.official_packs_btn.setEnabled(True)

    def on_search_error(self, error: str):
        print(f"[ERROR] {error}")
        self.status_label.setText(f"❌ {error}")
        self.browse_btn.setEnabled(True)
        self.mappack_browse_btn.setEnabled(True)
        self.official_packs_btn.setEnabled(True)

    def on_browse_item_selected(self, item: QListWidgetItem):
        item_type = item.data(Qt.UserRole + 1)
        
        if item_type == "mappack":
            self.selected_mappack = item.data(Qt.UserRole)
            self.browse_details.setText(self.selected_mappack.get_info_text())
            self.browse_download_btn.setEnabled(False)
            self.browse_launch_btn.setEnabled(False)
            self.fav_add_btn.setEnabled(False)
            self.fav_add_btn.hide()
            self.fav_mappack_btn.setEnabled(True)  # DODAJ
            self.fav_mappack_btn.show()  # DODAJ
            self.show_maps_btn.setEnabled(True)
            self.show_maps_btn.show()
            self.load_mappack_thumbnail(self.selected_mappack.ID)
        else:
            self.selected_map = item.data(Qt.UserRole)
            self.browse_details.setText(self.selected_map.get_info_text())
            self.browse_download_btn.setEnabled(True)
            self.fav_add_btn.setEnabled(True)  # DODAJ
            self.fav_add_btn.show()  # DODAJ
            self.fav_mappack_btn.setEnabled(False)
            self.fav_mappack_btn.hide()
            self.show_maps_btn.setEnabled(False)
            self.show_maps_btn.hide()
            
            map_file = os.path.join(MAPS_DIR, f"{self.selected_map.TrackID}.Map.Gbx")
            self.browse_launch_btn.setEnabled(os.path.exists(map_file))
            
            self.load_thumbnail(self.selected_map.TrackID, self.browse_thumbnail)

    def load_thumbnail(self, map_id: int, label: QLabel):
        thumbnail_path = os.path.join(CACHE_DIR, f"{map_id}.jpg")

        if os.path.exists(thumbnail_path):
            print(f"[THUMBNAIL] From cache: {map_id}")
            pixmap = QPixmap(thumbnail_path)
            label.setPixmap(pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return

        if not AUTO_CACHE:
            label.setText("Thumbnails disabled")
            return

        try:
            url = f"{API_THUMBNAIL}/{map_id}"
            print(f"[THUMBNAIL] Downloading from: {url}")

            response = requests.get(url, timeout=5, verify=VERIFY_SSL)
            response.raise_for_status()

            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)

            print(f"[THUMBNAIL] Saved: {thumbnail_path}")
            pixmap = QPixmap(thumbnail_path)
            label.setPixmap(pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        except Exception as e:
            print(f"[ERROR] Thumbnail error: {e}")
            label.setText("No image")

    def load_mappack_thumbnail(self, mappack_id: int):
        thumbnail_path = os.path.join(CACHE_DIR, f"mappack_{mappack_id}.jpg")

        if os.path.exists(thumbnail_path):
            print(f"[MAPPACK_THUMBNAIL] From cache: {mappack_id}")
            pixmap = QPixmap(thumbnail_path)
            self.browse_thumbnail.setPixmap(pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return

        if not AUTO_CACHE:
            self.browse_thumbnail.setText("Thumbnails disabled")
            return

        try:
            url = f"{API_MAPPACK_THUMBNAIL}/{mappack_id}"
            print(f"[MAPPACK_THUMBNAIL] Downloading from: {url}")

            response = requests.get(url, timeout=5, verify=VERIFY_SSL)
            response.raise_for_status()

            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)

            print(f"[MAPPACK_THUMBNAIL] Saved: {thumbnail_path}")
            pixmap = QPixmap(thumbnail_path)
            self.browse_thumbnail.setPixmap(pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        except Exception as e:
            print(f"[ERROR] Mappack thumbnail error: {e}")
            self.browse_thumbnail.setText("No image")

    def show_mappack_maps(self):
        if not self.selected_mappack:
            return

        print(f"[MAPPACK] Loading maps from mappack {self.selected_mappack.ID}")
        self.status_label.setText("🔍 Loading maps from mappack...")

        self.mappack_maps_worker = MappackMapsWorker(self.selected_mappack.ID)
        self.mappack_maps_worker.finished.connect(self.on_mappack_maps_loaded)
        self.mappack_maps_worker.error.connect(self.on_search_error)
        self.mappack_maps_worker.start()

    def on_mappack_maps_loaded(self, maps: List[MapInfo]):
        print(f"[MAPPACK] Loaded {len(maps)} maps")

        self.browse_results.clear()
        self.current_maps = maps

        if not maps:
            self.status_label.setText("❌ No maps in mappack")
            return

        for map_info in maps:
            item_text = f"🏁 {map_info.Name} | 👤 {map_info.Username}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, map_info)
            self.browse_results.addItem(item)

        self.status_label.setText(f"✅ Loaded {len(maps)} maps from mappack")

    def download_selected(self):
        if not self.selected_map:
            return

        self.status_label.setText("⬇️ Downloading...")
        self.browse_download_btn.setEnabled(False)

        self.download_worker = DownloadWorker(self.selected_map.TrackID)
        self.download_worker.finished.connect(lambda _: self.on_download_finished())
        self.download_worker.error.connect(self.on_search_error)
        self.download_worker.progress.connect(lambda p: self.status_label.setText(f"⬇️ {p}%"))
        self.download_worker.start()

    def on_download_finished(self):
        self.status_label.setText("✅ Downloaded")
        self.browse_download_btn.setEnabled(True)
        self.browse_launch_btn.setEnabled(True)

    def launch_selected(self):
        if not self.selected_map:
            return
        map_file = os.path.join(MAPS_DIR, f"{self.selected_map.TrackID}.Map.Gbx")
        self.launch_map(map_file)

    def launch_map(self, map_file: str):
        if not os.path.exists(map_file):
            self.status_label.setText("❌ Map file not found")
            return

        tm_exe = self.tm_path_input.text()
        if not os.path.exists(tm_exe):
            self.status_label.setText("❌ Trackmania.exe not found")
            return

        try:
            print(f"[LAUNCH] {map_file}")
            subprocess.Popen([tm_exe, "/useexedir", "/singleinst", f"/file={map_file}"])
            self.status_label.setText("✅ Launched")
            if LAUNCH_HIDDEN:
                self.hide()
        except Exception as e:
            print(f"[ERROR] {e}")
            self.status_label.setText(f"❌ {str(e)}")

    def add_mappack_to_favorites(self):
        if not self.selected_mappack:
            return
        
        # Check if already in favorites
        mappack_ids = [fav["id"] for fav in self.favorites["mappacks"]]
        if self.selected_mappack.ID in mappack_ids:
            self.status_label.setText("⚠️ Already in favorites")
            return
        
        # Add with name
        fav_entry = {
            "id": self.selected_mappack.ID,
            "name": self.selected_mappack.Name,
            "author": self.selected_mappack.Username,
            "map_count": self.selected_mappack.TrackCount
        }
        self.favorites["mappacks"].append(fav_entry)
        self.config.save_favorites(self.favorites)
        
        self.status_label.setText("⭐ Mappack added to favorites")
        self.load_favorites()

    def add_to_favorites(self):
        if not self.selected_map:
            return
        
        # Check if already in favorites
        map_ids = [fav["id"] for fav in self.favorites["maps"]]
        if self.selected_map.TrackID in map_ids:
            self.status_label.setText("⚠️ Already in favorites")
            return
        
        # Add with name
        fav_entry = {
            "id": self.selected_map.TrackID,
            "name": self.selected_map.Name,
            "author": self.selected_map.Username
        }
        self.favorites["maps"].append(fav_entry)
        self.config.save_favorites(self.favorites)
        
        self.status_label.setText("⭐ Added to favorites")
        self.load_favorites()

    def load_favorites(self):
        self.favorites_list.clear()
        
        # Maps
        for fav in self.favorites.get("maps", []):
            map_id = fav.get("id") if isinstance(fav, dict) else fav
            map_name = fav.get("name", "Unknown") if isinstance(fav, dict) else f"Map {fav}"
            map_author = fav.get("author", "Unknown") if isinstance(fav, dict) else "Unknown"
            
            item_text = f"🏁 {map_name}"
            if map_author != "Unknown":
                item_text += f" | 👤 {map_author}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, map_id)
            item.setData(Qt.UserRole + 1, "map")
            self.favorites_list.addItem(item)
        
        # Mappacks
        for fav in self.favorites.get("mappacks", []):
            mappack_id = fav.get("id") if isinstance(fav, dict) else fav
            mappack_name = fav.get("name", "Unknown") if isinstance(fav, dict) else f"Mappack {fav}"
            mappack_author = fav.get("author", "Unknown") if isinstance(fav, dict) else "Unknown"
            maps_count = fav.get("map_count", 0) if isinstance(fav, dict) else 0
            
            item_text = f"📦 {mappack_name}"
            if mappack_author != "Unknown":
                item_text += f" | 👤 {mappack_author}"
            if maps_count > 0:
                item_text += f" | 🗺️ {maps_count}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, mappack_id)
            item.setData(Qt.UserRole + 1, "mappack")
            self.favorites_list.addItem(item)

    def launch_favorite(self):
        """Launch map or show mappack maps from favorites"""
        item = self.favorites_list.currentItem()
        if not item:
            return
        
        item_id = item.data(Qt.UserRole)  # To już powinno być int, nie dict
        item_type = item.data(Qt.UserRole + 1)
        
        if item_type == "mappack":
            # Load and show mappack maps
            print(f"[FAVORITE] Opening mappack {item_id}")
            self.status_label.setText("🔍 Loading mappack maps...")
            self.fav_launch_btn.setEnabled(False)
            
            self.mappack_maps_worker = MappackMapsWorker(item_id)
            self.mappack_maps_worker.finished.connect(self.on_favorite_mappack_loaded)
            self.mappack_maps_worker.error.connect(self.on_search_error)
            self.mappack_maps_worker.start()
        else:
            # Launch map directly
            map_file = os.path.join(MAPS_DIR, f"{item_id}.Map.Gbx")
            if os.path.exists(map_file):
                self.launch_map(map_file)
            else:
                self.status_label.setText("❌ Map file not found - need to download first")
                self.fav_launch_btn.setEnabled(True)

    def on_favorite_mappack_loaded(self, maps: List[MapInfo]):
        """Callback after loading mappack from favorites"""
        print(f"[FAVORITE_MAPPACK] Loaded {len(maps)} maps")
        
        self.browse_results.clear()
        self.current_maps = maps
        
        # Switch to browse tab
        self.tabs.setCurrentIndex(0)
        
        if not maps:
            self.status_label.setText("❌ No maps in mappack")
            self.fav_launch_btn.setEnabled(True)
            return
        
        for map_info in maps:
            item_text = f"🏁 {map_info.Name} | 👤 {map_info.Username}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, map_info)
            self.browse_results.addItem(item)
        
        self.status_label.setText(f"✅ Loaded {len(maps)} maps from mappack - select one to play")
        self.fav_launch_btn.setEnabled(True)

    def remove_favorite(self):
        item = self.favorites_list.currentItem()
        if not item:
            return
        
        item_id = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)
        
        if item_type == "map":
            # Remove by ID
            self.favorites["maps"] = [fav for fav in self.favorites["maps"] if fav["id"] != item_id]
        else:  # mappack
            self.favorites["mappacks"] = [fav for fav in self.favorites["mappacks"] if fav["id"] != item_id]
        
        self.config.save_favorites(self.favorites)
        self.load_favorites()

    def save_settings(self):
        config_mgr.set('Paths', 'trackmania_exe', self.tm_path_input.text())
        config_mgr.set('Paths', 'maps_directory', self.maps_dir_input.text())
        config_mgr.set('API', 'base_url', self.api_input.text())
        config_mgr.set('UI', 'hotkey', self.hotkey_input.text())

        self.status_label.setText("💾 Saved to config.ini")
        QMessageBox.information(self, "Settings", "Settings saved to config.ini\nRestart application for changes to take effect.")

    def close_application(self):
        self.config.save_favorites(self.favorites)
        QApplication.quit()

def toggle_overlay():
    if overlay.isVisible():
        overlay.hide()
    else:
        overlay.show()
        overlay.activateWindow()

if __name__ == "__main__":
    print("="*60)
    print("TRACKMANIA EXCHANGE BROWSER v4.1 (Production Ready)")
    print("="*60)

    app = QApplication(sys.argv)
    overlay = TrackmaniaExchangeBrowser()

    hotkey = config_mgr.get('UI', 'hotkey', DEFAULT_HOTKEY)

    try:
        keyboard.add_hotkey(hotkey, toggle_overlay)
        print(f"[HOTKEY] {hotkey}")
    except Exception as e:
        print(f"[ERROR] {e}")

    overlay.show()
    print("[INFO] Started")
    print("="*60)

    sys.exit(app.exec())
