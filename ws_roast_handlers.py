# ws_roast_handlers.py

import logging
import json
import random
import re # Import re for string splitting
import asyncio # Import asyncio

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
    """
    Handles the request from the presenter to get a roast sequence for a target.
    Fetches quotes from the database and initializes the roast state.
    data: {"target_name": "黑粉昵称"}
    """
    presenter_addr = f"{websocket.remote_address}" if websocket else "N/A"
    logging.info(f"ws_roast_handlers: Presenter ({presenter_addr}) requested roast sequence for target: '{data.get('target_name')}'")

    target_name = data.get('target_name', '').strip()
    if not target_name:
        logging.warning(f"ws_roast_handlers: No target_name provided for roast sequence from {presenter_addr}.")
        await websocket.send(json.dumps({"type": "warning", "message": "请输入黑粉昵称以开始怼人。", "context": "roast_missing_target"}))
        # Signal client to re-enable buttons on error
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_missing_target_reenable"}))
        return

    if _db_manager is None:
         logging.error(f"ws_roast_handlers: DB manager not initialized. Cannot fetch roast quotes for {target_name}.")
         await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：数据库连接未初始化。", "context": "roast_db_init_error"}))
         await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_db_init_error_reenable"}))
         return

    # Send a message to the presenter indicating the process has started (optional, but good UX)
    await websocket.send(json.dumps({"type": "info", "message": f"正在获取 {target_name} 的怼人语录...", "context": "roast_fetching"}))


    try:
        # Fetch 3 anti-fan quotes from the database (as specified)
        # Assumes db_manager has a method fetch_anti_fan_quotes that returns a list of strings
        templates = await _db_manager.fetch_anti_fan_quotes(limit=3)

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

    current_state = _state_manager.get_state()
    current_index = current_state.get('current_roast_index', -1) + 1
    templates = current_state.get('current_roast_templates', [])
    total_templates = len(templates)
    target_name = current_state.get('current_roast_target_name', 'N/A')

    logging.info(f"ws_roast_handlers: Advance requested. Current Index BEFORE increment: {current_index-1}/{total_templates-1}. Target: {target_name}")


    if current_index >= total_templates:
        # Sequence finished naturally by advancing past the last item
        logging.info(f"ws_roast_handlers: Roast sequence for {target_name} finished naturally. Index {current_index} out of bounds {total_templates}.")
        _state_manager.exit_roast_sequence() # Reset state

        await websocket.send(json.dumps({
            "type": "roast_sequence_finished",
            "message": f"怼人序列完成！共 {total_templates} 条语录。",
            "target_name": target_name,
            "context": "roast_finished_natural"
        }))
        # Signal client to re-enable buttons after sequence finishes
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_finished_natural_reenable"}))
        # Frontend should request get_current_state here to restore script info


        return # Stop processing the advance


    # Get the current raw template string based on the new index
    raw_template = templates[current_index]
    logging.debug(f"ws_roast_handlers: Processing template #{current_index+1}: '{raw_template}'")

    # --- Implement Splitting Logic (by last full-width comma) ---
    danmaku_part = ""
    presenter_line = raw_template # Default: whole template is presenter line if no comma

    last_comma_index = raw_template.rfind('，') # Find the index of the last full-width comma

    if last_comma_index != -1: # If a full-width comma is found
        danmaku_part = raw_template[:last_comma_index].strip() # Part before the last comma
        presenter_line = raw_template[last_comma_index + 1:].strip() # Part after the last comma
        logging.debug(f"ws_roast_handlers: Split template. Danmaku: '{danmaku_part}', Prompt: '{presenter_line}'")
        if not danmaku_part:
             logging.warning(f"ws_roast_handlers: Roast template #{current_index+1} had no danmaku part before the comma: '{raw_template}'")
        if not presenter_line:
             logging.warning(f"ws_roast_handlers: Roast template #{current_index+1} had no prompt part after the comma: '{raw_template}'")
    else:
         # No full-width comma found, treat the whole string as the presenter line/prompt
         danmaku_part = "" # Send empty danmaku
         presenter_line = raw_template # Entire string is the prompt
         logging.warning(f"ws_roast_handlers: Roast template #{current_index+1} has no fullwidth comma '，': '{raw_template}'. Treating whole string as presenter part.")


    # --- Implement Parameter Replacement in Danmaku Part ---
    # Replace ALL occurrences of "{}" with the target name
    processed_danmaku = danmaku_part.replace("{}", target_name)
    logging.debug(f"ws_roast_handlers: Processed danmaku: '{processed_danmaku}' (replaced {{}} with {target_name})")


    # --- Update State Manager ---
    # Advance the state and store the processed data for the current step
    # The state manager's advance function now just increments the index and stores the parts for display/reference
    _state_manager.advance_roast_sequence(processed_danmaku, presenter_line, raw_template) # Pass processed data to state manager


    # --- Send Danmaku to Audience ---
    if processed_danmaku: # Only send danmaku if the processed danmaku part is not empty
         try:
             await _broadcast_message(
                "danmaku",
                {
                    "text": processed_danmaku,
                    "color": "#FF0000", # Red color for roast? (adjust as needed)
                    "size": "large", # Large size? (adjust as needed)
                    "position": "0", # Scrolling from right to left
                    "mode": 1, # Standard scrolling danmaku
                    "duration": ROAST_DANMAKU_DURATION_MS, # <-- Set the duration to 8 seconds as requested
                    "timestamp": time.time() # Add timestamp for audience sync if needed
                },
                client_type="audience" # Only send to audience clients
             )
             logging.info(f"ws_roast_handlers: Sent roast danmaku #{current_index+1}/{total_templates} to audience: '{processed_danmaku}' (Duration: {ROAST_DANMAKU_DURATION_MS}ms)")
         except Exception as e:
              logging.error(f"ws_roast_handlers: Error sending roast danmaku #{current_index+1} to audience: {e}", exc_info=True)
              # Decide how to handle send error - continue sequence or stop?
              # For now, log error and continue sequence. The status update below will signal presenter.


    else:
         logging.warning(f"ws_roast_handlers: No processed danmaku to send for template #{current_index+1}.")
         # Still send the presenter update even if danmaku is empty


    # --- Send Presenter Update Message ---
    # Send message to the presenter with the split prompt and other relevant info for the next step
    # Frontend handler for "presenter_roast_update" will update "Current Line", "Current Prompt", etc.
    await websocket.send(json.dumps({
        "type": "presenter_roast_update",
        "presenter_line": presenter_line, # Part after comma displayed as "Current Line" (presenter cue)
        "raw_template": raw_template, # Full raw template displayed as "Current Prompt" (or vice versa based on UI design)
        "current_roast_num": current_index + 1,
        "total_roasts": total_templates,
        "target_name": target_name,
        "context": "roast_update",
        # Optionally include the danmaku that was just sent for reference on presenter UI
        "danmaku_sent": processed_danmaku
    }))
    logging.debug(f"ws_roast_handlers: Presenter ('{presenter_addr}'): Sent roast update #{current_index+1}/{total_templates} for {target_name}. Presenter Line: '{presenter_line}'. Raw Template: '{raw_template}'")

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
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "roast_exit_init_error_reenable"})) # Signal client to re-enable buttons on error
        return

    # Exit the roast sequence state in State Manager
    current_target = _state_manager.get_state().get('current_roast_target_name', 'N/A')
    _state_manager.exit_roast_sequence()

    # Send confirmation message to presenter
    await websocket.send(json.dumps({
        "type": "roast_sequence_finished", # Use the same message type as finishing normally
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

