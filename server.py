# server.py

import asyncio
import websockets
import json
import logging
import os
import sys # For sys.exit
from threading import Thread
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
# pathlib already imported by config
import time # For time.time() if needed

# --- Configure Logging ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(module)s - %(funcName)s: %(message)s')

# --- Import Configuration ---
try:
    import config # <--- 取消注释这一行
    config.log_config() # Log configuration on startup
    # from database.db_config import SOCIAL_TOPICS_COLLECTION # 暂时先注释掉这个，一步一步来
except ImportError: # 捕获导入 config 失败的情况
    logging.critical("Failed to import config.py. Ensure it exists and there are no circular imports.", exc_info=True)
    sys.exit(1)
except Exception as e: # 捕获 config.log_config() 可能发生的其他错误
    logging.critical(f"Error during config loading or logging: {e}", exc_info=True)
    sys.exit(1)

# --- Project Specific Modules ---
try:
    # Import from the new database package
    # We only need the init and getter for the singleton manager from connection_manager
    from database import init_db_manager, get_db_manager

    # Import State Manager
    from state_manager import ApplicationStateManager, init_state_manager, get_state_manager # Also need getter now

    # Import core WebSocket dispatcher and helpers
    from ws_core import init_ws_core, dispatch_message, unregister_client, broadcast_message, PRESENTER_CLIENTS, AUDIENCE_CLIENTS

    # Import init and register functions for all WebSocket handlers
    # These handlers now get DB/State via their getters
    from ws_script_handlers import init_script_handlers, register_script_handlers, send_initial_script_options, clear_presenter_browse_path, handle_get_current_event_for_presenter
    from ws_roast_handlers import init_roast_handlers, register_roast_handlers
    from ws_danmaku_fetch_handlers import init_danmaku_fetch_handlers, register_danmaku_fetch_handlers
    from ws_danmaku_send_handlers import init_danmaku_send_handlers, register_danmaku_send_handlers

    # Import Flask Routes module
    from flask_routes import init_flask_routes, register_flask_routes


except ImportError as e:
    logging.critical(f"Failed to import required modules: {e}")
    logging.critical("Please ensure all required Python files and the 'database' package are correctly structured and accessible.")
    sys.exit(1) # Exit if core modules cannot be imported


# --- Flask App Setup ---
# Flask serves static files (HTML, CSS, JS) and handles HTTP API requests
# Use config.STATIC_FOLDER for static files
app = Flask(__name__, static_folder=config.STATIC_FOLDER)
CORS(app) # Enable CORS for all routes

# --- Database Setup ---
# Will hold the singleton instance, initialized in start_servers
db_manager_instance = None

# --- State Manager Setup ---
# Will hold the singleton instance, initialized in start_servers
state_manager_instance = None


# --- Root Routes for HTML files ---
# Serve presenter_control.html and audience_display.html from the BASE_DIR
@app.route('/presenter_control.html')
def serve_presenter_control():
    # Use config.BASE_DIR
    return send_from_directory(config.BASE_DIR, 'presenter_control.html')

@app.route('/audience_display.html')
def serve_audience_display():
     # Use config.BASE_DIR
     return send_from_directory(config.BASE_DIR, 'audience_display.html')

@app.route('/')
def index():
    # Use config.BASE_DIR
    return send_from_directory(config.BASE_DIR, 'presenter_control.html')


