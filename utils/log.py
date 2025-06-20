"""
Log Utility Module
提供全域log設定與logger取得
"""
import logging
import os
import glob
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Log')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'game_monitor.log')

class CustomRotatingFileHandler(RotatingFileHandler):
    """自定義的RotatingFileHandler，修改備份檔案命名格式"""
    
    def rotation_filename(self, default_name):
        """自定義備份檔案名稱格式"""
        dirname, basename = os.path.split(default_name)
        prefix, ext = os.path.splitext(basename)
        
        # 找出現有的備份檔案數量
        existing_files = glob.glob(os.path.join(dirname, f"{prefix}*.log"))
        backup_number = len(existing_files)
        
        return os.path.join(dirname, f"{prefix}{backup_number}.log")

def clear_log_directory():
    """清空Log資料夾"""
    if os.path.exists(LOG_DIR):
        for filename in os.listdir(LOG_DIR):
            file_path = os.path.join(LOG_DIR, filename)
            if os.path.isfile(file_path) and filename.endswith('.log'):
                os.remove(file_path)

def setup_logging():
    """設定日誌系統"""
    # 清空Log資料夾
    clear_log_directory()

# 清空Log資料夾
clear_log_directory()

# 設定root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        CustomRotatingFileHandler(LOG_FILE, maxBytes=20*1024*1024, backupCount=3, encoding='utf-8')
    ]
)

# 設定file handler為DEBUG, console為INFO，並分別設置formatter
for handler in logging.getLogger().handlers:
    if isinstance(handler, (RotatingFileHandler, CustomRotatingFileHandler)):
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(filename)s:%(lineno)d %(message)s'))
    else:
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

def get_logger(name=None):
    return logging.getLogger(name)
