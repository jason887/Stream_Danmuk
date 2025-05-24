# ws_danmaku_send_handlers.py

import logging
import json
import asyncio
import random # For shuffling danmaku
import time
import re # 确保 re 已导入

# Import from the new database package
from database import get_db_manager, db_config, get_random_danmaku, fetch_danmaku

# Global references to dependencies
_broadcast_message = None

# Interval between sending individual danmaku within an auto-send group
SEND_INTERVAL_MS = 2200
GROUP_PAUSE_MS = 3000
AUTO_SEND_DURATION_MS = 10000
BOSS_GIFT_DANMAKU_DURATION_MS = 22000

current_boss_danmaku_task = None

def init_danmaku_send_handlers(broadcast_message_func):
    logging.info("ws_danmaku_send_handlers: Initializing send handlers module with dependencies.")
    global _broadcast_message
    _broadcast_message = broadcast_message_func
    logging.info("ws_danmaku_send_handlers: Send handlers module initialized.")

def _is_db_connected():
    manager = get_db_manager()
    return manager and manager.is_connected()

async def _send_danmaku_group(danmaku_list, danmaku_type_label, websocket=None, target_name="", gift_name="", specific_duration_ms=None):
    if not danmaku_list:
        logging.info(f"ws_danmaku_send_handlers: 没有可发送的'{danmaku_type_label}'弹幕。")
        if websocket:
            await websocket.send(json.dumps({"type": "info", "message": f"没有可发送的{danmaku_type_label}弹幕。", "context": f"auto_send_{danmaku_type_label}_empty"}))
        return

    logging.info(f"ws_danmaku_send_handlers: 即将发送 {len(danmaku_list)} 条'{danmaku_type_label}'弹幕。")
    logging.info(f"ws_danmaku_send_handlers: 为 '{danmaku_type_label}' (目标: '{target_name}') 准备的弹幕列表内容: {danmaku_list}")

    if websocket:
        await websocket.send(json.dumps({"type": "info", "message": f"发送 {len(danmaku_list)} 条{danmaku_type_label}弹幕...", "context": f"auto_send_{danmaku_type_label}_group"}))

    is_roast = (danmaku_type_label.lower().startswith("吐槽") or danmaku_type_label.lower().startswith("怼人"))
    duration_to_use = specific_duration_ms if specific_duration_ms is not None else AUTO_SEND_DURATION_MS
    sent_count = 0

    for i, raw_text in enumerate(danmaku_list): # raw_text 现在应该是已经处理好的文本
        if not isinstance(raw_text, str) or not raw_text.strip():
            logging.warning(f"ws_danmaku_send_handlers: 跳过无效的 {danmaku_type_label} 弹幕条目 (已处理过): {raw_text}")
            continue

        processed_text = raw_text # 直接使用，因为已在 auto_send_boss_danmaku_flow 中处理

        danmaku_message = {
            "type": "danmaku", "text": processed_text, "duration_ms": duration_to_use,
            "is_roast": is_roast, "timestamp": time.time()
        }
        try:
            if _broadcast_message:
                await _broadcast_message("audience", danmaku_message)
                logging.debug(f"ws_danmaku_send_handlers: 发送 '{danmaku_type_label}' 弹幕 {sent_count+1}: '{processed_text}' (Duration: {duration_to_use}ms)")
                sent_count += 1
            else:
                 logging.error("ws_danmaku_send_handlers: Broadcast function not initialized!")
                 if websocket:
                      await websocket.send(json.dumps({"type": "error", "message": "广播功能未初始化，无法发送弹幕。", "context": "send_danmaku_broadcast_error"}))
                 break
        except Exception as e:
            logging.error(f"ws_danmaku_send_handlers: 广播 '{danmaku_type_label}' 弹幕时出错: {e}", exc_info=True)
            if websocket:
                 await websocket.send(json.dumps({"type": "error", "message": f"广播弹幕失败: {e}", "context": f"send_danmaku_{danmaku_type_label}_broadcast_exception"}))
        if i < len(danmaku_list) - 1:
            await asyncio.sleep(SEND_INTERVAL_MS / 1000)
    if sent_count > 0:
        logging.info(f"ws_danmaku_send_handlers: 完成发送 {sent_count} 条 '{danmaku_type_label}' 弹幕。")
    else:
        logging.warning(f"ws_danmaku_send_handlers: 没有发送任何有效的 '{danmaku_type_label}' 弹幕。")

