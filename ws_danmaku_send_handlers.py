# ws_danmaku_send_handlers.py



import logging

import json

import asyncio

import random # For shuffling danmaku



# Import from the new database package

# Need get_db_manager, db_config constants, and get_random_danmaku facade function (which is async)

# Also fetch_danmaku for handle_auto_send_danmaku

from database import get_db_manager, db_config, get_random_danmaku, fetch_danmaku # get_random_danmaku is async, fetch_danmaku is sync



# Global references to dependencies

_broadcast_message = None

# _db_manager = None # REMOVED - Use get_db_manager() instead



# Interval between sending individual danmaku within an auto-send group

# 10 danmaku in 22 seconds means roughly 2.2 seconds per danmaku

SEND_INTERVAL_MS = 2200 # 2200 milliseconds = 2.2 seconds



# Pause duration between sending different groups (e.g., between Welcome and Roast)

GROUP_PAUSE_MS = 3000 # 3 seconds pause between groups



# Duration for each danmaku sent in bulk auto-send (Welcome/Mock)

# MODIFIED: Default to 10 seconds for Welcome/Mock as per new general rule
AUTO_SEND_DURATION_MS = 10000 # 10 seconds 

# Duration for Boss/Gift danmaku will be specifically set to 22 seconds
BOSS_GIFT_DANMAKU_DURATION_MS = 22000 # 22 seconds





def init_danmaku_send_handlers(broadcast_message_func): # Removed db_manager_instance parameter

    """Initializes danmaku send handlers module with necessary dependencies."""

    logging.info("ws_danmaku_send_handlers: Initializing send handlers module with dependencies.")

    global _broadcast_message

    _broadcast_message = broadcast_message_func # Store the broadcast function

    # No global db_manager instance needed, handlers use get_db_manager()

    logging.info("ws_danmaku_send_handlers: Send handlers module initialized.")



# Helper to check DB connection

def _is_db_connected():

    manager = get_db_manager()

    return manager and manager.is_connected()