# --- WebSocket Server ---
async def websocket_handler(websocket, path):
    """Handles incoming WebSocket connections and dispatches messages."""
    addr = websocket.remote_address
    logging.info(f"connection open: {addr} on path {path}")

    client_type = None # Track client type after registration

    try:
        # Wait for the initial 'register' message
        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)

        try:
            data = json.loads(message)
            # Use ws_core's dispatch to handle the 'register' action
            # This relies on ws_core's handle_register_client calling register_client
            if data.get("action") == "register":
                 client_type = data.get("client_type") # Extract type early if valid format
                 if client_type not in ["presenter", "audience"]:
                     raise ValueError(f"Invalid client_type: {client_type}") # Raise error for invalid type

                 # Dispatch the register message. ws_core will handle adding client to sets and sending success.
                 await dispatch_message(websocket, data)

                 # --- Initial State Sync AFTER Successful Registration ---
                 # After a presenter registers successfully, send them the initial script options and current script state
                 if client_type == "presenter":
                      # We need to ensure state_manager is initialized before calling script handlers
                      if get_state_manager():
                          try:
                              # Call helpers from ws_script_handlers
                              await send_initial_script_options(websocket) # Send script browsing options
                              # Also send the current script state if a script is already loaded
                              # Trigger the handler via dispatch for consistency, even if it sents directly back to this websocket
                              await handle_get_current_event_for_presenter(websocket, {}) # Pass empty data dict

                          except Exception as e:
                                logging.error(f"server: Error during initial presenter sync for {addr}: {e}", exc_info=True)
                                # Optionally send an error back to the presenter about sync failure
                                # Use the internal send func ref from ws_core
                                if hasattr(ws_core, '_SEND_MESSAGE_FUNC') and ws_core._SEND_MESSAGE_FUNC:
                                     await ws_core._SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": f"初始化状态同步失败: {e}", "context": "initial_sync_error"})
                      else:
                           logging.error(f"server: State manager not initialized during presenter registration sync for {addr}.")
                           if hasattr(ws_core, '_SEND_MESSAGE_FUNC') and ws_core._SEND_MESSAGE_FUNC:
                                await ws_core._SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": "服务器内部错误：状态管理器缺失。", "context": "initial_sync_state_missing"})


            else:
                # Not a register message, and it's the first message - invalid
                logging.warning(f"server: Client {addr} on path {path} sent non-register first message: {message}")
                # Send error before closing
                await websocket.send(json.dumps({"type": "error", "message": "第一条消息必须是带有正确 'client_type' 的 'register'。", "context": "invalid_first_message"}))
                await websocket.close(code=1008, reason="Invalid first message")
                return # Exit handler

        except json.JSONDecodeError:
             logging.warning(f"server: Received invalid JSON as first message from {addr}: {message}")
             await websocket.send(json.dumps({"type": "error", "message": "第一条消息必须是有效的JSON格式。", "context": "invalid_first_json"}))
             await websocket.close(code=1008, reason="Invalid first JSON")
             return # Exit handler
        except ValueError as e: # Catch invalid client_type from our raise
             logging.warning(f"server: Client {addr} on path {path} sent invalid client_type: {e}")
             await websocket.send(json.dumps({"type": "error", "message": str(e), "context": "registration_invalid_type"}))
             await websocket.close(code=1008, reason=str(e))
             return # Exit handler
        except Exception as e:
             logging.error(f"server: Error during initial registration processing for {addr}: {e}", exc_info=True)
             await websocket.send(json.dumps({"type": "error", "message": f"服务器处理注册时发生未知错误: {e}", "context": "register_error"}))
             await websocket.close(code=1011, reason="Internal error during registration")
             return # Exit handler


    except asyncio.TimeoutError:
         logging.warning(f"server: Client {addr} on path {path} timed out waiting for register message.")
         await websocket.send(json.dumps({"type": "error", "message": "等待注册消息超时。", "context": "register_timeout"}))
         await websocket.close(code=1008, reason="Registration timeout")
         return # Exit handler

    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"connection closed (OK) before register: {addr}")
        return # Exit handler
    except websockets.exceptions.ConnectionClosedError as e:
         logging.warning(f"connection closed (Error) before register: {addr}: {e}")
         return # Exit handler
    except Exception as e:
         logging.error(f"server: Unexpected error during initial connection phase for {addr}: {e}", exc_info=True)
         try:
             await websocket.send(json.dumps({"type": "error", "message": f"服务器连接处理错误: {e}", "context": "initial_connection_error"}))
         except Exception: pass
         await websocket.close(code=1011, reason="Internal connection error")
         return # Exit handler


    # If registration was successful, proceed to process subsequent messages
    # The ws_core.dispatch_message function handles all subsequent incoming messages
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                # Dispatch all subsequent messages via ws_core
                await dispatch_message(websocket, data)
            except json.JSONDecodeError:
                logging.warning(f"server: Received invalid JSON message from {addr}: {message}")
                # Use the internal send func ref from ws_core if available
                if hasattr(ws_core, '_SEND_MESSAGE_FUNC') and ws_core._SEND_MESSAGE_FUNC:
                    await ws_core._SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": "无效的JSON格式。", "context": "json_decode_error"})
            except Exception as e:
                 logging.error(f"server: Unexpected error processing message from {addr}: {e}", exc_info=True)
                 if hasattr(ws_core, '_SEND_MESSAGE_FUNC') and ws_core._SEND_MESSAGE_FUNC:
                      await ws_core._SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": f"服务器处理消息时发生未知错误: {e}", "context": "server_processing_error"})


    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"connection closed (OK): {addr}")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.warning(f"connection closed (Error): {addr}: {e}")
    except Exception as e:
        logging.error(f"server: Unexpected error in WebSocket handler loop for {addr}: {e}", exc_info=True)
    finally:
        # Ensure client is unregistered and removed from sets upon disconnect
        logging.info(f"server: Client {addr} disconnected. Unregistering via ws_core.")
        # ws_core's unregister_client handles clearing presenter browse path internally if imported
        await unregister_client(websocket)


