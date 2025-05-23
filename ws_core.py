# ws_core.py
import asyncio
import json
import logging
import time # Still useful for timestamps in messages, etc.

# Global sets to store connected clients
# Each element is the websocket connection object
PRESENTER_CLIENTS = set()
AUDIENCE_CLIENTS = set()

# Global dictionary to hold registered action handlers {action_name: handler_function}
ACTION_HANDLERS = {}

# Global reference to the send_message_to_ws_func from server.py for error reporting
_SEND_MESSAGE_FUNC = None

# Global reference to the broadcast function from server.py for broadcasting specific core messages
_BROADCAST_MESSAGE_FUNC = None

async def handle_register_client(websocket, data): 
    """Handles the 'register' action.""" 
    client_type = data.get("client_type") 
    if client_type: 
        # 调用内部的注册逻辑 
        success = await register_client(websocket, client_type) # register_client 负责发送 registration_success 
        # 初始状态同步现在由 server.py 在注册成功消息发送后，在 websocket_handler 中处理。 
    else: 
        logging.warning(f"ws_core: Client {websocket.remote_address} sent 'register' without 'client_type'.") 
        if _SEND_MESSAGE_FUNC: 
            await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": "注册消息缺少 'client_type' 字段。", "action": "register", "context": "registration_no_type"}) 
        # 考虑关闭连接如果注册格式错误 
        # await websocket.close(code=1008, reason="Missing client_type for registration") 

async def handle_pong(websocket, data): 
    """Handles PONG messages from clients.""" 
    logging.debug(f"ws_core: Received PONG from {websocket.remote_address}.") 
    pass 

def init_ws_core(send_message_to_ws_func, broadcast_message_func, *handler_registration_funcs):
    global ACTION_HANDLERS, _SEND_MESSAGE_FUNC, _BROADCAST_MESSAGE_FUNC
    _SEND_MESSAGE_FUNC = send_message_to_ws_func
    _BROADCAST_MESSAGE_FUNC = broadcast_message_func
    ACTION_HANDLERS = {}

    ACTION_HANDLERS["register"] = handle_register_client
    ACTION_HANDLERS["pong"] = handle_pong

    for register_func in handler_registration_funcs:
        try:
            handlers_dict = register_func()
            for action in handlers_dict:
                if action in ACTION_HANDLERS:
                    logging.warning(f"ws_core: Action '{action}' from {register_func.__module__} is already registered. Overwriting.")
            ACTION_HANDLERS.update(handlers_dict)
            module_name = register_func.__module__ if hasattr(register_func, '__module__') else 'UnknownModule'
            logging.info(f"ws_core: Registered handlers from {module_name}. Total handlers: {len(ACTION_HANDLERS)}")
        except Exception as e:
            logging.error(f"ws_core: Error registering handlers from {register_func}: {e}", exc_info=True)

    logging.info(f"ws_core: WebSocket core initialized with {len(ACTION_HANDLERS)} action handlers.")


