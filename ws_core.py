# ws_core.py
import asyncio
import json
import logging
import traceback
import time # Import time for tracking client activity

# Constants for heartbeat and timeout
PING_INTERVAL = 30 # Send PING every 30 seconds
TIMEOUT_DURATION = PING_INTERVAL * 2 # Consider client timed out after 60 seconds without activity

# Global sets to store connected clients
# Each element is the websocket connection object
PRESENTER_CLIENTS = set()
AUDIENCE_CLIENTS = set()

# Dictionary to track last activity time for clients {websocket: timestamp}
# Activity includes receiving messages or successful PONG replies
CLIENT_LAST_ACTIVITY = {}

# Global dictionary to hold registered action handlers {action_name: handler_function}
# Handlers are expected to be async functions with the signature: async def handler(websocket, data)
ACTION_HANDLERS = {}

# Global reference to the send_message_to_ws_func from server.py for error reporting
_SEND_MESSAGE_FUNC = None

# Global reference to the broadcast function from server.py for broadcasting specific core messages
_BROADCAST_MESSAGE_FUNC = None


def init_ws_core(send_message_to_ws_func, broadcast_message_func, *handler_registration_funcs): 
    """ 
    Initializes the core WebSocket message dispatcher and client management. 
    Stores send_message_to_ws_func for error reporting and broadcast_message_func for core messages.
    Dependencies (DB, state) for specific action handlers are assumed to be initialized and available
    as module-level globals within the respective handler modules (via their own init functions
    called by server.py BEFORE init_ws_core).
    """ 
    logging.info("ws_core: Initializing core WebSocket dispatcher and client management.") 
    global ACTION_HANDLERS, _SEND_MESSAGE_FUNC, _BROADCAST_MESSAGE_FUNC 
    _SEND_MESSAGE_FUNC = send_message_to_ws_func 
    _BROADCAST_MESSAGE_FUNC = broadcast_message_func 
    ACTION_HANDLERS = {} 
 
    # Register core actions 
    ACTION_HANDLERS["register"] = handle_register_client 
    ACTION_HANDLERS["pong"] = handle_pong 
 
    # Loop through all provided registration functions and call them 
    for register_func in handler_registration_funcs: 
        try: 
            # Each registration function should return a dict of {action: handler_async_func} 
            handlers_dict = register_func() # Call the registration function 
 
            # Optional: Check for duplicate action names across modules 
            for action in handlers_dict: 
                if action in ACTION_HANDLERS: 
                    logging.warning(f"ws_core: Action '{action}' from {register_func.__module__} is already registered. Overwriting.") 
 
            ACTION_HANDLERS.update(handlers_dict) 
            module_name = register_func.__module__ if hasattr(register_func, '__module__') else 'UnknownModule' 
            logging.info(f"ws_core: Registered handlers from {module_name}. Total handlers: {len(ACTION_HANDLERS)}") 
        except Exception as e: 
            logging.error(f"ws_core: Error registering handlers from {register_func}: {e}", exc_info=True) 
            # Continue to register other handlers even if one fails 
 
    logging.info(f"ws_core: WebSocket core initialized with {len(ACTION_HANDLERS)} action handlers.") 