# Helper functions passed to ws_core for sending/broadcasting
# These functions are defined here in server.py because they need access to the
# websocket instances and the websockets library's send/close methods.
async def _send_message_to_ws(websocket, message):
    """Internal helper to send a JSON message to a specific websocket."""
    try:
        if not isinstance(message, dict):
            logging.error(f"server: Attempted to send non-dictionary message to {websocket.remote_address}: {message}")
            return

        # Add a timestamp for potential client-side display sync/debugging
        if "timestamp" not in message:
             message["timestamp"] = time.time()

        await websocket.send(json.dumps(message))
        # logging.debug(f"server: Sent message to {websocket.remote_address}: {message.get('type')}") # Too noisy
    except websockets.exceptions.ConnectionClosed:
        # This happens often during graceful disconnect, just log debug
        logging.debug(f"server: Failed to send message to closed connection {websocket.remote_address}.")
    except Exception as e:
        logging.error(f"server: Error sending message to {websocket.remote_address}: {e}", exc_info=True)

async def _broadcast_message_to_group(target_type, message):
    """Internal helper to broadcast a JSON message to a group of websockets."""
    if not isinstance(message, dict):
        logging.error(f"server: Attempted to broadcast non-dictionary message to {target_type}: {message}")
        return

    if "timestamp" not in message:
        message["timestamp"] = time.time()

    clients_source = []
    # Access client sets from ws_core module
    if target_type == "presenter":
        clients_source = PRESENTER_CLIENTS
        logging.debug(f"server: Broadcasting {message.get('type')} to presenter group ({len(clients_source)} total).")
    elif target_type == "audience":
        clients_source = AUDIENCE_CLIENTS
        # 使用 INFO 级别确保能看到 
        logging.info(f"server: Broadcasting to audience. AUDIENCE_CLIENTS size: {len(clients_source)}. Clients: {[str(c.remote_address) if c else 'None' for c in clients_source]}") 
        logging.debug(f"server: Broadcasting {message.get('type')} to audience group ({len(clients_source)} total).")
    elif target_type == "all":
        clients_source = PRESENTER_CLIENTS.union(AUDIENCE_CLIENTS)
        logging.debug(f"server: Broadcasting {message.get('type')} to all clients ({len(clients_source)} total).")
    else:
        logging.error(f"server: Unknown target type for broadcast: {target_type}")
        return

    # Create a list from the source set/union and explicitly filter out None values
    clients_to_send = [c for c in list(clients_source) if c is not None]

    if clients_to_send:
        # Use asyncio.gather for concurrent sending
        tasks = [_send_message_to_ws(client, message.copy()) for client in clients_to_send]
        if tasks:
            # Use return_exceptions=True to allow some sends to fail without stopping others
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Log any exceptions during individual sends
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    client_addr_str = "Unknown Client"
                    try:
                        if i < len(clients_to_send) and clients_to_send[i] and hasattr(clients_to_send[i], 'remote_address'):
                            client_addr_str = str(clients_to_send[i].remote_address)
                    except Exception as e_addr:
                        logging.debug(f"server: Could not get client address for error logging during broadcast error: {e_addr}")
                    logging.warning(f"server: Error during broadcast to {client_addr_str}: {result}")
            # logging.debug(f"server: Broadcast of '{message.get('type')}' to {len(clients_to_send)} clients completed (individual success/failure logged).")
    else:
        logging.debug(f"server: No active clients in target group '{target_type}' to broadcast to after filtering.")


