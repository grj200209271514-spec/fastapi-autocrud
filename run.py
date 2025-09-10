import uvicorn
import os
import sys
from pathlib import Path

# --- 这是解决问题的关键代码 ---
# 1. 获取当前文件 (run.py) 所在的目录的绝对路径
#    例如: C:\Users\admin\PycharmProjects\autoapi
ROOT_DIR = Path(__file__).resolve().parent

# 2. 将这个根目录添加到 Python 的模块搜索路径列表的最前面
#    这确保了 'from app.main import app' 总是从正确的基准路径开始查找，
#    从而避免了“双胞胎模块”问题。
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
# --- 关键代码结束 ---


# 定义应用模块的路径字符串，这是最关键的一步
# 它告诉 Uvicorn: "去 'app' 包里找 'main.py' 文件，然后加载名为 'app' 的变量"
APP_MODULE = "app.main:app"

# 从环境变量获取端口和主机，或者使用默认值
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("RELOAD", "True").lower() == "true"

if __name__ == "__main__":
    print("--- Starting FastAPI Server with Uvicorn (Fixed) ---")
    print(f"Project Root added to sys.path: {ROOT_DIR}")
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"Reload enabled: {RELOAD}")
    print(f"Application module: {APP_MODULE}")
    print("--------------------------------------------------")

    uvicorn.run(
        APP_MODULE,
        host=HOST,
        port=PORT,
        reload=RELOAD,
        # 你可以根据需要添加其他配置，例如 workers
        # workers=4
    )
