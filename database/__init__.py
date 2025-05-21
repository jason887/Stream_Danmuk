# database/__init__.py

import logging

# Expose main connection functions and the manager class
from .db_connection_manager import DatabaseConnectionManager, init_db_manager, get_db_manager

# Expose facade functions for easy application use
from .db_facade import (
    search_streamer_names,
    fetch_danmaku,
    fetch_anti_fan_quotes,
    fetch_reversal_copy_data,
    fetch_social_topics_data,
    get_random_danmaku # Make sure this is exposed if needed by handlers/routes
)

# Expose the config module itself, or specific constants if preferred
from . import db_config # To access constants like database.db_config.WELCOME_COLLECTION

__all__ = [
    # Connection management
    'DatabaseConnectionManager',
    'init_db_manager',
    'get_db_manager',
    # Facade functions (preferred way to interact for app logic)
    'search_streamer_names',
    'fetch_danmaku',
    'fetch_anti_fan_quotes',
    'fetch_reversal_copy_data',
    'fetch_social_topics_data',
    'get_random_danmaku',
    # Config module (to access constants like database.db_config.WELCOME_COLLECTION)
    'db_config'
]

logging.getLogger(__name__).info("Database package initialized.")

