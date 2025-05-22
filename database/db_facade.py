# database/db_facade.py
import logging
from pymongo.database import Database # Import for type hinting

# If in a sub-package 'database':
from .db_connection_manager import get_db_manager, DatabaseConnectionManager
from . import db_queries
from . import db_config

# If in the same directory:
# from db_connection_manager import get_db_manager, DatabaseConnectionManager
# import db_queries
# import db_config


def _get_db_or_log_error() -> Database | None:
    """Helper to get DB instance and return None if connection is missing."""
    manager = get_db_manager()
    # First, check if the manager itself exists and is connected
    if manager is None or not manager.is_connected():
        # Logging happens within DatabaseConnectionManager.connect_db if connection fails.
        # No need for repeated logging here for every check.
        return None # Return None if manager or connection is missing

    # Now that we know manager exists and is connected, get the db object
    # manager.get_db() internally checks if self.db is None
    db = manager.get_db()

    # Although manager.is_connected() implies db is not None if successful,
    # returning db directly is the goal of this helper.
    # The caller is responsible for checking if the returned db is None.
    return db # <-- This helper function itself looks correct


# Rest of the facade functions, APPLY THE FIX HERE:
def search_streamer_names(term: str, limit: int = 20):
    """Searches for streamer names via the facade."""
    db = _get_db_or_log_error()
    if db is not None: # <-- Corrected
        return db_queries.search_streamer_names_in_db(db, term, limit)
    return []


def fetch_danmaku(streamer_name: str | None, danmaku_type: str, limit: int = 10):
    """Fetches specific type of danmaku via the facade."""
    db = _get_db_or_log_error()
    if db is not None: # <-- Corrected
        return db_queries.fetch_danmaku_from_db(db, streamer_name, danmaku_type, limit)
    return []


def fetch_anti_fan_quotes(limit: int = 3):
    """Fetches anti-fan quotes via the facade."""
    db = _get_db_or_log_error()
    if db is not None: # <-- Corrected (This is the line indicated in the traceback)
        return db_queries.fetch_anti_fan_quotes_from_db(db, limit)
    return []


def fetch_reversal_copy_data(streamer_name: str, limit: int = 10):
    """Fetches Reversal_Copy data via the facade."""
    db = _get_db_or_log_error()
    if db is not None: # <-- Corrected
        return db_queries.fetch_reversal_copy_data_from_db(db, streamer_name, limit)
    return []


def fetch_social_topics_data(topic_name: str, limit: int = 10):
    """Fetches Social_Topics data via the facade."""
    db = _get_db_or_log_error()
    if db is not None: # <-- Corrected
        return db_queries.fetch_social_topics_data_from_db(db, topic_name, limit)
    return []

# This facade function must be async if the underlying db_queries function is async
async def get_random_danmaku(collection_name: str, count: int):
    """Fetches random danmaku via the facade."""
    db = _get_db_or_log_error()
    if db is not None: # <-- Corrected
        # Assuming db_queries.get_random_danmaku_from_db is async
        return await db_queries.get_random_danmaku_from_db(db, collection_name, count)
    return []


def fetch_big_brother_templates(limit: int = 30):
    """Fetches Big Brother welcome templates via the facade."""
    db = _get_db_or_log_error()
    if db is not None:
        return db_queries.fetch_big_brother_templates(db, limit)
    return []


def fetch_gift_thanks_templates(limit: int = 30):
    """Fetches Gift Thanks templates via the facade."""
    db = _get_db_or_log_error()
    if db is not None:
        return db_queries.fetch_gift_thanks_templates(db, limit)
    return []


def fetch_reversal_scripts(limit: int = 10):
    """Fetches reversal scripts (danmaku_part) via the facade."""
    db = _get_db_or_log_error()
    if db is not None:
        return db_queries.fetch_reversal_scripts(db, limit)
    return []

# Make sure db_config is exposed for access to collection names
# Example: database.db_config.ANTI_FAN_COLLECTION
__all__ = [
    'DatabaseConnectionManager', # Not needed by callers, but keeping for completeness if desired
    'init_db_manager',           # Not needed by callers
    'get_db_manager',            # Needed by init functions and some routes/handlers

    'search_streamer_names',
    'fetch_danmaku',
    'fetch_anti_fan_quotes',
    'fetch_reversal_copy_data',
    'fetch_social_topics_data',
    'get_random_danmaku',
    'fetch_big_brother_templates', 
    'fetch_gift_thanks_templates', 
    'fetch_reversal_scripts', # Add new function
    'db_config' # Expose db_config
]