async def _send_danmaku_group(danmaku_list, danmaku_type_label, websocket=None, target_name="", gift_name="", specific_duration_ms=None):

    """
    Helper to send a list of danmaku with delay between items.
    Accepts specific_duration_ms to override global AUTO_SEND_DURATION_MS.
    """

    if not danmaku_list:

        logging.info(f"ws_danmaku_send_handlers: 没有可发送的'{danmaku_type_label}'弹幕。")

        if websocket: # Send status update to control client

            await websocket.send(json.dumps({"type": "info", "message": f"没有可发送的{danmaku_type_label}弹幕。", "context": f"auto_send_{danmaku_type_label}_empty"}))

        return



    logging.info(f"ws_danmaku_send_handlers: 发送 {len(danmaku_list)} 条'{danmaku_type_label}'弹幕。")

    if websocket: # Send status update to control client

        await websocket.send(json.dumps({"type": "info", "message": f"发送 {len(danmaku_list)} 条{danmaku_type_label}弹幕...", "context": f"auto_send_{danmaku_type_label}_group"}))



    # Determine if it's a roast type based on label (for audience display styling)

    is_roast = (danmaku_type_label.lower().startswith("吐槽") or danmaku_type_label.lower().startswith("怼人"))



    # Determine the duration to use for each danmaku
    duration_to_use = specific_duration_ms if specific_duration_ms is not None else AUTO_SEND_DURATION_MS


    sent_count = 0

    for i, raw_text in enumerate(danmaku_list):

        if not isinstance(raw_text, str) or not raw_text.strip():

            logging.warning(f"ws_danmaku_send_handlers: 跳过无效的 {danmaku_type_label} 弹幕条目: {raw_text}")

            continue



        processed_text = raw_text.strip()



        # Parameter replacement logic

        # {} replacement for Welcome Boss

        if danmaku_type_label.startswith("欢迎大哥") and target_name:

            processed_text = processed_text.replace("{}", target_name, 1) # Replace first {}

            if "{}" in processed_text:

                 logging.warning(f"ws_danmaku_send_handlers: 欢迎大哥模板 '{raw_text}' 替换大哥昵称后仍包含 '{{}}': '{processed_text}'")



        # {} replacement for Gift Thanks

        elif danmaku_type_label.startswith("感谢大哥礼物"):

            # Replace gift_name first, then target_name if they exist

            if gift_name: processed_text = processed_text.replace("{}", gift_name, 1)

            if target_name: processed_text = processed_text.replace("{}", target_name, 1)



            # Handle any remaining {} if template has more than 2

            if "{}" in processed_text:

                logging.warning(f"ws_danmaku_send_handlers: 感谢礼物模板 '{raw_text}' 替换后仍包含 '{{}}': '{processed_text}'")

                # Default replacements for any leftover {}

                processed_text = processed_text.replace("{}", "礼物", 1) # Fallback for first remaining {}
                if "{}" in processed_text: # If another {} still exists
                    processed_text = processed_text.replace("{}", "大哥", 1) # Fallback for second remaining {}





        # Other types (Welcome/Mock fetched by handle_auto_send_danmaku) are assumed ready strings



        danmaku_message = {

            "type": "danmaku",

            "text": processed_text,

            "duration_ms": duration_to_use, # Use determined duration
            "is_roast": is_roast # Pass the roast flag
        }



        try:

            # Use the global _broadcast_message function

            if _broadcast_message:

                await _broadcast_message("audience", danmaku_message)

                logging.debug(f"ws_danmaku_send_handlers: 发送 '{danmaku_type_label}' 弹幕 {sent_count+1}: '{processed_text}' (Duration: {duration_to_use}ms)")

                sent_count += 1

            else:

                 logging.error("ws_danmaku_send_handlers: Broadcast function not initialized!")

                 if websocket:

                      await websocket.send(json.dumps({"type": "error", "message": "广播功能未初始化，无法发送弹幕。", "context": "send_danmaku_broadcast_error"}))

                 break # Stop sending if broadcast fails



        except Exception as e:

            logging.error(f"ws_danmaku_send_handlers: 广播 '{danmaku_type_label}' 弹幕时出错: {e}", exc_info=True)

            if websocket:

                 await websocket.send(json.dumps({"type": "error", "message": f"广播弹幕失败: {e}", "context": f"send_danmaku_{danmaku_type_label}_broadcast_exception"}))





        # Add delay only if there are more items to send in this group

        if i < len(danmaku_list) - 1:

            await asyncio.sleep(SEND_INTERVAL_MS / 1000)





    if sent_count > 0:

        logging.info(f"ws_danmaku_send_handlers: 完成发送 {sent_count} 条 '{danmaku_type_label}' 弹幕。")

    else:

        logging.warning(f"ws_danmaku_send_handlers: 没有发送任何有效的 '{danmaku_type_label}' 弹幕。")