async def register_client(websocket, client_type):
    """Registers a new client connection by type."""
    addr = websocket.remote_address
    is_presenter = websocket in PRESENTER_CLIENTS
    is_audience = websocket in AUDIENCE_CLIENTS

    if client_type == "presenter":
        if not is_presenter:
            PRESENTER_CLIENTS.add(websocket)
            CLIENT_LAST_ACTIVITY[websocket] = time.time() # Record initial activity
            logging.info(f"ws_core: Presenter client registered: {addr}. Total presenters: {len(PRESENTER_CLIENTS)}")
            # Send confirmation back
            if _SEND_MESSAGE_FUNC:
                 await _SEND_MESSAGE_FUNC(websocket, {"type": "registration_success", "client_type": client_type, "message": "Presenter registered successfully."})

            # --- Trigger initial state sync for presenter ---
            # This is now handled in server.py after successful registration message is received.
            # No action needed here.

            return True
        else:
            # Client already registered (shouldn't happen often with unique websocket objects)
            logging.warning(f"ws_core: Client {addr} attempted to re-register as Presenter.")
            if _SEND_MESSAGE_FUNC:
                 await _SEND_MESSAGE_FUNC(websocket, {"type": "warning", "message": f"已注册为 {client_type}", "context": "re_registration"})
            return False

    elif client_type == "audience":
         if not is_audience:
            AUDIENCE_CLIENTS.add(websocket)
            CLIENT_LAST_ACTIVITY[websocket] = time.time() # Record initial activity
            logging.info(f"ws_core: Audience client registered: {addr}. Total audience: {len(AUDIENCE_CLIENTS)}")
             # Send confirmation back
            if _SEND_MESSAGE_FUNC:
                 await _SEND_MESSAGE_FUNC(websocket, {"type": "registration_success", "client_type": client_type, "message": "Audience registered successfully."})

            # --- Trigger initial state sync for audience ---
            # Audience might need the current state of the script display (line/prompt)
            # Requesting this from state manager and broadcasting the current audience display message
            # This needs the state manager and broadcast function, which are module globals here.
            # Let's trigger a broadcast of the *current* audience display state if it exists
            # The state manager holds the current script state. We need to translate it to an audience_display message.
            # This logic might fit better in ws_script_handlers if that module handles audience state.
            # Or, Audience JS should send a 'get_current_display_state' action after registration.
            # Let's assume Audience JS requests it or waits for presenter updates for simplicity.

            return True
         else:
             logging.warning(f"ws_core: Client {addr} attempted to re-register as Audience.")
             if _SEND_MESSAGE_FUNC:
                 await _SEND_MESSAGE_FUNC(websocket, {"type": "warning", "message": f"已注册为 {client_type}", "context": "re_registration"})
             return False

    else:
        logging.warning(f"ws_core: Attempted to register client {addr} with unknown type: {client_type}")
        if _SEND_MESSAGE_FUNC:
            await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": f"未知客户端类型: {client_type}", "context": "registration_error"})
        return False


async def unregister_client(websocket):
    """Unregisters a client connection."""
    addr = websocket.remote_address
    is_presenter = websocket in PRESENTER_CLIENTS
    is_audience = websocket in AUDIENCE_CLIENTS

    removed = False
    if is_presenter:
        try:
            PRESENTER_CLIENTS.remove(websocket)
            logging.info(f"ws_core: Presenter client {addr} removed from set. Total presenters: {len(PRESENTER_CLIENTS)}")
            removed = True
        except KeyError:
            logging.debug(f"ws_core: Presenter client {addr} not found in set during unregister.") # Already removed

    if is_audience:
        try:
            AUDIENCE_CLIENTS.remove(websocket)
            logging.info(f"ws_core: Audience client {addr} removed from set. Total audience: {len(AUDIENCE_CLIENTS)}")
            removed = True
        except KeyError:
            logging.debug(f"ws_core: Audience client {addr} not found in set during unregister.") # Already removed


    if websocket in CLIENT_LAST_ACTIVITY:
        try:
            del CLIENT_LAST_ACTIVITY[websocket] # Remove activity tracking
            logging.debug(f"ws_core: Removed activity tracking for {addr}.")
        except KeyError:
             logging.debug(f"ws_core: Activity tracking for {addr} not found during unregister.") # Already removed


    if not removed:
        logging.info(f"ws_core: Unregistered or unknown client disconnected: {addr}")
    else:
        logging.info(f"ws_core: Client {addr} disconnect handling finished. Current connected clients: Presenters: {len(PRESENTER_CLIENTS)}, Audience: {len(AUDIENCE_CLIENTS)}")

    # Clear presenter-specific states like browse path if it's a presenter
    # This needs a call to ws_script_handlers if it manages that state
    # Assumes ws_script_handlers.clear_presenter_browse_path exists and accepts websocket
    try:
         from ws_script_handlers import clear_presenter_browse_path # Import here to avoid circular dependency on module level
         clear_presenter_browse_path(websocket)
         logging.debug(f"ws_core: Cleared script browse path for {addr}.")
    except ImportError:
         logging.error("ws_core: Could not import clear_presenter_browse_path. Script browse state might not be cleared on disconnect.")
    except Exception as e:
         logging.error(f"ws_core: Error clearing script browse path for {addr}: {e}")


