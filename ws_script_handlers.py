# ws_script_handlers.py

import logging
import os
from pathlib import Path
import json # Need json for sending messages

# Assume script_parser.py exists and has parse_script_file function
try:
    from script_parser import parse_script_file
except ImportError:
    logging.error("ws_script_handlers: Failed to import script_parser. Script parsing will be unavailable.")
    parse_script_file = None # Set to None if import fails

# Global references to dependencies
_state_manager = None
# _db_manager = None # REMOVED - Script handlers don't directly need DB manager instance now
# _broadcast_message = None # Assuming script navigation might trigger audience updates - Removed if not used

# Define the base directory for script browsing
# This should match the BASE_DIR used in server.py for serving static files
# We assume the scripts folder is a subdirectory of the base directory
BASE_DIR = Path(__file__).parent # Gets the directory where this ws_script_handlers.py file is located
SCRIPTS_DIR = BASE_DIR / "scripts" # Path to the 'scripts' subdirectory

# Ensure the scripts directory exists
if not SCRIPTS_DIR.exists():
    logging.warning(f"ws_script_handlers: Scripts directory not found at {SCRIPTS_DIR}. Script browsing will be empty.")
    # Attempt to create it if it doesn't exist, but only once
    try:
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        logging.info(f"ws_script_handlers: Created missing scripts directory at {SCRIPTS_DIR}.")
    except OSError as e:
        logging.error(f"ws_script_handlers: Failed to create scripts directory at {SCRIPTS_DIR}: {e}")


# Dictionary to track the current browsing path for each presenter client {websocket: current_path_str}
# This allows different presenters to browse different directories simultaneously
_presenter_browse_paths = {}


def init_script_handlers(state_manager_instance): # Removed db_manager_instance parameter
    """Initializes script handlers module with necessary dependencies."""
    logging.info("ws_script_handlers: Initializing script handlers module with dependencies.")
    global _state_manager # _db_manager removed
    _state_manager = state_manager_instance
    # _broadcast_message = broadcast_message_func # Uncomment if broadcast is needed

    logging.info("ws_script_handlers: Script handlers module initialized.")