async def handle_auto_send_danmaku(websocket, data):
    if _broadcast_message is None:
        logging.error("ws_danmaku_send_handlers: Broadcast function not initialized.")
        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：弹幕发送功能未初始化。", "context": "auto_send_init"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_init_reenable"}))
        return
    if not _is_db_connected():
        logging.error("ws_danmaku_send_handlers: DB not connected.")
        await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法自动发送弹幕。", "action": "auto_send_danmaku", "context": "auto_send_db_disconnected"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_db_reenable"}))
        return

    streamer_name = data.get("streamer_name")
    presenter_addr = websocket.remote_address
    desired_count_per_type = 10 # 你希望每种类型发送10条

    if not streamer_name:
        logging.warning(f"ws_danmaku_send_handlers: Presenter {presenter_addr} sent auto_send_danmaku with no streamer name.")
        await websocket.send(json.dumps({"type": "warning", "message": "请提供主播名。", "action": "auto_send_danmaku", "context": "auto_send_no_name"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_no_name_reenable"}))
        return

    welcome_danmaku_list_to_send = []
    roast_danmaku_list_to_send = []
    try:
        db_manager = get_db_manager()
        db = db_manager.get_db() if db_manager and db_manager.is_connected() else None
        if db is None:
            logging.error(f"ws_danmaku_send_handlers: DB connection lost before fetching danmaku for {streamer_name}.")
            await websocket.send(json.dumps({"type": "error", "message": "数据库连接丢失。", "context": "auto_send_db_fetch_error"}))
            # Re-enable buttons on error
            await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_db_fetch_error_reenable"}))
            return # 直接返回，因为没有数据库连接无法继续

        # --- 获取欢迎弹幕 ---
        welcome_collection = db[db_config.WELCOME_COLLECTION]
        # 修改查询条件和字段名
        welcome_query = {"streamer_name": {"$regex": f"^{re.escape(streamer_name)}$", "$options": "i"}}
        welcome_projection = {"generated_danmaku": 1, "_id": 0}
        welcome_doc = welcome_collection.find_one(welcome_query, welcome_projection)

        if welcome_doc and 'generated_danmaku' in welcome_doc and isinstance(welcome_doc['generated_danmaku'], list):
            source_welcome_list = [tpl for tpl in welcome_doc['generated_danmaku'] if isinstance(tpl, str) and tpl.strip()]
            if source_welcome_list:
                logging.info(f"ws_danmaku_send_handlers: Fetched {len(source_welcome_list)} 'welcome' danmaku for '{streamer_name}'.")
                random.shuffle(source_welcome_list)
                welcome_danmaku_list_to_send = source_welcome_list[:desired_count_per_type]
            else:
                logging.info(f"ws_danmaku_send_handlers: 'generated_danmaku' array for 'welcome' is empty or invalid for '{streamer_name}'.")
        else:
            logging.info(f"ws_danmaku_send_handlers: No 'welcome' danmaku document found for '{streamer_name}'.")

        # --- 获取吐槽弹幕 ---
        mock_collection = db[db_config.MOCK_COLLECTION]
        # 修改查询条件和字段名
        roast_query = {"streamer_name": {"$regex": f"^{re.escape(streamer_name)}$", "$options": "i"}}
        roast_projection = {"generated_danmaku": 1, "_id": 0}
        roast_doc = mock_collection.find_one(roast_query, roast_projection)

        if roast_doc and 'generated_danmaku' in roast_doc and isinstance(roast_doc['generated_danmaku'], list):
            source_roast_list = [tpl for tpl in roast_doc['generated_danmaku'] if isinstance(tpl, str) and tpl.strip()]
            if source_roast_list:
                logging.info(f"ws_danmaku_send_handlers: Fetched {len(source_roast_list)} 'roast' (mock) danmaku for '{streamer_name}'.")
                random.shuffle(source_roast_list)
                roast_danmaku_list_to_send = source_roast_list[:desired_count_per_type]
            else:
                logging.info(f"ws_danmaku_send_handlers: 'generated_danmaku' array for 'roast' is empty or invalid for '{streamer_name}'.")
        else:
            logging.info(f"ws_danmaku_send_handlers: No 'roast' (mock) danmaku document found for '{streamer_name}'.")

        # --- 后续发送逻辑 ---
        if not welcome_danmaku_list_to_send and not roast_danmaku_list_to_send:
            logging.warning(f"ws_danmaku_send_handlers: No welcome or mock danmaku to send for streamer '{streamer_name}'.")
            await websocket.send(json.dumps({
                "type": "warning", "message": f"未找到 {streamer_name} 的欢迎或吐槽弹幕可供发送。",
                "action": "auto_send_danmaku", "context": "auto_send_no_data_to_construct"
            }))
            return

        logging.info(f"ws_danmaku_send_handlers: Starting auto-send for '{streamer_name}'. Welcome: {len(welcome_danmaku_list_to_send)}, Mock: {len(roast_danmaku_list_to_send)}")
        await websocket.send(json.dumps({"type": "info", "message": f"开始自动发送 {streamer_name} 的弹幕...", "context": "auto_send_starting"}))
        await websocket.send(json.dumps({"type": "auto_send_started", "context": "auto_send_started"})) # 前端可以用这个消息来禁用按钮

        if welcome_danmaku_list_to_send:
            await _send_danmaku_group(welcome_danmaku_list_to_send, "欢迎", websocket, target_name=streamer_name)
            if roast_danmaku_list_to_send: # 只有在欢迎弹幕发送后且有吐槽弹幕时才暂停
                 logging.info(f"ws_danmaku_send_handlers: Pausing {GROUP_PAUSE_MS/1000}s before mock group.")
                 await asyncio.sleep(GROUP_PAUSE_MS / 1000)
        if roast_danmaku_list_to_send:
            await _send_danmaku_group(roast_danmaku_list_to_send, "吐槽", websocket, target_name=streamer_name)

        logging.info(f"ws_danmaku_send_handlers: Auto-send sequence for '{streamer_name}' finished.")
        await websocket.send(json.dumps({"type": "success", "message": "自动发送完成。", "context": "auto_send_finished"}))

    except asyncio.CancelledError:
         logging.info("ws_danmaku_send_handlers: Auto-send task was cancelled.")
         await websocket.send(json.dumps({"type": "info", "message": "自动发送已取消。", "context": "auto_send_cancelled"}))
    except Exception as e:
        logging.error(f"ws_danmaku_send_handlers: Error during auto-send for '{streamer_name}' from {presenter_addr}: {e}", exc_info=True)
        await websocket.send(json.dumps({"type": "error", "message": f"自动发送弹幕时出错: {e}", "action": "auto_send_danmaku", "context": "auto_send_error"}))
    finally:
        # 确保按钮在任何情况下都会重新启用
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "auto_send_finally_reenable"}))

