# database/db_config.py
import logging
# Import configuration from the central config file
# Assuming database package is adjacent to config.py
# from .. import config # If database is a sub-package like 'src/database'
# If database package is in the same directory as config.py and server.py
# from config import MONGO_URI, DB_NAME # This works if config.py is at the top level

# Let's assume config.py is at the top level, same as server.py
# You might need to adjust this import based on your project structure.
# Example: If your structure is project_root/server.py, project_root/config.py, project_root/database/__init__.py etc.
try:
    from config import MONGO_URI, DB_NAME
    # Import collection names which are *defined* within the database package's config file
    # Ensure these are defined below in this file
except ImportError:
    logging.critical("database.db_config: Could not import configuration from config.py. Ensure config.py is accessible.")
    # Provide dummy values to prevent immediate errors, though DB will likely fail
    MONGO_URI = "mongodb://localhost:27017/"
    DB_NAME = "default_db"


# Collection names (Defined here, specific to the database structure)
WELCOME_COLLECTION = "Welcome_Danmaku"
MOCK_COLLECTION = "Mock_Danmaku"
ANTI_FAN_COLLECTION = "Anti_Fan_Quotes"
REVERSAL_COLLECTION = "Reversal_Copy"
SOCIAL_TOPICS_COLLECTION = "Social_Topics" # 用于“加载主题/段子” (或者叫 Generated_Captions，取决于哪个集合包含 topic_name 和 generated_danmaku)
BIG_BROTHERS_COLLECTION = "Big_Brothers"
GIFT_THANKS_COLLECTION = "Gift_Thanks_Danmaku"

# You can keep a logging function here specific to DB config if needed, but general config is in config.py
# def log_db_specific_config():
#     logging.info(f"DB_Config: Welcome Collection: {WELCOME_COLLECTION}")
#     ...
