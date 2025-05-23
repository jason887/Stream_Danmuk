# ws_roast_handlers.py

import logging
import json
import random
import re # Import re for string splitting
import asyncio # Import asyncio
import time # FIX: 添加这一行，导入 time 模块
from database import get_db_manager, db_config, fetch_anti_fan_quotes # 新增导入语句

# Global references to dependencies
# These will be assigned by the init_roast_handlers function
_state_manager = None
_db_manager = None
_broadcast_message = None

# Define the danmaku duration for roast mode (8 seconds as requested)
ROAST_DANMAKU_DURATION_MS = 8000

# Define the collection for roast quotes (Synchronize with db_manager)
ANTI_FAN_COLLECTION = "Anti_Fan_Quotes"


def init_roast_handlers(state_manager_instance, db_manager_instance, broadcast_message_func):
    """
    Initializes the global dependencies for the roast handlers module.
    Called by server.py during application startup.
    """
    global _state_manager, _db_manager, _broadcast_message
    _state_manager = state_manager_instance
    _db_manager = db_manager_instance
    _broadcast_message = broadcast_message_func
    logging.info("ws_roast_handlers: Roast handlers module initialized.")


async def handle_get_roast_sequence(websocket, data):
    presenter_addr = f"{websocket.remote_address}" if websocket else "N/A"
    target_name = data.get('target_name', '').strip()
    if not target_name:
        logging.warning(f"ws_roast_handlers: No target_name provided for roast sequence from {presenter_addr}.")
        await websocket.send(json.dumps({"type": "warning", "message": "请输入黑粉昵称以开始怼人。", "context": "roast_missing_target"}))
        # Signal client to re-enable buttons on error
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_missing_target_reenable"}))
        return

    logging.info(f"ws_roast_handlers: Presenter ({presenter_addr}) requested roast sequence for target: '{target_name}'")

    try:
        templates = fetch_anti_fan_quotes(limit=3)
    except Exception as e:
        logging.error(f"ws_roast_handlers: Error fetching anti-fan quotes for roast sequence from {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"获取怼人语录时出错: {e}", "action": "get_roast_sequence", "context": "roast_fetch_error"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_fetch_error_reenable"}))
        return

    if not templates:
        logging.info(f"ws_roast_handlers: No anti-fan quotes found in collection '{ANTI_FAN_COLLECTION}'.")
        await websocket.send(json.dumps({"type": "info", "message": "数据库中没有找到怼黑粉语录。", "context": "roast_empty_db"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_empty_db_reenable"}))
        return

    # 启动怼黑粉序列
    _state_manager.start_roast_sequence(target_name, templates)

    # 获取并发送第一条语录的内容到前端，以便 UI 立即显示
    first_danmaku_part, first_presenter_line, first_raw_template, first_num, first_total = _state_manager.get_next_roast_template()

    if first_danmaku_part is None:
        logging.error(f"ws_roast_handlers: Failed to get first roast template for {target_name}. Templates: {templates}")
        await websocket.send(json.dumps({"type": "error", "message": "无法获取第一条语录，请检查数据。", "context": "roast_first_template_error"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_first_template_error_reenable"}))
        _state_manager.exit_roast_sequence()  # 清理状态
        return

    await websocket.send(json.dumps({
        "type": "roast_sequence_ready",
        "target_name": target_name,
        "total_roasts": len(templates),
        "message": f"已加载 {len(templates)} 条语录。",
        "context": "roast_ready",
        # 添加初始语录内容，让前端立即显示
        "initial_presenter_line": first_presenter_line,
        "initial_raw_template": first_raw_template,
        "initial_roast_num": first_num,
        "initial_total_roasts": first_total
    }))
    logging.info(f"ws_roast_handlers: Roast sequence for target '{target_name}' loaded with {len(templates)} templates. Ready to advance. From {presenter_addr}.")

    if _db_manager is None: # This check remains relevant if _db_manager is used elsewhere for connection status
        logging.error(f"ws_roast_handlers: DB manager not initialized. Cannot fetch roast quotes for {target_name}.")
        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：数据库连接未初始化。", "context": "roast_db_init_error"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_db_init_error_reenable"}))
        return

    # Send a message to the presenter indicating the process has started (optional, but good UX)
    await websocket.send(json.dumps({"type": "info", "message": f"正在获取 {target_name} 的怼人语录...", "context": "roast_fetching"}))


    try:
        # FIX: Call the facade function directly, and remove 'await' because fetch_anti_fan_quotes is synchronous
        templates = fetch_anti_fan_quotes(limit=3)

        if not templates:
            logging.info(f"ws_roast_handlers: No anti-fan quotes found in collection '{ANTI_FAN_COLLECTION}'.")
            await websocket.send(json.dumps({"type": "info", "message": "数据库中没有找到怼黑粉语录。", "context": "roast_empty_db"}))
            await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_empty_db_reenable"}))
            return

        logging.info(f"ws_roast_handlers: Fetched {len(templates)} anti-fan quotes for roast sequence.")

        # Initialize roast sequence state in State Manager
        # State manager stores the raw templates list and target name
        _state_manager.start_roast_sequence(target_name, templates)

        # Send confirmation message to presenter indicating readiness
        await websocket.send(json.dumps({
            "type": "roast_sequence_ready",
            "target_name": target_name,
            "total_roasts": len(templates),
            "message": f"已加载 {len(templates)} 条语录。", # Message for status display
            "context": "roast_ready"
        }))
        logging.info(f"ws_roast_handlers: Roast sequence for target '{target_name}' loaded with {len(templates)} templates. Ready to advance. From {presenter_addr}.")

        # The frontend handler for "roast_sequence_ready" will update the UI
        # (hide start button, show advance/exit buttons, re-enable them via re_enable_auto_send_buttons).


    except Exception as e:
        logging.error(f"ws_roast_handlers: Error fetching anti-fan quotes for roast sequence from {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"获取怼人语录时出错: {e}", "action": "get_roast_sequence", "context": "roast_fetch_error"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_fetch_error_reenable"}))


async def handle_advance_roast_sequence(websocket, data):
    """ 
    Handles the request to send the current roast danmaku and get the next prompt. 
    Called by presenter when clicking the "Send Danmaku and Next Prompt" button. 
    data: {} (no specific data needed from frontend) 
    """ 
    presenter_addr = f"{websocket.remote_address}" if websocket else "N/A" 
    logging.info(f"ws_roast_handlers: Presenter ({presenter_addr}) requested advance roast sequence.") 
 
    if _state_manager is None or _broadcast_message is None: 
        logging.error(f"ws_roast_handlers: Dependencies missing. Cannot advance roast sequence from {presenter_addr}.") 
        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：状态管理或广播功能未初始化。", "context": "roast_advance_init_error"})) 
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_advance_init_error_reenable"})) # Signal client to re-enable buttons on error 
        return 
 
    # 从 _state_manager.get_current_state() 中获取 target_name
    current_state = _state_manager.get_current_state()
    target_name = current_state.get('current_roast_target_name', 'N/A')

    # 调用 _state_manager.get_next_roast_template() 来获取下一条文案数据 
    danmaku_part_to_send, presenter_line_to_display, raw_template_for_display, current_num, total_num = _state_manager.get_next_roast_template() 

    if danmaku_part_to_send is None: # 表示序列已结束 
        current_state = _state_manager.get_current_state()
        target_name = current_state.get('current_roast_target_name', 'N/A')
        logging.info(f"ws_roast_handlers: Roast sequence for {target_name} finished naturally. Index {current_num} out of bounds {total_num}.") 
        _state_manager.exit_roast_sequence() # Reset state 
        await websocket.send(json.dumps({ 
            "type": "roast_sequence_finished", 
            "message": f"怼人序列完成！共 {total_num} 条语录。", 
            "target_name": target_name, 
            "context": "roast_finished_natural" 
        })) 
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_finished_natural_reenable"})) 
        return 
 
    # 3. 发送弹幕到观众端 
    if danmaku_part_to_send: 
        logging.debug(f"DEBUG: Final danmaku_part_to_send: '{danmaku_part_to_send}'") # 添加这一行 
        try: 
            await _broadcast_message( 
                "audience", # FIX: 第一个参数就是 target_type，设置为 "audience" 
                { 
                    "type": "danmaku", # 消息类型 
                    "text": danmaku_part_to_send, 
                    "color": "#FF0000", # 红色的怼人弹幕 
                    "size": "large", 
                    "position": "0", # 滚动 
                    "mode": 1, 
                    "duration_ms": ROAST_DANMAKU_DURATION_MS, 
                    "is_roast": True, # 标记为怼黑粉弹幕，方便前端样式区分 
                    "timestamp": time.time() 
                }
                # 移除 client_type="audience" 这个多余的参数 
            ) 
            logging.info(f"ws_roast_handlers: Sent roast danmaku #{current_num}/{total_num} to audience: '{danmaku_part_to_send}' (Duration: {ROAST_DANMAKU_DURATION_MS}ms)") 
        except Exception as e: 
            logging.error(f"ws_roast_handlers: Error sending roast danmaku #{current_num} to audience: {e}", exc_info=True) 
    else: 
        logging.warning(f"ws_roast_handlers: No processed danmaku to send for template #{current_num}.") 

    # --- Send Presenter Update Message ---
    # Send message to the presenter with the split prompt and other relevant info for the next step
    # Frontend handler for "presenter_roast_update" will update "Current Line", "Current Prompt", etc.
    await websocket.send(json.dumps({
        "type": "presenter_roast_update",
        "presenter_line": presenter_line_to_display, # Part after comma displayed as "Current Line" (presenter cue)
        "raw_template": raw_template_for_display, # Full raw template displayed as "Current Prompt" (or vice versa based on UI design)
        "current_roast_num": current_num,
        "total_roasts": total_num,
        "target_name": target_name, 
        "context": "roast_update",
        # Optionally include the danmaku that was just sent for reference on presenter UI
        "danmaku_sent": danmaku_part_to_send
    }))
    logging.debug(f"ws_roast_handlers: Presenter ('{presenter_addr}'): Sent roast update #{current_num}/{total_num} for {target_name}. Presenter Line: '{presenter_line_to_display}'. Raw Template: '{raw_template_for_display}'")


    # Re-enable advance and exit buttons on the frontend. This is typically handled
    # by the frontend handler receiving "presenter_roast_update". If the handler
    # doesn't do this, you might need to send a specific re-enable message here,
    # but the design assumes "presenter_roast_update" signals step completion allowing next action.


async def handle_exit_roast_mode(websocket, data): 
    """ 
    Handles the request from the presenter to exit the roast mode. 
    Resets the roast state in the state manager. 
    """ 
    presenter_addr = f"{websocket.remote_address}" if websocket else "N/A" 
    logging.info(f"ws_roast_handlers: Presenter ({presenter_addr}) requested to exit roast mode.") 
 
    if _state_manager is None: 
        logging.error(f"ws_roast_handlers: State manager not initialized. Cannot exit roast mode.") 
        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：状态管理未初始化。", "context": "roast_exit_init_error"})) 
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_exit_init_error_reenable"})) 
        return 
 
    # FIX: Change get_state() to get_current_state() 
    current_target = _state_manager.get_current_state().get('current_roast_target', 'N/A') # 注意这里也从 'current_roast_target_name' 改为 'current_roast_target'，保持和 get_current_state 返回的键一致 
    _state_manager.exit_roast_sequence() 
 
    # Send confirmation message to presenter
    await websocket.send(json.dumps({
        "type": "roast_sequence_finished", # Use the same message type as finishing naturally
        "message": f"已退出对 {current_target} 的怼人模式。",
        "target_name": current_target, # Include target name for frontend context
        "context": "roast_exit"
    }))
    logging.info(f"ws_roast_handlers: Exited roast mode for {current_target}. Sent roast_sequence_finished to {presenter_addr}.")

    # Signal client to re-enable buttons (start roast, script nav, etc.)
    # This is crucial after exiting any modal state.
    await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_exit_reenable"}))

    # Frontend should request 'get_current_state' after receiving 'roast_sequence_finished'
    # to update script display area from roast info back to script info.
    logging.info("ws_roast_handlers: Frontend should request get_current_state after exiting roast mode to restore script UI.")


# --- Register Roast Handlers ---
# This function is called by ws_core.py during its initialization.
# It should return a dictionary mapping action names to the corresponding async handler functions.
def register_roast_handlers():
    """
    Registers the WebSocket handlers for roast mode actions.
    Returns a dictionary of action names mapped to handler functions.
    """
    logging.info("ws_roast_handlers: Registering roast handlers.")
    handlers = {
        "get_roast_sequence": handle_get_roast_sequence, # Action to start fetching roast quotes
        "advance_roast": handle_advance_roast_sequence,     # Action to send the current roast danmaku and get next prompt
        "exit_roast_mode": handle_exit_roast_mode,         # Action to exit the roast mode
        # Add other roast-related actions and their handlers here if any
    }
    logging.info(f"ws_roast_handlers: Registered handlers: {list(handlers.keys())}")
    return handlers


# Expose the registration function for ws_core.py
__all__ = [
    'init_roast_handlers',
    'register_roast_handlers',
]