async def handle_browse_script_path(websocket, data):
    """Handles the 'browse_script_path' action."""
    if _state_manager is None or parse_script_file is None:
        logging.error("ws_script_handlers: Handlers not initialized or parser missing. Cannot process browse_script_path.")
        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：脚本功能未初始化或解析器缺失。", "context": "browse_init"}))
        return

    req_path_str = data.get("path", ".") # Default to current directory '.'
    presenter_addr = websocket.remote_address

    logging.info(f"ws_script_handlers: Presenter {presenter_addr} requested script browse path: {req_path_str}")

    try:
        # Resolve the requested path relative to the SCRIPTS_DIR
        # Use resolve(strict=False) to handle '..', but check if it stays within SCRIPTS_DIR
        requested_path = (SCRIPTS_DIR / req_path_str).resolve(strict=False)

        # Security check: ensure the resolved path is within the SCRIPTS_DIR
        if not requested_path.is_relative_to(SCRIPTS_DIR) and requested_path != SCRIPTS_DIR:
             # Additional check for '..' resolving above base, resolve will catch simple cases but check explicitly
             # Check if the resolved path is *outside* the BASE_DIR completely (allowing SCRIPTS_DIR itself)
             if not str(requested_path).startswith(str(SCRIPTS_DIR)):
                 logging.warning(f"ws_script_handlers: Presenter {presenter_addr} attempted path traversal: {req_path_str} resolved to {requested_path}")
                 await websocket.send(json.dumps({"type": "error", "message": "无效的路径。", "context": "path_traversal"}))
                 # Send script options for the current valid path instead of an error
                 current_valid_path = _presenter_browse_paths.get(websocket, ".") # Get their last known valid path
                 await _send_script_options(websocket, current_valid_path)
                 return


        # If the resolved path is SCRIPTS_DIR itself, the relative path context is "."
        if requested_path == SCRIPTS_DIR:
            current_relative_path = "."
        else:
            # Otherwise, calculate the relative path from SCRIPTS_DIR
            current_relative_path = requested_path.relative_to(SCRIPTS_DIR).as_posix() # Use as_posix() for consistent path separators

        _presenter_browse_paths[websocket] = current_relative_path # Store the current valid path for this presenter

        # Send the updated options list for the new path
        await _send_script_options(websocket, current_relative_path)


    except Exception as e:
        logging.error(f"ws_script_handlers: Error browsing path '{req_path_str}' for {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"浏览目录时出错: {e}", "context": "browse_error"}))
        # On error, try to send options for the last known valid path
        current_valid_path = _presenter_browse_paths.get(websocket, ".")
        await _send_script_options(websocket, current_valid_path) # Attempt to send options for last good path


async def _send_script_options(websocket, relative_path_str):
    """Fetches and sends the list of items in a given relative path within SCRIPTS_DIR."""
    presenter_addr = websocket.remote_address
    full_path_to_browse = SCRIPTS_DIR / relative_path_str

    if not full_path_to_browse.exists(): # Check if path exists at all
         logging.warning(f"ws_script_handlers: Requested path does not exist: {full_path_to_browse}")
         await websocket.send(json.dumps({"type": "error", "message": "请求的路径不存在。", "context": "path_not_found"}))
         # Attempt to send options for the last known valid path
         current_valid_path = _presenter_browse_paths.get(websocket, ".")
         # Avoid potential infinite recursion if '.' itself is problematic.
         # This check might not be strictly necessary if the initial browse of '.' always works or fails fast.
         # Let's remove this recursive attempt on error for simplicity unless proven needed.
         # if relative_path_str != ".":
         #    await _send_script_options(websocket, current_valid_path)
         return

    if not full_path_to_browse.is_dir():
         logging.warning(f"ws_script_handlers: Requested path is not a directory: {full_path_to_browse}")
         await websocket.send(json.dumps({"type": "error", "message": "请求的路径不是一个目录。", "context": "not_a_directory"}))
         # Attempt to send options for the last known valid path. Similar to above, simplify.
         # current_valid_path = _presenter_browse_paths.get(websocket, ".")
         # if relative_path_str != current_valid_path:
         #    await _send_script_options(websocket, current_valid_path)
         return


    items_list = []
    breadcrumb_list = []

    try:
        # Get list of items in the directory
        logging.debug(f"ws_script_handlers: Browsing directory: {full_path_to_browse}") # DEBUG LOG
        raw_items = []
        try:
            raw_items = list(full_path_to_browse.iterdir())
        except Exception as e_iter:
            logging.error(f"ws_script_handlers: Error during iterdir for {full_path_to_browse}: {e_iter}", exc_info=True) # DEBUG LOG

        logging.debug(f"ws_script_handlers: Raw items found in {full_path_to_browse}: {[item.name for item in raw_items]}") # DEBUG LOG

        items_list = sorted([item.name for item in raw_items])

        # Build the options list for the frontend
        options = []
        # Add ".." option if not at the root SCRIPTS_DIR
        if relative_path_str != ".":
             # Calculate the path for ".." relative to SCRIPTS_DIR
             parent_path = full_path_to_browse.parent
             parent_relative_path = parent_path.relative_to(SCRIPTS_DIR).as_posix() if parent_path != SCRIPTS_DIR else "."
             options.append({"name": "../", "path": parent_relative_path, "type": "browse_dir"})


        for item_name in items_list:
            item_path = full_path_to_browse / item_name
            logging.debug(f"ws_script_handlers: Checking item: {item_path}, is_dir: {item_path.is_dir()}, is_file: {item_path.is_file()}, suffix: {item_path.suffix.lower()}") # DEBUG LOG
            # Calculate the relative path of the item from SCRIPTS_DIR
            try:
                 item_relative_path = item_path.relative_to(SCRIPTS_DIR).as_posix()
            except ValueError:
                 logging.warning(f"ws_script_handlers: Failed to calculate relative path for item {item_path}. Skipping.")
                 continue # Skip this item

            if item_path.is_dir():
                options.append({"name": f"{item_name}/", "path": item_relative_path, "type": "browse_dir"})
            elif item_path.is_file() and item_path.suffix.lower() == ".txt": # Only list .txt files as scripts
                options.append({"name": item_name, "path": item_relative_path, "type": "script_file"})

        # Build the breadcrumb path
        # Split the relative path and build breadcrumb names
        path_parts = relative_path_str.split('/')
        current_breadcrumb_path_str = ""
        breadcrumb_list.append({"name": "脚本根目录", "path": "."}) # Link for root

        # Build breadcrumb for subdirectories
        # Join parts incrementally to build paths
        cumulative_path_parts = []
        for part in path_parts:
            if part and part != '.': # Ignore empty parts and the initial '.'
                 cumulative_path_parts.append(part)
                 # Join parts with '/' and use as_posix()
                 breadcrumb_path = Path(*cumulative_path_parts).as_posix()
                 breadcrumb_list.append({"name": part, "path": breadcrumb_path})


        message = {
            "type": "script_options_update",
            "current_path": relative_path_str, # Send the relative path string
            "breadcrumb": breadcrumb_list, # Send list of {name, path} dicts for breadcrumb
            "options": options
        }
        await websocket.send(json.dumps(message))
        logging.info(f"ws_script_handlers: Sent script options for '{relative_path_str}' to {presenter_addr}. Found {len(options)} items.")

    except Exception as e:
        logging.error(f"ws_script_handlers: Error sending script options for '{relative_path_str}' to {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"获取脚本列表时出错: {e}", "context": "list_scripts_error"}))


async def handle_load_script(websocket, data):
    """Handles the 'load_script' action."""
    if _state_manager is None or parse_script_file is None:
         logging.error("ws_script_handlers: Handlers not initialized or parser missing. Cannot process load_script.")
         await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：脚本功能未初始化或解析器缺失。", "context": "load_init"}))
         return


    script_relative_path_str = data.get("filename") # This should be the relative path from the frontend
    presenter_addr = websocket.remote_address

    if not script_relative_path_str:
        logging.warning(f"ws_script_handlers: Presenter {presenter_addr} sent load_script with no filename.")
        await websocket.send(json.dumps({"type": "error", "message": "未提供脚本文件名。", "context": "load_no_filename"}))
        return

    # Resolve the full path, ensuring it is within the SCRIPTS_DIR
    script_full_path = (SCRIPTS_DIR / script_relative_path_str).resolve(strict=False)

    # Security check: ensure the resolved path is within the SCRIPTS_DIR
    if not script_full_path.is_relative_to(SCRIPTS_DIR):
        logging.warning(f"ws_script_handlers: Presenter {presenter_addr} attempted to load script outside SCRIPTS_DIR: {script_relative_path_str} resolved to {script_full_path}")
        await websocket.send(json.dumps({"type": "error", "message": "无效的脚本文件路径。", "context": "load_path_traversal"}))
        return

    if not script_full_path.is_file():
        logging.warning(f"ws_script_handlers: Presenter {presenter_addr} attempted to load path that is not a file: {script_full_path}")
        await websocket.send(json.dumps({"type": "error", "message": "请求的路径不是一个文件。", "context": "load_not_a_file"}))
        return

    if script_full_path.suffix.lower() != ".txt":
         logging.warning(f"ws_script_handlers: Presenter {presenter_addr} attempted to load non-.txt file as script: {script_full_path}")
         await websocket.send(json.dumps({"type": "error", "message": "仅支持加载 .txt 文件。", "context": "load_wrong_type"}))
         return


    logging.info(f"ws_script_handlers: Presenter {presenter_addr} requested to load script: {script_full_path}")

    # Load the script using the state manager
    success = _state_manager.load_script(script_full_path)

    if success:
        logging.info(f"ws_script_handlers: Script '{script_relative_path_str}' loaded by {presenter_addr}.")
        # Send the initial state of the loaded script back to the presenter
        current_state = _state_manager.get_current_state()
        # Modify state data for presenter-specific message if needed, or reuse generic
        # Let's reuse get_current_state and send a specific message type for the presenter
        await websocket.send(json.dumps({"type": "script_loaded_presenter", **current_state}))

        # Optional: Notify audience page that a new script is loaded (if audience needs to know filename)
        # This would require a broadcast to audience clients - needs broadcast_message dependency
        # If audience display updates based on explicit 'audience_display' messages triggered by presenter navigation,
        # then loading a script doesn't need to trigger audience update immediately unless it automatically goes to index 0.
        # The advance/prev handlers broadcast updates. Let's rely on that.
        # If audience needs to know script name on load:
        # if _broadcast_message: # Check if broadcast is initialized
        #      await _broadcast_message("audience", {"type": "script_loaded", "script_name": _state_manager.get_current_state().get("script_filename", "新的脚本")})


    else:
        logging.error(f"ws_script_handlers: Failed to load script '{script_full_path}' for {presenter_addr}.")
        await websocket.send(json.dumps({"type": "error", "message": f"加载脚本时出错: {script_full_path}", "context": "load_script_error"}))
        # Also send an empty state update to clear frontend if loading failed
        await websocket.send(json.dumps({"type": "script_loaded_presenter", "script_filename": None, "total_events": 0, "event_index": -1, "current_line": "", "current_prompt": ""}))


async def handle_prev_event(websocket, data):
    """Handles the 'prev_event' action."""
    if _state_manager is None:
         logging.error("ws_script_handlers: State manager not initialized. Cannot process prev_event.")
         await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：状态管理器缺失。", "context": "prev_init"}))
         return

    presenter_addr = websocket.remote_address
    logging.info(f"ws_script_handlers: Presenter {presenter_addr} requested prev_event.")

    try:
        new_index = _state_manager.prev_event()
        current_state = _state_manager.get_current_state()

        # Send state update to the presenter who triggered the action
        # Using presenter_generic_update for navigation updates
        await websocket.send(json.dumps({"type": "presenter_generic_update", **current_state}))

        # Optional: Broadcast the new state to audience clients if they need to update display
        # This might be redundant if audience only cares about the *current* line/prompt being displayed
        # and presenter_generic_update is not needed for audience.
        # If audience needs *any* update on presenter navigation, broadcast here.
        # Let's assume audience display updates based on explicit 'audience_display' message types sent by core/server
        # Need the broadcast_message function for this. Add it to init if needed.
        # Or, Audience JS should request state if needed.
        # If _broadcast_message is available and audience needs updates:
        # if _broadcast_message:
        #      await _broadcast_message("audience", {"type": "audience_display", "line": current_state.get("current_line", ""), "prompt": current_state.get("current_prompt", "")})


        logging.info(f"ws_script_handlers: Presenter {presenter_addr} moved to prev event: index {new_index}.")

    except Exception as e:
        logging.error(f"ws_script_handlers: Error processing prev_event for {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"导航到上一条出错: {e}", "context": "prev_event_error"}))


async def handle_next_event(websocket, data):
    """Handles the 'next_event' action."""
    if _state_manager is None:
         logging.error("ws_script_handlers: State manager not initialized. Cannot process next_event.")
         await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：状态管理器缺失。", "context": "next_init"}))
         return

    presenter_addr = websocket.remote_address
    logging.info(f"ws_script_handlers: Presenter {presenter_addr} requested next_event.")


    try:
        new_index = _state_manager.advance_event()
        current_state = _state_manager.get_current_state()

        # Send state update to the presenter who triggered the action
        await websocket.send(json.dumps({"type": "presenter_generic_update", **current_state}))

        # Optional: Broadcast the new state to audience clients
        # If _broadcast_message is available and audience needs updates:
        # if _broadcast_message:
        #      await _broadcast_message("audience", {"type": "audience_display", "line": current_state.get("current_line", ""), "prompt": current_state.get("current_prompt", "")})


        if new_index >= _state_manager._total_events: # Check if index is past or at the last event
            logging.info(f"ws_script_handlers: Presenter {presenter_addr} reached end of script.")
            # Optionally send an explicit 'end_of_script' message
            await websocket.send(json.dumps({"type": "end_of_script", "message": "脚本播放完毕。"}))
            # If audience needs notification of script end:
            # if _broadcast_message:
            #      await _broadcast_message("audience", {"type": "info", "text": "脚本播放完毕。", "duration_ms": 5000})


        logging.info(f"ws_script_handlers: Presenter {presenter_addr} moved to next event: index {new_index}.")


    except Exception as e:
        logging.error(f"ws_script_handlers: Error processing next_event for {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"导航到下一条出错: {e}", "context": "next_event_error"}))


async def handle_get_current_event_for_presenter(websocket, data):
    """
    Handles the 'get_current_event_for_presenter' action.
    Sends the current script state back to the requesting presenter.
    Useful for syncing UI on reconnect or exiting modes.
    """
    if _state_manager is None:
         logging.error("ws_script_handlers: State manager not initialized. Cannot process get_current_event_for_presenter.")
         await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：状态管理器缺失。", "context": "get_state_init"}))
         return

    presenter_addr = websocket.remote_address
    logging.info(f"ws_script_handlers: Presenter {presenter_addr} requested current state.")

    try:
        current_state = _state_manager.get_current_state()
        # Send the state specifically using the presenter-specific message type
        await websocket.send(json.dumps({"type": "script_loaded_presenter", **current_state})) # Reuse type for initial load

    except Exception as e:
        logging.error(f"ws_script_handlers: Error processing get_current_event_for_presenter for {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"获取当前状态出错: {e}", "context": "get_state_error"}))


# --- Helper for initial browse on presenter connect ---
async def send_initial_script_options(websocket):
    """Sends the initial script options for the root directory to a newly connected presenter."""
    # This function is called by server.py after presenter registration
    # Set their initial browse path context to root
    _presenter_browse_paths[websocket] = "."
    await _send_script_options(websocket, ".")

# --- Helper for clearing browse path on presenter disconnect ---
def clear_presenter_browse_path(websocket):
    """Removes the presenter's browsing path context on disconnect."""
    if websocket in _presenter_browse_paths:
        del _presenter_browse_paths[websocket]
        logging.debug(f"ws_script_handlers: Cleared browse path for {websocket.remote_address}.")


# --- Registering Handlers (called by ws_core) ---
def register_script_handlers():
    """Registers script-related WebSocket action handlers."""
    # Check if state manager is initialized
    if _state_manager is None:
        logging.error("ws_script_handlers: State manager not initialized during handler registration. Script handlers will be unavailable.")
        return {}


    handlers = {
        "browse_scripts": handle_browse_script_path,
        "load_script": handle_load_script,
        "prev_event": handle_prev_event,
        "next_event": handle_next_event,
        "get_current_state": handle_get_current_event_for_presenter,
    }
    logging.info(f"ws_script_handlers: Registering script handlers: {list(handlers.keys())}")
    return handlers

# Expose necessary functions for server.py and ws_core.py
__all__ = [
    'init_script_handlers',
    'register_script_handlers',
    'send_initial_script_options', # Called by server.py after registration
    'clear_presenter_browse_path', # Called by ws_core.py on disconnect
    # handle_get_current_event_for_presenter is needed by server.py's initial sync logic
    'handle_get_current_event_for_presenter', # Called by server.py after initial registration
]