def _boss_task_done_callback(task):
    try:
        task.result() # 如果任务有异常，这里会重新抛出
        logging.info(f"Boss danmaku task {task.get_name()} completed successfully.")
    except asyncio.CancelledError:
        logging.info(f"Boss danmaku task {task.get_name()} was cancelled.")
    except Exception as e:
        logging.error(f"Boss danmaku task {task.get_name()} failed with exception: {e}", exc_info=True)

async def handle_send_boss_danmaku(websocket, data):
    global current_boss_danmaku_task
    presenter_addr = f"{websocket.remote_address}" if websocket else "N/A"
    logging.info(f"ws_danmaku_send_handlers: Received send_boss_danmaku action from {presenter_addr} with data: {data}")
    if _broadcast_message is None:
        logging.error("ws_danmaku_send_handlers: Broadcast function not initialized.")
        await websocket.send(json.dumps({"type": "error", "message": "服务器内部错误：弹幕发送功能未初始化。", "context": "send_boss_init_error"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_init_error_reenable"}))
        return
    if not _is_db_connected():
         logging.error("ws_danmaku_send_handlers: DB not connected.")
         await websocket.send(json.dumps({"type": "error", "message": "数据库未连接，无法发送大哥弹幕。", "action": "send_boss_danmaku", "context": "send_boss_db_disconnected"}))
         await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_db_reenable"}))
         return

    danmaku_type = data.get("danmaku_type")
    boss_name = data.get("boss_name")
    gift_name = data.get("gift_name", "")
    desired_total_count = 30 # 确保这里定义了

    if danmaku_type not in ["welcome_boss", "thanks_boss_gift"]:
        logging.warning(f"ws_danmaku_send_handlers: Invalid danmaku_type: {danmaku_type} from {presenter_addr}")
        await websocket.send(json.dumps({"type": "error", "message": f"无效的弹幕类型: {danmaku_type}", "action": "send_boss_danmaku", "context": "send_boss_invalid_type"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_invalid_type_reenable"}))
        return
    if not boss_name:
        logging.warning(f"ws_danmaku_send_handlers: Missing boss_name for {danmaku_type} from {presenter_addr}")
        await websocket.send(json.dumps({"type": "error", "message": "缺少大哥名称", "action": "send_boss_danmaku", "context": "send_boss_missing_name"}))
        await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_missing_name_reenable"}))
        return
    if danmaku_type == "thanks_boss_gift" and not gift_name:
          logging.warning(f"ws_danmaku_send_handlers: Missing gift_name for thanks_boss_gift from {presenter_addr}")
          await websocket.send(json.dumps({"type": "error", "message": "缺少礼物名称", "action": "send_boss_danmaku", "context": "send_boss_missing_gift"}))
          await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_missing_gift_reenable"}))
          return

    # 如果已有任务在运行，取消它
    if current_boss_danmaku_task and not current_boss_danmaku_task.done():
        logging.info(f"Cancelling previous boss danmaku task for {current_boss_danmaku_task.get_name()} before starting new one for {boss_name}")
        current_boss_danmaku_task.cancel()
        try:
            await current_boss_danmaku_task
        except asyncio.CancelledError:
            logging.info(f"Previous boss danmaku task {current_boss_danmaku_task.get_name()} was cancelled successfully.")
        except Exception as e:
            logging.error(f"Error awaiting previous cancelled boss task: {e}")

    # 创建新的发送任务
    # asyncio.create_task() 的 name 参数在 Python 3.8+ 可用
    new_task_name = f"boss_danmaku_for_{boss_name}"
    current_boss_danmaku_task = asyncio.create_task(
        auto_send_boss_danmaku_flow(websocket, boss_name, gift_name, danmaku_type, desired_total_count),
        name=new_task_name
    )
    current_boss_danmaku_task.add_done_callback(_boss_task_done_callback)
    logging.info(f"Created new boss danmaku task: {new_task_name}")
    await websocket.send(json.dumps({"type": "auto_send_started", "message": f"开始发送 {danmaku_type} 弹幕...", "context": f"send_boss_{danmaku_type}_started"}))


async def auto_send_boss_danmaku_flow(websocket, boss_name, gift_name, danmaku_type, desired_total_count):
    task_name = asyncio.current_task().get_name() if hasattr(asyncio.current_task(), 'get_name') else "UnknownTask"
    logging.info(f"Task {task_name}: auto_send_boss_danmaku_flow STARTED for {boss_name}, type {danmaku_type}")
    collection_name = ""
    danmaku_type_label = ""
    db_field_name = ""

    if danmaku_type == "welcome_boss":
        collection_name = db_config.BIG_BROTHERS_COLLECTION
        danmaku_type_label = "欢迎大哥"
        db_field_name = "welcome_text"
    elif danmaku_type == "thanks_boss_gift":
        collection_name = db_config.GIFT_THANKS_COLLECTION
        danmaku_type_label = "感谢大哥礼物"
        db_field_name = "danmaku_text"
    else:
        logging.error(f"Task {task_name}: ws_danmaku_send_handlers: Invalid danmaku_type '{danmaku_type}' in auto_send_boss_danmaku_flow.")
        if websocket:
            await websocket.send(json.dumps({"type": "error", "message": "内部错误：无效的大哥弹幕类型。", "context": "send_boss_internal_type_error"}))
        logging.info(f"Task {task_name}: Invalid danmaku type, RETURNING.")
        return

    try: # This is the main try block for the entire flow
        db_manager = get_db_manager()
        logging.info(f"Task {task_name}: BEFORE checking DB connection")
        db = db_manager.get_db() if db_manager and db_manager.is_connected() else None
        logging.info(f"Task {task_name}: AFTER checking DB connection")
        if db is None:
            logging.error(f"Task {task_name}: ws_danmaku_send_handlers: DB connection lost before fetching {danmaku_type_label} templates for {boss_name}.")
            if websocket:
                await websocket.send(json.dumps({"type": "error", "message": "数据库连接丢失。", "context": "send_boss_db_fetch_error"}))
            logging.info(f"Task {task_name}: DB connection lost, RETURNING.")
            return

        mongo_collection = db[collection_name]
        # 获取所有不为空的模板
        logging.info(f"Task {task_name}: BEFORE fetching distinct danmaku templates")
        unique_danmaku_templates_raw = mongo_collection.distinct(db_field_name)
        logging.info(f"Task {task_name}: AFTER fetching distinct danmaku templates")
        unique_danmaku_templates = [tpl for tpl in unique_danmaku_templates_raw if isinstance(tpl, str) and tpl.strip()]

        if not unique_danmaku_templates:
            logging.info(f"Task {task_name}: ws_danmaku_send_handlers: No *valid* unique '{danmaku_type_label}' danmaku found in collection '{collection_name}'.")
            if websocket:
                await websocket.send(json.dumps({"type": "info", "message": f"数据库中没有找到可用的{danmaku_type_label}弹幕。", "context": f"send_boss_{danmaku_type}_empty"}))
            logging.info(f"Task {task_name}: No valid templates, RETURNING.")
            return

        logging.info(f"Task {task_name}: ws_danmaku_send_handlers: Fetched {len(unique_danmaku_templates)} *valid* unique '{danmaku_type_label}' templates for {boss_name}.")

        processed_danmaku_list = []
        # 准备 desired_total_count (30) 条弹幕
        temp_template_list = []
        if len(unique_danmaku_templates) >= desired_total_count:
            random.shuffle(unique_danmaku_templates)
            temp_template_list = unique_danmaku_templates[:desired_total_count]
        else:
            # 如果模板不足，循环使用
            for i in range(desired_total_count):
                temp_template_list.append(unique_danmaku_templates[i % len(unique_danmaku_templates)])

        # 进行占位符替换
        for raw_template in temp_template_list:
            processed_text = raw_template
            s_boss_name = str(boss_name) if boss_name else "大哥" # 默认值
            s_gift_name = str(gift_name) if gift_name else "礼物" # 默认值

            if danmaku_type == "welcome_boss":
                # 欢迎大哥：只替换 boss_name
                processed_text = processed_text.replace("{}", s_boss_name, 1)
                if "{}" in processed_text:
                    logging.warning(f"Task {task_name}: ws_danmaku_send_handlers: Welcome boss template '{raw_template}' still contains '{{}}' after replacing boss_name: '{processed_text}'")

            elif danmaku_type == "thanks_boss_gift":
                # 感谢大哥礼物：模板通常是 "感谢{大哥名}的{礼物名}..."
                # 按顺序替换：第一个 {} 是 boss_name，第二个 {} 是 gift_name

                # 先替换第一个 {} 为 boss_name
                if "{}" in processed_text:
                    processed_text = processed_text.replace("{}", s_boss_name, 1)
                else: # 如果模板本身没有占位符，或者第一个已被意外处理（不太可能）
                    logging.warning(f"Task {task_name}: ws_danmaku_send_handlers: Thanks gift template '{raw_template}' did not have a first '{{}}' for boss_name.")

                # 再替换（可能存在的）第二个 {} 为 gift_name
                if "{}" in processed_text:
                    processed_text = processed_text.replace("{}", s_gift_name, 1)
            processed_danmaku_list.append(processed_text)

        if not processed_danmaku_list:
            logging.info(f"Task {task_name}: No processed danmaku, RETURNING EARLY.")
            return

        # 分成两组发送
        group_size = len(processed_danmaku_list) // 2
        group1 = processed_danmaku_list[:group_size]
        group2 = processed_danmaku_list[group_size:]

        if group1:
            logging.info(f"ws_danmaku_send_handlers: Sending Group 1 ({len(group1)} items) of '{danmaku_type_label}' for {boss_name} with {BOSS_GIFT_DANMAKU_DURATION_MS}ms duration each...")
            await _send_danmaku_group(group1, danmaku_type_label, websocket, boss_name, gift_name, specific_duration_ms=BOSS_GIFT_DANMAKU_DURATION_MS)

        if group2:
            logging.info(f"ws_danmaku_send_handlers: Pausing for {GROUP_PAUSE_MS / 1000} seconds between groups before sending group2 for {boss_name}.")
            await asyncio.sleep(GROUP_PAUSE_MS / 1000)
            logging.info(f"ws_danmaku_send_handlers: Sending Group 2 ({len(group2)} items) of '{danmaku_type_label}' for {boss_name} with {BOSS_GIFT_DANMAKU_DURATION_MS}ms duration each...")
            await _send_danmaku_group(group2, danmaku_type_label, websocket, boss_name, gift_name, specific_duration_ms=BOSS_GIFT_DANMAKU_DURATION_MS)

        logging.info(f"ws_danmaku_send_handlers: Auto-send sequence for '{boss_name}' {danmaku_type_label} finished.")
        if websocket:
            await websocket.send(json.dumps({"type": "success", "message": f"{danmaku_type_label}弹幕自动发送完成。", "context": f"send_boss_{danmaku_type}_finished"}))

    except asyncio.CancelledError:
        logging.info("ws_danmaku_send_handlers: Boss auto-send task was cancelled.")
        if websocket:
            await websocket.send(json.dumps({"type": "info", "message": "大哥弹幕自动发送已取消。", "context": "send_boss_cancelled"}))
    except Exception as e:
        logging.error(f"ws_danmaku_send_handlers: Error during boss auto-send for '{boss_name}': {e}", exc_info=True)
        if websocket:
            await websocket.send(json.dumps({"type": "error", "message": f"大哥弹幕自动发送时出错: {e}", "context": "send_boss_error"}))
    finally:
        # 确保按钮在任何情况下都会重新启用
        if websocket:
            await websocket.send(json.dumps({"type": "re_enable_auto_send_buttons", "context": "send_boss_finally_reenable"}))

def register_danmaku_send_handlers():
    if _broadcast_message is None:
        logging.error("ws_danmaku_send_handlers: Dependencies missing. Send handlers will be unavailable.")
        return {}
    handlers = {
        "auto_send_danmaku": handle_auto_send_danmaku,
        "send_boss_danmaku": handle_send_boss_danmaku,
    }
    logging.info(f"ws_danmaku_send_handlers: Registering send handlers: {list(handlers.keys())}")
    return handlers

__all__ = [
    'init_danmaku_send_handlers',
    'register_danmaku_send_handlers',
]