# This broadcast_message function is intended for other handler modules to use
# It uses the internal _BROADCAST_MESSAGE_FUNC provided by server.py
async def broadcast_message(target_type, message):
    """Broadcasts a message to all connected clients of a specific type or all clients."""
    if _BROADCAST_MESSAGE_FUNC is None:
        logging.error("ws_core: Broadcast function not initialized. Cannot broadcast message.")
        # Optionally send an error back to presenters if broadcast is critical?
        # For now, just log on server side.
        return

    # Ensure the message is a dictionary before passing
    if not isinstance(message, dict):
        logging.error(f"ws_core: Attempted to broadcast non-dictionary message: {message}")
        # Cannot broadcast error back universally, just log
        return

    # Add a timestamp for potential client-side display sync/debugging - server helper adds this
    # If "timestamp" not in message:
    #     message["timestamp"] = time.time()

    # Use the broadcast function provided during initialization
    # The provided function should handle JSON dumping and sending to correct group(s)
    await _BROADCAST_MESSAGE_FUNC(target_type, message)


async def handle_register_client(websocket, data):
    """Handles the 'register' action."""
    # This is a core handler, part of ws_core's own ACTION_HANDLERS
    client_type = data.get("client_type")
    if client_type:
        # Call the internal registration logic
        success = await register_client(websocket, client_type)

        # Initial state sync is now handled in server.py after this function returns and registration_success is sent
        # This avoids circular dependencies where handlers call each other during initial registration.


    else:
        logging.warning(f"ws_core: Client {websocket.remote_address} sent 'register' without 'client_type'.")
        if _SEND_MESSAGE_FUNC:
             await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": "注册消息缺少 'client_type' 字段。", "action": "register", "context": "registration_no_type"})
        await websocket.close(code=1008, reason="Missing client_type") # Close connection for invalid registration attempt


async def handle_pong(websocket, data):
    """Handles PONG messages from clients."""
    # Receiving a PONG is client activity, update the last activity timestamp
    # This is already handled in dispatch_message which updates activity on *any* received message.
    # No specific action needed here, but the handler must exist to be registered.
    # logging.debug(f"ws_core: Received PONG from {websocket.remote_address}. Activity updated by dispatch_message.") # Too noisy
    pass


async def periodic_heartbeat_and_timeout_check():
    """
    Background task to send PING heartbeats and check for client timeouts.
    This task should be created and run by the server.py asyncio loop.
    """
    logging.info("ws_core: Background heartbeat and timeout check task started.")
    while True:
        await asyncio.sleep(PING_INTERVAL) # Wait for the ping interval

        now = time.time()
        # Operate on a copy of the client sets to avoid issues if clients disconnect during iteration
        clients_to_check = list(PRESENTER_CLIENTS) + list(AUDIENCE_CLIENTS)

        # Send PINGs and identify potentially timed-out clients
        timed_out_clients = []
        for websocket in clients_to_check:
            # Check if the websocket object is still valid (e.g., not None) - defensive check
            if websocket is None:
                 logging.warning("ws_core: Found None object in client list during heartbeat check. Removing.")
                 # Attempt to remove None from the sets (set.discard handles non-existent items)
                 PRESENTER_CLIENTS.discard(None)
                 AUDIENCE_CLIENTS.discard(None)
                 if None in CLIENT_LAST_ACTIVITY:
                     del CLIENT_LAST_ACTIVITY[None]
                 continue # Skip this iteration

            try:
                # Check last activity
                last_activity = CLIENT_LAST_ACTIVITY.get(websocket, 0) # Default to 0 if somehow missing
                if now - last_activity > TIMEOUT_DURATION:
                    logging.warning(f"ws_core: client {websocket.remote_address} timed out after {now - last_activity:.2f}s inactivity.")
                    timed_out_clients.append(websocket)
                else:
                    # Send PING heartbeat if client is active (activity updated by dispatch_message or PONG handler)
                    # We send PING; client is expected to send PONG. Activity timestamp is updated on receiving PONG.
                    await websocket.ping()
                    # logging.debug(f"ws_core: Sent PING to {websocket.remote_address}.") # Too noisy

            except websockets.exceptions.ConnectionClosed:
                # If sending PING fails because connection is already closed, client is gone
                logging.warning(f"ws_core: ConnectionClosed while sending PING to {websocket.remote_address}. Marking for removal.")
                timed_out_clients.append(websocket) # Treat as timed out
            except Exception as e:
                # Catch other unexpected errors during ping
                logging.error(f"ws_core: Error sending PING to {websocket.remote_address}: {e}. Marking for removal.", exc_info=True)
                timed_out_clients.append(websocket) # Assume timed out if ping fails

        # Disconnect timed-out clients
        for websocket in timed_out_clients:
             # Check if websocket is still in the sets before attempting close/unregister
             # This prevents errors if another process (e.g., the main handler) already unregistered it
             if websocket in PRESENTER_CLIENTS or websocket in AUDIENCE_CLIENTS:
                try:
                    # Cleanly close the connection if possible
                    logging.info(f"ws_core: Closing connection for timed-out client {websocket.remote_address}.")
                    # Use a timeout for the close operation itself
                    await asyncio.wait_for(websocket.close(code=1000, reason="Heartbeat timeout"), timeout=5.0) # 5 sec timeout for close
                    logging.info(f"ws_core: Closed connection for timed-out client {websocket.remote_address} successfully.")
                except asyncio.TimeoutError:
                    logging.warning(f"ws_core: Timeout during close operation for timed-out client {websocket.remote_address}. Forcing unregister.")
                except websockets.exceptions.ConnectionClosed:
                    logging.debug(f"ws_core: Connection already closed for {websocket.remote_address} during timeout handling.")
                except Exception as e:
                    logging.error(f"ws_core: Error closing connection for timed-out client {websocket.remote_address}: {e}", exc_info=True)
                finally:
                    # Ensure client is removed from our tracking sets and activity dict
                    # unregister_client handles removal from sets and dict
                    # It's safe to call even if client was already removed or not found
                    await unregister_client(websocket) # <--- This removes from sets and dict


