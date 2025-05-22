# ws_danmaku_fetch_handlers.py



import logging

import json

# Import from the new database package

from database import get_db_manager, db_config, search_streamer_names, fetch_danmaku, fetch_reversal_copy_data, fetch_social_topics_data, fetch_anti_fan_quotes, fetch_big_brother_templates, fetch_gift_thanks_templates, fetch_reversal_scripts
# Import the new query function
from database.db_queries import fetch_complaints_data # Direct import for clarity
# For broadcasting to audience
from ws_core import broadcast_message




# Global references to dependencies (only need db_manager via getter, no direct instance needed)

# _db_manager = None # REMOVED



def init_danmaku_fetch_handlers(): # Removed db_manager_instance parameter

    """Initializes danmaku fetch handlers module."""

    logging.info("ws_danmaku_fetch_handlers: Initializing fetch handlers module.")

    # No global instance needed, handlers will use get_db_manager() directly

    logging.info("ws_danmaku_fetch_handlers: Fetch handlers module initialized.")





# Helper to check DB connection

def _is_db_connected():

    manager = get_db_manager()

    return manager and manager.is_connected()





async def handle_fetch_danmaku_list(websocket, data):

    """

    通过WebSocket获取指定主播的欢迎弹幕 (Welcome_Danmaku) 或吐槽弹幕 (Mock_Danmaku) 列表.
    data: {
        "streamer_name": "xxx",
        "danmaku_type": "welcome" (maps to Welcome_Danmaku) or "roast" (maps to Mock_Danmaku)
    }
    """
    # Check DB connection using helper

    if not _is_db_connected():

        logging.error("ws_danmaku_fetch_handlers: DB not connected. Cannot process fetch_danmaku_list.")

        await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法获取弹幕。", "context": "fetch_danmaku_db"}))

        return



    streamer_name = data.get("streamer_name")

    danmaku_type = data.get("danmaku_type") # "welcome" or "roast" (for mock)
    if not streamer_name or danmaku_type not in ["welcome", "roast"]:

        await websocket.send(json.dumps({"type": "error", "message": "参数错误，需提供主播名和弹幕类型('welcome' 或 'roast')。", "context": "fetch_danmaku_param"}))

        return



    try:

        # Use the facade function fetch_danmaku, it's synchronous
        # Assumes fetch_danmaku correctly queries Welcome_Danmaku for type 'welcome'
        # and Mock_Danmaku for type 'roast', filtered by streamer_name
        danmaku_list = fetch_danmaku(streamer_name, danmaku_type, limit=10) 



        await websocket.send(json.dumps({

            "type": "danmaku_list", # Client expects this type
            "danmaku_type": danmaku_type, # e.g., "welcome" or "roast"
            "streamer_name": streamer_name,

            "danmaku_list": danmaku_list,
            "context": f"fetch_danmaku_{danmaku_type}" # For client-side differentiation
        }))

        logging.info(f"ws_danmaku_fetch_handlers: Sent {len(danmaku_list)} '{danmaku_type}' danmaku for '{streamer_name}' to {websocket.remote_address}.")



    except Exception as e:

        logging.error(f"ws_danmaku_fetch_handlers: Error fetching danmaku list for '{streamer_name}', type '{danmaku_type}': {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "error", "message": f"获取弹幕时出错: {e}", "context": "fetch_danmaku_error"}))





async def handle_fetch_reversal(websocket, data):

    """

    通过WebSocket获取指定主播的反转语录列表 (Reversal_Copy collection).
    data: { "streamer_name": "xxx" }
    """
    if not _is_db_connected():

        logging.error("ws_danmaku_fetch_handlers: DB not connected. Cannot process fetch_reversal.")

        await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法获取反转语录。", "context": "fetch_reversal_db"}))

        return



    streamer_name = data.get("streamer_name")

    if not streamer_name:

        await websocket.send(json.dumps({"type": "error", "message": "参数错误，需提供主播名。", "context": "fetch_reversal_param"}))

        return



    try:

        # Use the facade function, it's synchronous
        # Assumes fetch_reversal_copy_data queries Reversal_Copy collection by streamer_name
        reversal_list = fetch_reversal_copy_data(streamer_name, limit=10) 
        
        await websocket.send(json.dumps({

            "type": "reversal_list", # Client expects this type
            "streamer_name": streamer_name,

            "reversal_list": reversal_list,
            "context": "fetch_reversal"
        }))

        logging.info(f"ws_danmaku_fetch_handlers: Sent {len(reversal_list)} reversal entries for '{streamer_name}' to {websocket.remote_address}.")



    except Exception as e:

        logging.error(f"ws_danmaku_fetch_handlers: Error fetching reversal data for '{streamer_name}': {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "error", "message": f"获取反转语录时出错: {e}", "context": "fetch_reversal_error"}))





async def handle_fetch_captions(websocket, data):

    """

    通过WebSocket获取指定主题的段子/主题弹幕列表 (Generated_Captions collection).
    data: { "topic_name": "xxx" }
    """
    if not _is_db_connected():

        logging.error("ws_danmaku_fetch_handlers: DB not connected. Cannot process fetch_captions.")

        await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法获取主题弹幕。", "context": "fetch_captions_db"}))

        return



    topic_name = data.get("topic_name") # This is the 'event' or 'theme' name
    if not topic_name:

        await websocket.send(json.dumps({"type": "error", "message": "参数错误，需提供主题名。", "context": "fetch_captions_param"}))

        return



    try:

        # Use the facade function, it's synchronous
        # Assumes fetch_social_topics_data queries Generated_Captions (or db_config.CAPTIONS_COLLECTION) by topic_name
        captions_list = fetch_social_topics_data(topic_name, limit=10)



        await websocket.send(json.dumps({

            "type": "captions_list", # Client expects this type
            "topic_name": topic_name,

            "captions_list": captions_list,
            "context": "fetch_captions"
        }))

        logging.info(f"ws_danmaku_fetch_handlers: Sent {len(captions_list)} captions entries for topic '{topic_name}' to {websocket.remote_address}.")



    except Exception as e:

        logging.error(f"ws_danmaku_fetch_handlers: Error fetching captions data for topic '{topic_name}': {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "error", "message": f"获取主题弹幕时出错: {e}", "context": "fetch_captions_error"}))





async def handle_fetch_anti_fan_quotes(websocket, data):

    """

    通过WebSocket获取怼黑粉语录列表 (Anti_Fan_Quotes collection).
    This handler is for generic fetching if needed, roast mode uses its own fetch.
    data: {}
    """
    if not _is_db_connected():

        logging.error("ws_danmaku_fetch_handlers: DB not connected. Cannot process fetch_anti_fan_quotes.")

        await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法获取怼黑粉语录。", "context": "fetch_anti_fan_quotes_db"}))

        return



    try:

        # Use the facade function, it's synchronous
        # Assumes fetch_anti_fan_quotes queries Anti_Fan_Quotes collection
        # For the "怼黑粉" (Counter Black Fans) button, fetch 3 quotes as per requirement.
        quotes_list = fetch_anti_fan_quotes(limit=3) 



        await websocket.send(json.dumps({

            "type": "anti_fan_quotes_list", # Client expects this type
            "quotes_list": quotes_list,
            "context": "fetch_anti_fan_quotes"
        }))

        logging.info(f"ws_danmaku_fetch_handlers: Sent {len(quotes_list)} anti-fan quotes to {websocket.remote_address}.")



    except Exception as e:

        logging.error(f"ws_danmaku_fetch_handlers: Error fetching anti-fan quotes: {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "error", "message": f"获取怼黑粉语录时出错: {e}", "context": "fetch_anti_fan_quotes_error"}))



# Handler for streamer name search (used by frontend autocomplete)
async def handle_search_streamers(websocket, data):

    """

    通过WebSocket根据关键词搜索主播名.
    data: { "term": "部分主播名" }
    """
    if not _is_db_connected():

        await websocket.send(json.dumps({"type": "streamer_search_results", "term": data.get("term", ""), "results": []}))

        return



    term = data.get("term", "").strip()

    # It's okay to search for empty term if frontend wants to show initial list or all.
    # For now, we require a term. If empty term means "show all (limited)", logic can be adjusted.
    # For fuzzy search, empty term usually means no results or a predefined popular list.
    # Let's return empty for empty term to be safe.
    if not term and len(term) < 1: # Adjusted to allow single character search if desired, or set min length
         await websocket.send(json.dumps({"type": "streamer_search_results", "term": term, "results": []}))
         return


    try:

        # Use the facade function for search (synchronous)
        results = search_streamer_names(term, limit=20) 



        await websocket.send(json.dumps({

            "type": "streamer_search_results",

            "term": term,

            "results": results

        }))

    except Exception as e:

        logging.error(f"ws_danmaku_fetch_handlers: Error searching streamers for term '{term}': {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "streamer_search_results", "term": term, "results": []}))


# Handler for topic name search (e.g., from Generated_Captions, for frontend autocomplete)
async def handle_search_topics(websocket, data):

    """

    通过WebSocket根据关键词搜索主题名 (from Generated_Captions/Social_Topics).
    data: { "term": "部分主题名" }
    """
    if not _is_db_connected():

        await websocket.send(json.dumps({"type": "topic_search_results", "term": data.get("term", ""), "results": []}))

        return



    term = data.get("term", "").strip()
    if not term and len(term) < 1: # Min 1 char to search
         await websocket.send(json.dumps({"type": "topic_search_results", "term": term, "results": []}))
         return

    results = []
    try:
        manager = get_db_manager()
        db = manager.get_db() if manager and manager.is_connected() else None

        if db:
             # Assuming db_config.CAPTIONS_COLLECTION is 'Generated_Captions' or similar
             # And documents in this collection have a field like 'topic_name' or 'theme'
             collection_name = getattr(db_config, 'CAPTIONS_COLLECTION', 'Generated_Captions')
             topic_field_name = getattr(db_config, 'CAPTIONS_TOPIC_FIELD', 'topic_name') # Or 'theme', 'event_name'

             collection = db[collection_name]
             
             # Search for distinct topic names matching the term
             # Using $regex for case-insensitive partial match
             regex_query = {"$regex": term, "$options": "i"}
             
             # distinct() returns a list of unique values for the specified field
             distinct_topics = collection.distinct(topic_field_name, {topic_field_name: regex_query})
             
             # Limit results server-side
             results = distinct_topics[:20] 
             logging.debug(f"ws_danmaku_fetch_handlers: Found {len(results)} distinct topics for term '{term}' in '{collection_name}'.")

        await websocket.send(json.dumps({

            "type": "topic_search_results",

            "term": term,

            "results": results # Send found results or empty list if DB/collection error
        }))

    except Exception as e:

        logging.error(f"ws_danmaku_fetch_handlers: Error searching topics for term '{term}': {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "topic_search_results", "term": term, "results": []}))


# --- Registering Handlers (called by ws_core) ---

def register_danmaku_fetch_handlers():

    """Registers danmaku fetch-related WebSocket action handlers."""

    if get_db_manager() is None: # Basic check
        logging.error("ws_danmaku_fetch_handlers: DB manager not initialized during handler registration. Fetch handlers will be unavailable.")

        return {}



    handlers = {

        "fetch_danmaku_list": handle_fetch_danmaku_list,         # For Welcome_Danmaku, Mock_Danmaku
        "fetch_reversal": handle_fetch_reversal,                 # For Reversal_Copy
        "fetch_captions": handle_fetch_captions,                 # For Generated_Captions/Social_Topics
        "fetch_anti_fan_quotes": handle_fetch_anti_fan_quotes,   # For Anti_Fan_Quotes (general fetch)
        
        "search_streamers": handle_search_streamers,             # For streamer name autocomplete
        "search_topics": handle_search_topics,                   # For topic/theme name autocomplete
        "fetch_complaints_danmaku": handle_fetch_complaints_danmaku_request, 
        "fetch_big_brother_welcome": handle_fetch_big_brother_welcome_request,
        "fetch_gift_thanks_danmaku": handle_fetch_gift_thanks_danmaku_request,
        "fetch_reversal_scripts_request": handle_fetch_reversal_scripts_request, # New handler
    }

    logging.info(f"ws_danmaku_fetch_handlers: Registering fetch handlers: {list(handlers.keys())}")

    return handlers



# Expose necessary functions for server.py and ws_core.py

__all__ = [

    'init_danmaku_fetch_handlers',

    'register_danmaku_fetch_handlers',

]