async def register_client(websocket, client_type):
    """Registers a new client connection by type."""
    addr = websocket.remote_address

    if client_type == "presenter":
        if websocket not in PRESENTER_CLIENTS:
            PRESENTER_CLIENTS.add(websocket)
            logging.info(f"ws_core: Presenter client registered: {addr}. Total presenters: {len(PRESENTER_CLIENTS)}")
            if _SEND_MESSAGE_FUNC:
                await _SEND_MESSAGE_FUNC(websocket, {"type": "registration_success", "client_type": client_type, "message": "Presenter registered successfully."})
            return True
        else:
            logging.warning(f"ws_core: Client {addr} attempted to re-register as Presenter.")
            if _SEND_MESSAGE_FUNC:
                await _SEND_MESSAGE_FUNC(websocket, {"type": "warning", "message": f"已注册为 {client_type}", "context": "re_registration"})
            return False

    elif client_type == "audience":
         if websocket not in AUDIENCE_CLIENTS:
            AUDIENCE_CLIENTS.add(websocket)
            logging.info(f"ws_core: Audience client registered: {addr}. Total audience: {len(AUDIENCE_CLIENTS)}")
            if _SEND_MESSAGE_FUNC:
                await _SEND_MESSAGE_FUNC(websocket, {"type": "registration_success", "client_type": client_type, "message": "Audience registered successfully."})
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
    removed_from_presenter = False
    removed_from_audience = False

    if websocket in PRESENTER_CLIENTS:
        try:
            PRESENTER_CLIENTS.remove(websocket)
            removed_from_presenter = True
            logging.info(f"ws_core: Presenter client {addr} removed. Total presenters: {len(PRESENTER_CLIENTS)}")
        except KeyError:
            logging.debug(f"ws_core: Presenter client {addr} not found in set during unregister (already removed).")

    if websocket in AUDIENCE_CLIENTS:
        try:
            AUDIENCE_CLIENTS.remove(websocket)
            removed_from_audience = True
            logging.info(f"ws_core: Audience client {addr} removed. Total audience: {len(AUDIENCE_CLIENTS)}")
        except KeyError:
            logging.debug(f"ws_core: Audience client {addr} not found in set during unregister (already removed).")

    if not removed_from_presenter and not removed_from_audience:
        logging.info(f"ws_core: Unregistered or unknown client disconnected: {addr}")
    else:
        logging.info(f"ws_core: Client {addr} disconnect handling finished.")

    # Clear presenter-specific states if it was a presenter
    if removed_from_presenter:
        try:
             from ws_script_handlers import clear_presenter_browse_path
             clear_presenter_browse_path(websocket)
             logging.debug(f"ws_core: Cleared script browse path for presenter {addr}.")
        except ImportError:
             logging.debug("ws_core: ws_script_handlers or clear_presenter_browse_path not available for cleanup.")
        except Exception as e:  # 明确捕获异常类型
            logging.debug(f"ws_core: An unexpected error occurred during cleanup: {e}")  # 添加缩进的代码块


async def dispatch_message(websocket, data): 
    """ 
    Looks up and calls the appropriate async handler function for an incoming WebSocket message. 
    """ 
    addr = websocket.remote_address 
    action = data.get("action") 
 
    if not action: 
        logging.warning(f"ws_core: Received message without 'action' field from {addr}. Message: {data}") 
        if _SEND_MESSAGE_FUNC: 
            await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": "消息缺少 'action' 字段。", "context": "dispatch"}) 
        return 
 
    handler = ACTION_HANDLERS.get(action) 
    if handler: 
        try: 
            await handler(websocket, data) 
        except Exception as e: 
            logging.error(f"ws_core: Error processing message from {addr}: Action='{action}', Error: {e}", exc_info=True) 
            if _SEND_MESSAGE_FUNC: 
                await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": f"服务器处理消息时出错: {e}", "action": action, "context": "handler_error"}) 
    else: 
        logging.warning(f"ws_core: No handler registered for action '{action}' from {addr}. Message: {data}") 
        if _SEND_MESSAGE_FUNC: 
            await _SEND_MESSAGE_FUNC(websocket, {"type": "error", "message": f"未知操作: {action}", "action": action, "context": "unknown_action"}) 


async def broadcast_message(target_type, message): 
    """Broadcasts a message to all connected clients of a specific type or all clients.""" 
    if _BROADCAST_MESSAGE_FUNC is None: 
        logging.error("ws_core: Broadcast function not initialized. Cannot broadcast message.") 
        return 
    if not isinstance(message, dict): 
        logging.error(f"ws_core: Attempted to broadcast non-dictionary message: {message}") 
        return 
    await _BROADCAST_MESSAGE_FUNC(target_type, message) 

__all__ = [ 
    'init_ws_core', 
    'dispatch_message', 
    'unregister_client', 
    'broadcast_message', 
    'PRESENTER_CLIENTS', 
    'AUDIENCE_CLIENTS', 
]