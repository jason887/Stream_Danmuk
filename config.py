# config.py
from dotenv import load_dotenv
import os
from pathlib import Path

import logging
from pathlib import Path

# --- Application Configuration ---
FLASK_PORT = 5000
WEBSOCKET_PORT = 8765

# Determine the base directory of the script (assuming config.py is in the same dir as server.py)

BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / "MongoDB_url.env")
# Static files directory (for HTML, CSS, JS)
STATIC_FOLDER = BASE_DIR / "static"
# Scripts directory
SCRIPTS_DIR = BASE_DIR / "scripts"

# --- Database Configuration (Moved from old db_manager.py/db_config.py) ---
# Replace with your MongoDB connection string if different
MONGO_URI = os.getenv("mongodb_url")
DB_NAME = "trae_data"

# --- WebSocket Core Configuration (Moved from ws_core.py if they were there) ---
PING_INTERVAL = 30 # Send PING every 30 seconds
TIMEOUT_DURATION = PING_INTERVAL * 2 # Consider client timed out after 60 seconds without activity

# --- Danmaku Send Configuration (Moved from ws_danmaku_send_handlers.py) ---
SEND_INTERVAL_MS = 2200 # Interval between sending individual danmaku within an auto-send group
GROUP_PAUSE_MS = 3000 # Pause duration between sending different groups
AUTO_SEND_DURATION_MS = 22000 # Duration for each danmaku sent in bulk auto-send

def log_config():
    """Logs key configuration values (avoiding sensitive info)."""
    uri_to_log = MONGO_URI
    if "@" in uri_to_log:
        uri_to_log = "mongodb://" + uri_to_log.split('@')[-1]

    logging.info("-" * 20)
    logging.info("Application Configuration:")
    logging.info(f"  Flask Port: {FLASK_PORT}")
    logging.info(f"  WebSocket Port: {WEBSOCKET_PORT}")
    logging.info(f"  Base Directory: {BASE_DIR}")
    logging.info(f"  Static Folder: {STATIC_FOLDER}")
    logging.info(f"  Scripts Folder: {SCRIPTS_DIR}")
    logging.info("-" * 20)
    logging.info("Database Configuration:")
    logging.info(f"  MONGO_URI (sanitized): {uri_to_log}")
    logging.info(f"  DB_NAME: {DB_NAME}")
    logging.info("-" * 20)
    logging.info("WebSocket Heartbeat:")
    logging.info(f"  PING Interval: {PING_INTERVAL}s")
    logging.info(f"  Timeout Duration: {TIMEOUT_DURATION}s")
    logging.info("-" * 20)
    logging.info("Danmaku Send Timing:")
    logging.info(f"  Send Interval: {SEND_INTERVAL_MS}ms")
    logging.info(f"  Group Pause: {GROUP_PAUSE_MS}ms")
    logging.info(f"  Auto-Send Duration: {AUTO_SEND_DURATION_MS}ms")
    logging.info("-" * 20)

