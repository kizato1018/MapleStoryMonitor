"""
Log Utility Module
提供全域log設定與logger取得
"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Log')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'game_monitor.log')

def setup_logging():
    """設定日誌系統"""
    # 創建日誌目錄
    log_dir = LOG_DIR
    
    # 配置日誌
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(
                LOG_FILE, 
                mode='w',  # 改為 'w' 模式，每次啟動時覆蓋日誌檔案
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )

# 設定root logger
logging.basicConfig(
    level=logging.DEBUG,  # 這裡改成DEBUG，讓所有訊息都能進入handler
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(LOG_FILE, maxBytes=2*1024*1024, backupCount=3, encoding='utf-8')
    ]
)

# 設定file handler為DEBUG, console為INFO，並分別設置formatter
for handler in logging.getLogger().handlers:
    if isinstance(handler, RotatingFileHandler):
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(filename)s:%(lineno)d %(message)s'))
    else:
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

def get_logger(name=None):
    return logging.getLogger(name)