async def dispatch_message(websocket, data):
    """
    Looks up and calls the appropriate async handler function for an incoming WebSocket message.
    Expected message format: {"action": "action_name", ...other_data...}
    This function also updates client activity timestamp on receiving any valid message.
    """
    addr = websocket.remote_address
    action = data.get("action")

    # Update activity timestamp for the client upon receiving any message
    # This counts receiving the message itself as activity
    # Ensure websocket is not None before accessing CLIENT_LAST_ACTIVITY (defensive)
    if websocket is not None:
        CLIENT_LAST_ACTIVITY[websocket] = time.time()
        # logging.debug(f"ws_core: Activity updated for {addr} on message receipt.") # Too noisy


    if not action:
        logging.warning(f"ws_core: Received message without 'action' field from {addr}. Message: {data}")
        if _SEND_MESSAGE_FUNC:
            await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": "消息缺少 'action' 字段。", "context": "dispatch"})
        return

    handler = ACTION_HANDLERS.get(action)

    if handler:
        # logging.info(f"ws_core: Dispatching: From {addr}: Action='{action}', Type='{data.get('type', 'None')}'") # Too noisy
        # Specific actions can log if they are important (e.g. register, load_script, start_roast)

        try:
            # CALL THE HANDLER WITH ONLY WEBSOCKET AND DATA
            await handler(websocket, data) # <--- THIS IS THE CORRECT CALL
        except Exception as e:
            logging.error(f"ws_core: Error processing message from {addr}: Action='{action}', Error: {e}", exc_info=True)
            # Send error back to the specific client that sent the message
            if _SEND_MESSAGE_FUNC:
                 await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": f"服务器处理消息时出错: {e}", "action": action, "context": "handler_error"})
    else:
        logging.warning(f"ws_core: No handler registered for action '{action}' from {addr}. Message: {data}")
        # Send error back
        if _SEND_MESSAGE_FUNC:
            await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": f"未知操作: {action}", "action": action, "context": "unknown_action"})

# Expose necessary functions and clients sets
__all__ = [
    'init_ws_core',
    'dispatch_message',
    'register_client', # Might be needed by server or tests
    'unregister_client', # Might be needed by server handler
    'broadcast_message', # Primary way other modules send messages to groups
    'PRESENTER_CLIENTS', # Expose sets for monitoring/broadcasting
    'AUDIENCE_CLIENTS', # Expose sets for monitoring/broadcasting
    'periodic_heartbeat_and_timeout_check', # Expose cleanup task runner
    # Internal helpers like _SEND_MESSAGE_FUNC are NOT exposed via __all__
    # Internal handlers like handle_register_client and handle_pong are NOT exposed
]
