# database/__init__.py

import logging

# Expose main connection functions and the manager class
from .db_connection_manager import init_db_manager, get_db_manager
from .db_config import (
    WELCOME_COLLECTION, MOCK_COLLECTION, ANTI_FAN_COLLECTION,
    REVERSAL_COLLECTION, 
    # 删除 CAPTIONS_COLLECTION，添加 SOCIAL_TOPICS_COLLECTION
    BIG_BROTHERS_COLLECTION, GIFT_THANKS_COLLECTION,
    SOCIAL_TOPICS_COLLECTION
)
from .db_facade import (
    search_streamer_names,
    fetch_danmaku,
    fetch_anti_fan_quotes,
    fetch_reversal_copy_data,
    fetch_social_topics_data,
    get_random_danmaku
)

__all__ = [
    'init_db_manager', 'get_db_manager',
    'WELCOME_COLLECTION', 'MOCK_COLLECTION', 'ANTI_FAN_COLLECTION',
    'REVERSAL_COLLECTION', 
    # 删除 CAPTIONS_COLLECTION，添加 SOCIAL_TOPICS_COLLECTION
    'BIG_BROTHERS_COLLECTION', 'GIFT_THANKS_COLLECTION',
    'search_streamer_names', 'fetch_danmaku', 'fetch_anti_fan_quotes',
    'fetch_reversal_copy_data', 'fetch_social_topics_data', 'get_random_danmaku',  # 修正：添加逗号
    'SOCIAL_TOPICS_COLLECTION'  # 新增到 __all__ 列表
]

logging.getLogger(__name__).info("Database package initialized.")