async def handle_auto_send_danmaku(websocket, data):

    """
    Handles the 'auto_send_danmaku' action to fetch and automatically send welcome/mock danmaku.
    Welcome danmaku from 'Welcome_Danmaku' collection.
    Mock (吐槽) danmaku from 'Mock_Danmaku' collection.
    Uses global AUTO_SEND_DURATION_MS (10 seconds) via _send_danmaku_group default.
    """
    # Check dependencies using globals set by init

    if _broadcast_message is None: # Need broadcast function

        logging.error("ws_danmaku_send_handlers: Broadcast function not initialized. Cannot process auto_send_danmaku.")

        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：弹幕发送功能未初始化。", "context": "auto_send_init"}))

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_init_reenable"}))

        return



    # Check DB connection using helper

    if not _is_db_connected():

        logging.error("ws_danmaku_send_handlers: DB not connected. Cannot fetch danmaku for auto-send.")

        await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法自动发送弹幕。", "action": "auto_send_danmaku", "context": "auto_send_db_disconnected"}))

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_db_reenable"}))

        return





    streamer_name = data.get("streamer_name")

    presenter_addr = websocket.remote_address



    if not streamer_name:

        logging.warning(f"ws_danmaku_send_handlers: Presenter {presenter_addr} sent auto_send_danmaku with no streamer name.")

        await websocket.send(json.dumps({"type": "warning", "message": "请提供主播名。", "action": "auto_send_danmaku", "context": "auto_send_no_name"}))

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_no_name_reenable"}))

        return





    try:

        # Fetch danmaku lists using the facade functions (fetch_danmaku is sync)
        # Assuming fetch_danmaku(streamer_name, "welcome", ...) queries Welcome_Danmaku for this streamer
        # Assuming fetch_danmaku(streamer_name, "roast", ...) queries Mock_Danmaku for this streamer
        welcome_danmaku_list = fetch_danmaku(streamer_name, "welcome", limit=10)
        roast_danmaku_list = fetch_danmaku(streamer_name, "roast", limit=10) # "roast" type here implies "Mock_Danmaku"



        if not welcome_danmaku_list and not roast_danmaku_list:

            logging.warning(f"ws_danmaku_send_handlers: No welcome or mock danmaku found for streamer '{streamer_name}'.")

            await websocket.send(json.dumps({

                "type": "warning",

                "message": f"未找到 {streamer_name} 的欢迎或吐槽弹幕。",

                "action": "auto_send_danmaku",

                "context": "auto_send_no_data"

            }))

            # Signal client to re-enable buttons

            await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_no_data_reenable"}))

            return



        # --- Start Auto-Sending Sequence ---

        logging.info(f"ws_danmaku_send_handlers: Starting auto-send sequence for '{streamer_name}'. Welcome: {len(welcome_danmaku_list)}, Mock: {len(roast_danmaku_list)}")

        await websocket.send(json.dumps({"type": "info", "message": f"开始自动发送 {streamer_name} 的弹幕...", "context": "auto_send_starting"}))

        # Signal client to disable buttons during sending

        await websocket.send(json.dumps({"type": "auto_send_started", "context": "auto_send_started"}))





        # Send Welcome danmaku group (uses default AUTO_SEND_DURATION_MS via _send_danmaku_group)

        if welcome_danmaku_list:

            # Pass websocket to _send_danmaku_group for progress updates

            await _send_danmaku_group(welcome_danmaku_list, "欢迎", websocket)



            # Wait for the pause duration after the welcome group, only if there's a next group

            if roast_danmaku_list:

                 logging.info(f"ws_danmaku_send_handlers: Pausing {GROUP_PAUSE_MS/1000}s before mock group.")

                 await asyncio.sleep(GROUP_PAUSE_MS / 1000)





        # Send Mock (吐槽) danmaku group (uses default AUTO_SEND_DURATION_MS via _send_danmaku_group)

        if roast_danmaku_list:

            # Pass websocket to _send_danmaku_group for progress updates

            await _send_danmaku_group(roast_danmaku_list, "吐槽", websocket)





        logging.info(f"ws_danmaku_send_handlers: Auto-send sequence for '{streamer_name}' finished.")

        await websocket.send(json.dumps({"type": "success", "message": "自动发送完成。", "context": "auto_send_finished"}))



    except asyncio.CancelledError:

         logging.info("ws_danmaku_send_handlers: Auto-send task was cancelled.")

         await websocket.send(json.dumps({"type": "info", "message": "自动发送已取消。", "context": "auto_send_cancelled"}))



    except Exception as e:

        logging.error(f"ws_danmaku_send_handlers: Error during auto-send for '{streamer_name}' from {presenter_addr}: {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "error", "message": f"自动发送弹幕时出错: {e}", "action": "auto_send_danmaku", "context": "auto_send_error"}))



    finally:

        # Signal client to re-enable buttons (even on error or cancel)

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_finally_reenable"}))





async def handle_send_boss_danmaku(websocket, data):

    """

    Handles sending '欢迎大哥' (from Big_Brothers collection) or 
    '感谢大哥礼物' (from Gift_Thanks_Danmaku collection) danmaku.
    Uses specific BOSS_GIFT_DANMAKU_DURATION_MS (22 seconds) for these.
    data: {
        "danmaku_type": "welcome_boss" or "thanks_boss_gift",
        "boss_name": "xxx",
        "gift_name": "yyy" # Only for thanks_boss_gift
    }
    """
    presenter_addr = f"{websocket.remote_address}" if websocket else "N/A"

    logging.info(f"ws_danmaku_send_handlers: Received send_boss_danmaku action from {presenter_addr} with data: {data}")



    # Check dependencies using globals set by init

    if _broadcast_message is None: # Need broadcast function

        logging.error("ws_danmaku_send_handlers: Broadcast function not initialized. Cannot process send_boss_danmaku.")

        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：弹幕发送功能未初始化。", "context": "send_boss_init_error"}))

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_init_error_reenable"}))

        return



    # Check DB connection using helper

    if not _is_db_connected():

         logging.error("ws_danmaku_send_handlers: DB not connected. Cannot fetch danmaku for boss send.")

         await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法发送大哥弹幕。", "action": "send_boss_danmaku", "context": "send_boss_db_disconnected"}))

         await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_db_reenable"}))

         return





    # --- Input Validation ---

    danmaku_type = data.get("danmaku_type")

    boss_name = data.get("boss_name")

    gift_name = data.get("gift_name", "") # Default to empty string if not provided



    if danmaku_type not in ["welcome_boss", "thanks_boss_gift"]:

        logging.warning(f"ws_danmaku_send_handlers: Invalid danmaku_type received: {danmaku_type} from {presenter_addr}")

        await websocket.send(json.dumps({"type": "error", "message": "无效的弹幕类型。", "context": "send_boss_invalid_type"}))

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_invalid_type_reenable"}))

        return



    if not boss_name:

        logging.warning(f"ws_danmaku_send_handlers: Missing boss_name for {danmaku_type} from {presenter_addr}")

        await websocket.send(json.dumps({"type": "warning", "message": "请输入大哥昵称。", "context": "send_boss_missing_name"}))

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_missing_name_reenable"}))

        return



    if danmaku_type == "thanks_boss_gift" and not gift_name:

          logging.warning(f"ws_danmaku_send_handlers: Missing gift_name for thanks_boss_gift from {presenter_addr}")

          await websocket.send(json.dumps({"type": "warning", "message": "感谢礼物需要输入礼物名称。", "context": "send_boss_missing_gift"}))

          await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_missing_gift_reenable"}))

          return





    # --- Determine Collection and Labels ---

    collection_name = ""

    danmaku_type_label = "" # Used for logging and frontend messages



    if danmaku_type == "welcome_boss":

        collection_name = db_config.BIG_BROTHERS_COLLECTION # Fetches from Big_Brothers
        danmaku_type_label = "欢迎大哥"

    elif danmaku_type == "thanks_boss_gift":

        collection_name = db_config.GIFT_THANKS_COLLECTION # Fetches from Gift_Thanks_Danmaku
        danmaku_type_label = "感谢大哥礼物"



    # Send start message to client (disables UI buttons)

    await websocket.send(json.dumps({"type": "auto_send_started", "message": f"开始发送 {danmaku_type_label} 弹幕...", "context": f"send_boss_{danmaku_type}_started"}))



    # --- Fetch Danmaku from DB ---

    try:

        # Request 30 items as specified

        # Use the async facade function and await it

        danmaku_list = await get_random_danmaku(collection_name, 30)



        if not danmaku_list:

            logging.info(f"ws_danmaku_send_handlers: No '{danmaku_type_label}' danmaku found in collection '{collection_name}'.")

            await websocket.send(json.dumps({"type": "info", "message": f"数据库中没有找到{danmaku_type_label}弹幕。", "context": f"send_boss_{danmaku_type}_empty"}))

            await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": f"send_boss_{danmaku_type}_empty_reenable"}))

            return



        logging.info(f"ws_danmaku_send_handlers: Fetched {len(danmaku_list)} '{danmaku_type_label}' danmaku from '{collection_name}'.")



    except Exception as e:

        logging.error(f"ws_danmaku_send_handlers: Error fetching '{danmaku_type_label}' danmaku from DB for {presenter_addr}: {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "error", "message": f"获取弹幕时出错: {e}", "action": "send_boss_danmaku", "context": "send_boss_db_error"}))

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_db_error_reenable"}))

        return



    # --- Send Danmaku in Two Groups ---



    # Split into two groups (approximately)

    # Ensure danmaku_list only contains strings
    valid_danmaku_list = [item for item in danmaku_list if isinstance(item, str)]
    if not valid_danmaku_list:
        logging.warning(f"ws_danmaku_send_handlers: No valid string danmaku items found in fetched list for {danmaku_type_label} from {collection_name}.")
        await websocket.send(json.dumps({"type": "info", "message": f"获取到的{danmaku_type_label}弹幕内容无效。", "context": f"send_boss_{danmaku_type}_invalid_content"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": f"send_boss_{danmaku_type}_invalid_content_reenable"}))
        return
        
    group_size = len(valid_danmaku_list) // 2
    group1 = valid_danmaku_list[:group_size]
    group2 = valid_danmaku_list[group_size:]


    try:

        # Send Group 1 with specific duration for Boss/Gift danmaku
        logging.info(f"ws_danmaku_send_handlers: Sending Group 1 ({len(group1)} items) of '{danmaku_type_label}' for {boss_name} with {BOSS_GIFT_DANMAKU_DURATION_MS}ms duration each...")
        await _send_danmaku_group(group1, danmaku_type_label, websocket, boss_name, gift_name, specific_duration_ms=BOSS_GIFT_DANMAKU_DURATION_MS)


        # Pause between groups (3 seconds) if group2 exists
        if group2:
            logging.info(f"ws_danmaku_send_handlers: Pausing for {GROUP_PAUSE_MS / 1000} seconds between groups.")
            await asyncio.sleep(GROUP_PAUSE_MS / 1000)


        # Send Group 2 with specific duration for Boss/Gift danmaku
        if group2: # Only send if group2 has items
            logging.info(f"ws_danmaku_send_handlers: Sending Group 2 ({len(group2)} items) of '{danmaku_type_label}' for {boss_name} with {BOSS_GIFT_DANMAKU_DURATION_MS}ms duration each...")
            await _send_danmaku_group(group2, danmaku_type_label, websocket, boss_name, gift_name, specific_duration_ms=BOSS_GIFT_DANMAKU_DURATION_MS)


        # --- Send Completion Message ---

        logging.info(f"ws_danmaku_send_handlers: Finished sending '{danmaku_type_label}' danmaku for {boss_name}.")

        await websocket.send(json.dumps({"type": "auto_send_finished", "message": f"{danmaku_type_label}弹幕发送完成。", "context": f"send_boss_{danmaku_type}_finished"}))



    except asyncio.CancelledError:

        logging.info(f"ws_danmaku_send_handlers: Send boss danmaku task for {danmaku_type_label} was cancelled.")

        await websocket.send(json.dumps({"type": "info", "message": f"{danmaku_type_label}弹幕发送已取消。", "context": f"send_boss_{danmaku_type}_cancelled"}))



    except Exception as e:

        logging.error(f"ws_danmaku_send_handlers: Error sending '{danmaku_type_label}' danmaku for {boss_name} from {presenter_addr}: {e}", exc_info=True)

        await websocket.send(json.dumps({"type": "error", "message": f"发送弹幕时出错: {e}", "action": "send_boss_danmaku", "context": "send_boss_send_error"}))



    finally:

        # Signal client to re-enable buttons (even on error or cancel)

        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": f"send_boss_{danmaku_type}_finally_reenable"}))





# --- Registering Handlers (called by ws_core) ---

def register_danmaku_send_handlers():

    """Registers danmaku send-related WebSocket action handlers."""

    # Check if broadcast function is initialized (db_manager check is done by handlers using getter)

    if _broadcast_message is None:

        logging.error("ws_danmaku_send_handlers: Dependencies missing during handler registration. Send handlers will be unavailable.")

        return {}



    # Ensure here listed action names match frontend and handler function names

    handlers = {

        "auto_send_danmaku": handle_auto_send_danmaku, # Handles Welcome/Mock auto-send
        "send_boss_danmaku": handle_send_boss_danmaku, # Handles Welcome/Thanks Boss auto-send
    }

    logging.info(f"ws_danmaku_send_handlers: Registering send handlers: {list(handlers.keys())}")

    return handlers



# Expose necessary functions for server.py and ws_core.py

__all__ = [

    'init_danmaku_send_handlers',

    'register_danmaku_send_handlers',

]