# --- Async Server Startup ---
async def start_servers():
    """Starts the WebSocket and Flask servers."""
    logging.info("server: Starting application...")

    # 1. Initialize components that handle shared resources/state
    logging.info("server: Initializing components...")
    global db_manager_instance, state_manager_instance

    # Initialize DatabaseManager using the init_db_manager from the database package
    db_manager_instance = init_db_manager() # Get the singleton instance
    if not db_manager_instance.connect_db():
        logging.critical("server: Failed to connect to MongoDB during startup. Dependent features will be unavailable.")
        # Decide if you want to exit or continue with limited functionality
        # For now, let's allow startup but features requiring DB will fail gracefully.
        # sys.exit(1) # Uncomment to exit on DB connection failure

    # Initialize State Manager
    state_manager_instance = ApplicationStateManager()
    init_state_manager(state_manager_instance)
    logging.info("state_manager: Application state initialized.")

    # 2. Initialize WebSocket handler modules with dependencies
    logging.info("server: Initializing WebSocket handler modules.")
    # Handlers now get DB via get_db_manager(), State via get_state_manager()
    # Pass only necessary dependencies like broadcast or state manager *instance*
    init_script_handlers(state_manager_instance) # Pass state manager instance
    # 此处已经正确传递 db_manager_instance
    init_roast_handlers(state_manager_instance, db_manager_instance, _broadcast_message_to_group) # Pass state manager, db manager instance, and broadcast
    init_danmaku_fetch_handlers() # No specific deps needed here, it uses getters
    init_danmaku_send_handlers(_broadcast_message_to_group) # Needs broadcast, uses getters


    # 3. Initialize WebSocket core dispatcher and register handlers
    logging.info("server: Initializing WebSocket core dispatcher.")
    # Pass send/broadcast helpers defined in server.py and registration functions from all handler modules
    init_ws_core(_send_message_to_ws, _broadcast_message_to_group,
                 register_script_handlers,
                 register_roast_handlers,
                 register_danmaku_fetch_handlers,
                 register_danmaku_send_handlers)
    logging.info(f"ws_core: WebSocket core initialized.")

    # 4. Initialize Flask routes module and register routes
    # Routes use getters for DB/State, only need broadcast passed if they use it (less common)
    logging.info("flask_routes: Initializing Flask routes with dependencies.")
    # Pass db_manager_instance explicitly to flask_routes init for its startup data fetch
    init_flask_routes(db_manager_instance, state_manager_instance, _broadcast_message_to_group)

    logging.info("flask_routes: Registering Flask routes.")
    register_flask_routes(app)
    logging.info("flask_routes: Flask routes registered successfully.")


    # 5. Start the Flask app in a separate thread
    logging.info(f"server: Flask app thread starting on http://0.0.0.0:{config.FLASK_PORT}")
    # Use config.FLASK_PORT
    # For production, use a WSGI server like Gunicorn or uWSGI.
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.FLASK_PORT, debug=False, use_reloader=False))
    flask_thread.daemon = True # Daemonize thread so it exits when main thread exits
    flask_thread.start()

    # 6. Start the WebSocket server 
    # Use config.WEBSOCKET_PORT 
    logging.info(f"server listening on 0.0.0.0:{config.WEBSOCKET_PORT}") 
     
    # Configure logging for websockets library 
    # 确保这些日志配置在你希望的位置，并且不会与其他日志配置冲突 
    # logging.getLogger("websockets").setLevel(logging.DEBUG) 
    # logging.getLogger("websockets").addHandler(logging.StreamHandler()) 
    # 为了更精细控制，可以针对 server 和 protocol 分别设置 
    server_logger = logging.getLogger("websockets.server") 
    server_logger.setLevel(logging.DEBUG) # 或者 INFO 
    if not server_logger.hasHandlers(): # 避免重复添加处理器 
        server_logger.addHandler(logging.StreamHandler()) 
 
    protocol_logger = logging.getLogger("websockets.protocol") 
    protocol_logger.setLevel(logging.DEBUG) # 或者 INFO 
    if not protocol_logger.hasHandlers(): # 避免重复添加处理器 
        protocol_logger.addHandler(logging.StreamHandler()) 
 
    class CustomServerProtocol(websockets.WebSocketServerProtocol): 
        async def process_pong(self, data: bytes) -> None: 
            # 你可以选择在这里记录PONG，或者完全依赖库的日志 
            logging.debug(f"CustomServerProtocol: PONG received from {self.remote_address}. Data: {data!r} (Handled by library)") 
            await super().process_pong(data) 
            # 移除调用 update_client_activity

    # ***** 将 websockets.serve 的结果赋值给 ws_server ***** 
    ws_server = await websockets.serve( 
        websocket_handler, # 注意这里是 websocket_handler 而不是 ws_handler_entry 
        "0.0.0.0", 
        config.WEBSOCKET_PORT, 
        ping_interval=config.PING_INTERVAL, 
        ping_timeout=config.PING_TIMEOUT_FOR_WEBSOCKETS_LIB, # 确保这个值在 config.py 中定义且合理 
        create_protocol=CustomServerProtocol 
    ) 
    logging.info(f"server: WebSocket server started on ws://0.0.0.0:{config.WEBSOCKET_PORT}") 
    logging.info(f"server: PING Interval: {config.PING_INTERVAL}s, PING Timeout (websockets lib): {getattr(config, 'PING_TIMEOUT_FOR_WEBSOCKETS_LIB', 'N/A')}s") 
 
 
    # 7. Start background cleanup tasks (e.g., heartbeat checks)
    logging.info("server: Background cleanup task starting.")
    # periodic_heartbeat_and_timeout_check needs access to client sets in ws_core and the unregister function
    # These are available via importing ws_core
    # 移除以下行
    # cleanup_task = asyncio.create_task(periodic_heartbeat_and_timeout_check())
    logging.info("server: Background cleanup task started.")

    # Keep the asyncio loop running indefinitely
    logging.info("server: Application running. Press CTRL+C to quit")
    try:
        await ws_server.wait_closed() # 现在 ws_server 已定义 
    except asyncio.CancelledError:
        logging.info("server: Application task cancelled.")
    except Exception as e:
        logging.critical(f"server: Critical error in main asyncio execution: {e}", exc_info=True)
    finally:
        # Ensure cleanup task is cancelled on server shutdown
        # if cleanup_task and not cleanup_task.done():
        #     logging.info("server: Cancelling cleanup task.")
        #     cleanup_task.cancel()
        #     try:
        #         await cleanup_task
        #     except asyncio.CancelledError:
        #         pass  # Expected
        #     except Exception as e:
        #         logging.error(f"server: Error waiting for cleanup task cancellation: {e}")

        logging.info("server: WebSocket server stopping.")

        # Perform database disconnect on shutdown using the instance initialized earlier
        if db_manager_instance and db_manager_instance.is_connected():
            db_manager_instance.disconnect_db()

        logging.info("server: Application shutdown process complete.")


# --- Main Execution ---
if __name__ == "__main__":
    try:
        # This will run the async start_servers function
        # asyncio.run handles creating/closing the loop
        asyncio.run(start_servers())
    except KeyboardInterrupt:
        logging.info("server: Server shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logging.critical(f"server: Application failed to run: {e}", exc_info=True)

