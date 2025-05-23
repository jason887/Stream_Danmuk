# minimal_test_server.py
import asyncio
import websockets
import logging
import time # For the file write test
import os   # For file operations

# 详细的日志配置
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(name)-22s %(module)-18s %(funcName)-25s L%(lineno)-4d: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler() # 确保输出到控制台
    ]
)
# 为 websockets 库设置 DEBUG 级别
logging.getLogger("websockets").setLevel(logging.DEBUG)
# 为本模块的 logger 设置 DEBUG 级别
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# 用于标记 process_pong 是否被调用的文件
PONG_TEST_FILE = "pong_test_flag.txt"

class MyCustomProtocol(websockets.WebSocketServerProtocol):
    async def process_pong(self, data: bytes) -> None:
        # --- 这是关键的测试部分 ---
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        log_message = (
            f"!!!!!!!! MY CUSTOM PROTOCOL: PONG RECEIVED at {timestamp_str} "
            f"from {self.remote_address}. Data: {data!r} !!!!!!!!"
        )
        
        # 1. 直接打印到控制台 (尝试绕过任何日志配置问题)
        print(log_message, flush=True)
        
        # 2. 使用高优先级的日志记录
        logger.error(log_message) # 使用模块级别的 logger

        # 3. 尝试写入文件作为明确的副作用
        try:
            with open(PONG_TEST_FILE, "a") as f:
                f.write(f"{log_message}\n")
            logger.info(f"Successfully wrote to {PONG_TEST_FILE}")
        except Exception as e:
            logger.error(f"Failed to write to {PONG_TEST_FILE}: {e}", exc_info=True)
        # --- 测试部分结束 ---

        # 暂时注释掉 super() 调用，以完全隔离我们的代码行为
        # await super().process_pong(data)
        # logger.info("MY CUSTOM PROTOCOL: super().process_pong would have been called here.")
        pass # 目前在这里不做其他事情


async def handler(websocket, path):
    logger.info(f"Client {websocket.remote_address} connected to path '{path}'.")
    try:
        async for message in websocket:
            logger.info(f"Received message from {websocket.remote_address}: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Client {websocket.remote_address} disconnected. Code: {e.code}, Reason: '{e.reason}'")
    except Exception as e:
        logger.error(f"Error in handler for {websocket.remote_address}: {e}", exc_info=True)
    finally:
        logger.info(f"Handler for {websocket.remote_address} finished.")

async def main():
    # 在启动时清理旧的标记文件
    try:
        if os.path.exists(PONG_TEST_FILE):
            os.remove(PONG_TEST_FILE)
        logger.info(f"Removed old {PONG_TEST_FILE} if it existed.")
    except Exception as e:
        logger.error(f"Error removing old {PONG_TEST_FILE}: {e}", exc_info=True)

    server = await websockets.serve(
        handler,
        "localhost",
        8766, # 确保使用这个端口
        ping_interval=5,    # 快速 PING 以便测试
        ping_timeout=10,
        create_protocol=MyCustomProtocol # 使用我们的自定义协议
    )
    logger.info("Minimal server started on ws://localhost:8766 with ping_interval=5s")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())